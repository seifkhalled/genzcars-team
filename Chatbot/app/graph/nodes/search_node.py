import json
import logging
import math
from uuid import UUID
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError
from app.enums import TaskType
from app.graph.state import CarsChatState
from app.core.hallucination_guard import verify_results
from app.data.car_features import format_expansions_prompt
from app.core.ai_metrics import search_quality_total
from app.data.constants import (
    SEARCH_QUALITY_TOP_SCORE_MIN,
    SEARCH_QUALITY_AVG_SCORE_MIN,
    SEARCH_INITIAL_LIMIT,
    SEARCH_BROAD_LIMIT,
    MERGE_MAX_COUNT,
)
from app.schemas.search import LLMExtractedFilters, CarAd

logger = logging.getLogger(__name__)

QUERY_BUILDER_SYSTEM = """You are a search query builder for a car marketplace vector database.
Given the user's message and the conversation history, build the best
possible search query string that will retrieve relevant car listings.

Rules:
1. Extract ONLY clear metadata filters from the ENTIRE conversation: brand,
   price_min, price_max, city, fuel_type, transmission, body_types.
   If uncertain, leave null/[]. body_types is a LIST — even for a single
   body type, use ["sedan"].
2. NEVER extract "condition" filter from words like "conditioner",
   "conditioning", "AC", "air conditioning" — these are car FEATURES, not
   the car's mechanical condition.
3. Put EVERYTHING else (features, needs, preferences) into search_query for
   semantic matching against listing descriptions.
4. CRITICAL — body_type keywords (sedan, SUV, hatchback, coupe, convertible,
   pickup, van, crossover, station wagon, etc.) MUST be extracted as
   filters.body_types list items, NEVER placed in search_query. Only body_type
   values that appear in the user's message go in filters.body_types;
   if none mentioned, use [].
5. Expand colloquial car terms in search_query:
{expansions_prompt}
6. If the user asks about features typically in descriptions (not metadata),
   use a broader search query and leave filters minimal/null.

Return ONLY valid JSON:
{{
  "search_query": "detailed expanded search query for semantic matching",
  "filters": {{
    "price_min": null,
    "price_max": null,
    "brand": null,
    "city": null,
    "fuel_type": null,
    "transmission": null,
    "body_types": []
  }}
}}

User message: "{message}"
Conversation history:
{conversation_history}"""

RESPONSE_SYSTEM = """You are a helpful Egyptian car marketplace assistant.
You have just searched the listings and found cars matching the user's request.
Write a natural, friendly 1-2 sentence response.

CRITICAL RULES:
1. NEVER list, enumerate, or describe individual cars by number, bullet,
   or any other format. The visual cards below your message will show each car.
2. ONLY describe the results in aggregate using the summary below.
3. Use EXACTLY the numbers from the summary — do not change counts, prices,
   or locations. If the summary says "2 cars", say "2 cars", not "1 car".
4. If the summary shows mixed body types, mention that. Do NOT pick one
   body type and ignore the others.
5. The marketplace operates in Egypt. Currency is ALWAYS EGP (Egyptian
   Pounds). NEVER use USD, dollars, $, or any non-Egyptian currency.
6. Cities are ALWAYS Egyptian cities (e.g., Cairo, Alexandria, Giza,
   New Cairo, Sheikh Zayed, Mansoura). NEVER use non-Egyptian cities or
   states (e.g., never New York, California, Dubai, London).

Found cars summary:
{cars_summary}

User message: "{message}"
"""


def evaluate_search_quality(results: list[dict]) -> bool:
    if not results:
        search_quality_total.labels(service="chatbot", passed="false").inc()
        return False
    avg_score = sum(r.get("score", 0) for r in results) / len(results)
    top_score = results[0].get("score", 0) if results else 0
    passed = top_score > SEARCH_QUALITY_TOP_SCORE_MIN or avg_score > SEARCH_QUALITY_AVG_SCORE_MIN
    search_quality_total.labels(service="chatbot", passed=str(passed).lower()).inc()
    return passed


def compute_relevance_score(results: list[dict]) -> float:
    if not results:
        return 0.0
    dcg = 0.0
    for i, r in enumerate(results):
        gain = r.get("score", 0.0)
        dcg += gain / math.log2(i + 2)
    return dcg


def merge_dedup_results(primary: list[dict], secondary: list[dict], max_count: int = MERGE_MAX_COUNT) -> list[dict]:
    seen = set()
    merged = []
    for r in primary + secondary:
        aid = r.get("ad_id", r.get("id"))
        if aid and aid not in seen:
            seen.add(aid)
            merged.append(r)
    return merged[:max_count]


def _prefs_to_filters_dict(prefs: dict) -> dict:
    merged = {}
    mapping = {
        "preferred_brands": "brands",
        "preferred_body_types": "body_types",
        "inferred_body_types": "body_types",
        "budget_min": "price_min",
        "budget_max": "price_max",
        "preferred_fuel_types": "fuel_type",
        "preferred_transmission": "transmission",
        "preferred_cities": "city",
    }
    for pref_key, filter_key in mapping.items():
        pref_val = prefs.get(pref_key)
        if pref_val:
            if filter_key in merged:
                existing = merged[filter_key]
                if isinstance(existing, list):
                    merged[filter_key] = list(set(existing + (pref_val if isinstance(pref_val, list) else [pref_val])))
            else:
                merged[filter_key] = pref_val
    for excl_key in ("excluded_body_types", "excluded_brands", "excluded_models"):
        val = prefs.get(excl_key)
        if val:
            merged[excl_key] = val
    for year_key in ("year_min", "year_max"):
        val = prefs.get(year_key)
        if val:
            merged[year_key] = val
    return merged


async def search_node(state: CarsChatState, config: RunnableConfig) -> dict:
    multi_llm = config["configurable"].get("multi_llm")
    llm_fast = config["configurable"]["llm_fast"]
    llm_stream = config["configurable"]["llm_stream"]
    embedder = config["configurable"]["embedder"]
    qdrant_search = config["configurable"]["qdrant_search"]
    pool = config["configurable"].get("db_pool")
    mcp_registry = config["configurable"].get("mcp_registry")

    last_message = state["messages"][-1].content if state.get("messages") else ""

    # Build conversation history from last 6 messages (3 user+assistant pairs)
    history_msgs = []
    for m in state.get("messages", [])[-6:]:
        role = "user" if m.type == "human" else "assistant"
        history_msgs.append(f"{role}: {m.content}")
    conversation_history = "\n".join(history_msgs) if history_msgs else "No prior conversation."

    # Inject accumulated brand preferences into conversation history
    # so the query builder LLM sees them even when the current message is vague.
    prefs = state.get("preferences", {})
    preferred_brands = prefs.get("preferred_brands")
    if preferred_brands:
        mentioned = any(
            b.lower() in last_message.lower()
            for b in (preferred_brands if isinstance(preferred_brands, list) else [preferred_brands])
        )
        if not mentioned:
            brands_str = ", ".join(preferred_brands) if isinstance(preferred_brands, list) else str(preferred_brands)
            conversation_history += f"\n[Known user preferences: brands = {brands_str}]"

    # Step 1: Build enhanced search query from conversation history
    system_msg = SystemMessage(content=QUERY_BUILDER_SYSTEM.format(
        message=last_message,
        conversation_history=conversation_history,
        expansions_prompt=format_expansions_prompt(),
    ))
    if multi_llm:
        query_response = await multi_llm.ainvoke_task(TaskType.SEARCH, [system_msg, HumanMessage(content=last_message)])
    else:
        query_response = await llm_fast.ainvoke([system_msg, HumanMessage(content=last_message)])

    search_query = last_message
    filters: dict = {}
    try:
        raw = query_response.content.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(raw)
        validated = LLMExtractedFilters(**parsed)
        search_query = validated.search_query
        filters = validated.model_dump(exclude={"search_query"}, exclude_none=True)
    except (json.JSONDecodeError, ValidationError, AttributeError) as e:
        logger.warning("Query builder LLM output parse failed: %s: %s", type(e).__name__, str(e)[:200])

    # Step 2: Merge preferences into filters — single pass
    prefs_override = _prefs_to_filters_dict(state.get("preferences", {}))
    # Unify the brand dimension: a current explicit brand intent from the LLM
    # (brand or brands) must win over stale accumulated preferred_brands.
    # Otherwise we'd inject "brands" alongside an existing "brand" and AND them
    # into an empty result set.
    if filters.get("brand") is not None or filters.get("brands") is not None:
        prefs_override.pop("brands", None)
    for key, val in prefs_override.items():
        if val is not None and filters.get(key) is None:
            filters[key] = val

    brand_filter = filters.get("brand")
    body_type_filter = filters.get("body_types")
    if isinstance(body_type_filter, list):
        body_type_filter = [b for b in body_type_filter if b]
    else:
        body_type_filter = body_type_filter or None

    # Step 3: Search listings
    results = []
    if mcp_registry:
        try:
            mcp_results = await mcp_registry.call_tool("search_cars", {
                "query": search_query,
                "limit": SEARCH_INITIAL_LIMIT + 3,
                "budget_min": filters.get("price_min"),
                "budget_max": filters.get("price_max"),
                "brand": brand_filter if isinstance(brand_filter, str) else None,
                "brands": filters.get("brands"),
                "city": filters.get("city"),
                "fuel_type": filters.get("fuel_type"),
                "transmission": filters.get("transmission"),
                "body_types": body_type_filter,
                "excluded_body_types": filters.get("excluded_body_types"),
                "excluded_brands": filters.get("excluded_brands"),
                "excluded_models": filters.get("excluded_models"),
            })
            if isinstance(mcp_results, list):
                results = mcp_results
        except Exception as e:
            logger.warning("MCP search_cars failed (%s: %s), falling back to direct search", type(e).__name__, str(e)[:200])

    cached_vector = None
    if not results:
        cached_vector = embedder.encode(search_query)
        results = qdrant_search.hybrid_search(
            query_text=search_query,
            vector=cached_vector,
            limit=SEARCH_INITIAL_LIMIT + 3,
            price_min=filters.get("price_min"),
            price_max=filters.get("price_max"),
            city=filters.get("city"),
            brand=brand_filter if isinstance(brand_filter, str) else None,
            brands=filters.get("brands"),
            fuel_type=filters.get("fuel_type"),
            transmission=filters.get("transmission"),
            body_types=body_type_filter,
            excluded_body_types=filters.get("excluded_body_types"),
            excluded_brands=filters.get("excluded_brands"),
            excluded_models=filters.get("excluded_models"),
        )

    results = verify_results(results)
    relevance_score = compute_relevance_score(results)

    # Broaden search if quality is poor
    if not evaluate_search_quality(results):
        broader_results = []
        if mcp_registry:
            try:
                b = await mcp_registry.call_tool("search_cars", {
                    "query": search_query,
                    "limit": SEARCH_BROAD_LIMIT,
                    "brand": brand_filter if isinstance(brand_filter, str) else None,
                    "brands": filters.get("brands"),
                    "excluded_body_types": filters.get("excluded_body_types"),
                    "excluded_brands": filters.get("excluded_brands"),
                    "excluded_models": filters.get("excluded_models"),
                })
                if isinstance(b, list):
                    broader_results = b
            except Exception as e:
                logger.warning("MCP search_cars broadening failed (%s: %s)", type(e).__name__, str(e)[:200])
        if not broader_results and qdrant_search:
            if cached_vector is None:
                cached_vector = embedder.encode(search_query)
            broader_results = qdrant_search.hybrid_search(
                query_text=search_query,
                vector=cached_vector,
                limit=SEARCH_BROAD_LIMIT,
                brand=brand_filter if isinstance(brand_filter, str) else None,
                brands=filters.get("brands"),
                excluded_body_types=filters.get("excluded_body_types"),
                excluded_brands=filters.get("excluded_brands"),
                excluded_models=filters.get("excluded_models"),
            )
        broader_results = verify_results(broader_results)
        broader_relevance = compute_relevance_score(broader_results)
        if broader_relevance > relevance_score:
            results = merge_dedup_results(broader_results, results, max_count=MERGE_MAX_COUNT)
        else:
            results = merge_dedup_results(results, broader_results, max_count=MERGE_MAX_COUNT)

    # Step 4: Fetch images and build validated ad list
    ad_ids = []
    for r in results:
        try:
            aid = UUID(r.get("ad_id", r["id"]))
            ad_ids.append(aid)
        except (ValueError, KeyError) as e:
            logger.warning("Skipping result with bad ad_id (%s): %s", type(e).__name__, r.get("ad_id", r.get("id", "unknown")))
            continue

    images_map = {}
    if ad_ids:
        if mcp_registry:
            try:
                images_map = await mcp_registry.call_tool("get_car_images", {"ad_ids": [str(a) for a in ad_ids]})
                if not isinstance(images_map, dict):
                    images_map = {}
            except Exception as e:
                logger.warning("MCP get_car_images failed (%s: %s), falling back to direct", type(e).__name__, str(e)[:200])
                images_map = {}
        if not images_map and pool:
            from app.db.queries import get_ad_images_by_ids
            images_map = await get_ad_images_by_ids(pool, ad_ids)

    ads: list[CarAd] = []
    for r in results:
        aid = r.get("ad_id", r["id"])
        try:
            ad = CarAd(
                id=aid,
                brand=r.get("brand", ""),
                model=r.get("model", ""),
                year=r.get("year", 0),
                price=float(r.get("price", 0)),
                condition=r.get("condition", ""),
                km_driven=r.get("km_driven", 0),
                body_type=r.get("body_type", ""),
                transmission=r.get("transmission", ""),
                fuel_type=r.get("fuel_type", ""),
                city=r.get("city", ""),
                cover_image_url=r.get("cover_image_url", ""),
                images=images_map.get(aid, []),
                score=r.get("score", 0),
            )
            ads.append(ad)
        except (ValueError, TypeError, ValidationError) as e:
            logger.warning("Skipping malformed result (ad_id=%s): %s: %s", aid, type(e).__name__, str(e)[:200])
            continue

    # Step 5: Build conversational response
    cars_summary = ""
    if ads:
        result_cities = set()
        result_body_types = set()
        result_prices = set()
        result_brands = set()
        for a in ads:
            if a.city:
                result_cities.add(a.city)
            if a.body_type:
                result_body_types.add(a.body_type)
            if a.price:
                result_prices.add(a.price)
            if a.brand:
                result_brands.add(a.brand)
        parts = [f"{len(ads)} car{'s' if len(ads) != 1 else ''} found"]
        if result_brands:
            parts.append(f"brands: {', '.join(sorted(result_brands))}")
        if result_cities:
            parts.append(f"in {', '.join(sorted(result_cities))}")
        if result_body_types:
            parts.append(f"(body types: {', '.join(sorted(result_body_types))})")
        if result_prices:
            parts.append(f"priced {min(result_prices):,.0f} – {max(result_prices):,.0f} EGP")
        cars_summary = " ".join(parts)

    streamed_text = ""
    if not ads:
        filter_parts = []
        if brand_filter:
            if isinstance(brand_filter, list):
                filter_parts.append(f"for {', '.join(brand_filter)}")
            else:
                filter_parts.append(f"for {brand_filter}")
        if filters.get("price_min") or filters.get("price_max"):
            range_parts = []
            if filters.get("price_min"):
                range_parts.append(f"from {filters['price_min']:,.0f} EGP")
            if filters.get("price_max"):
                range_parts.append(f"up to {filters['price_max']:,.0f} EGP")
            if range_parts:
                filter_parts.append(" ".join(range_parts))
        if body_type_filter:
            filter_parts.append(f"body type: {', '.join(body_type_filter)}")
        if filters.get("city"):
            filter_parts.append(f"in {filters['city']}")
        if filters.get("fuel_type"):
            filter_parts.append(f"fuel: {filters['fuel_type']}")
        if filters.get("transmission"):
            filter_parts.append(f"transmission: {filters['transmission']}")
        if filter_parts:
            streamed_text = f"I searched {', '.join(filter_parts)} but couldn't find any matching listings right now. Try adjusting your filters or check back later — new ads are added regularly."
        else:
            streamed_text = "I searched the listings but couldn't find any cars matching your criteria. Try adjusting your filters or checking back later — new ads are added regularly."
    else:
        response_msgs = [
            SystemMessage(content=RESPONSE_SYSTEM.format(
                message=last_message,
                cars_summary=cars_summary,
            )),
            HumanMessage(content=last_message),
        ]
        if multi_llm:
            async for chunk in multi_llm.astream_task(TaskType.SEARCH, response_msgs):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                streamed_text += content
        else:
            async for chunk in llm_stream.astream(response_msgs):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                streamed_text += content

    ad_dicts = [a.model_dump() for a in ads[:MERGE_MAX_COUNT]]
    return {
        "retrieved_ads": ad_dicts,
        "node_response": streamed_text,
    }
