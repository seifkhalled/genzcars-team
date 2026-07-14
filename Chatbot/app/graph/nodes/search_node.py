import json
import logging
from uuid import UUID
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
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

RESPONSE_SYSTEM = """You are a helpful car marketplace assistant.
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


def compute_dcg(results: list[dict]) -> float:
    """Compute DCG-like metric using Qdrant scores as relevance gains."""
    dcg = 0.0
    for i, r in enumerate(results):
        gain = r.get("score", 0.0) * 3
        if i == 0:
            dcg += gain
        else:
            dcg += gain / (i + 1)
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

    try:
        parsed = json.loads(query_response.content.strip().removeprefix("```json").removesuffix("```").strip())
        search_query = parsed.get("search_query", last_message)
        filters = parsed.get("filters", {})
    except (json.JSONDecodeError, AttributeError):
        search_query = last_message
        filters = {}

    # Step 2: Extract filters from the query builder output only
    brand_filter = filters.get("brand")
    body_types = list(filters.get("body_types") or [])
    excluded_body_types = filters.get("excluded_body_types")
    excluded_brands = filters.get("excluded_brands")
    excluded_models = filters.get("excluded_models")

    # Step 2.1: Merge accumulated preferences as fallback filters
    prefs = state.get("preferences", {})
    prefs_to_filters = {
        "preferred_brands": "brand",
        "preferred_body_types": "body_types",
        "budget_min": "price_min",
        "budget_max": "price_max",
        "preferred_fuel_types": "fuel_type",
        "preferred_transmission": "transmission",
        "preferred_cities": "city",
    }
    prefs_to_list_filters = {
        "inferred_body_types": "body_types",
    }
    for pref_key, filter_key in prefs_to_filters.items():
        pref_val = prefs.get(pref_key)
        if pref_val and not filters.get(filter_key):
            filters[filter_key] = pref_val
    for pref_key, filter_key in prefs_to_list_filters.items():
        pref_val = prefs.get(pref_key)
        if pref_val and not filters.get(filter_key):
            filters[filter_key] = pref_val

    # Re-sync after merge
    brand_filter = filters.get("brand")
    body_types = list(filters.get("body_types") or [])
    excluded_body_types = filters.get("excluded_body_types") or prefs.get("excluded_body_types")
    excluded_brands = filters.get("excluded_brands") or prefs.get("excluded_brands")
    excluded_models = filters.get("excluded_models") or prefs.get("excluded_models")

    results = []
    if mcp_registry:
        try:
            mcp_results = await mcp_registry.call_tool("search_cars", {
                "query": search_query,
                "limit": SEARCH_INITIAL_LIMIT + 3,
                "budget_min": filters.get("price_min"),
                "budget_max": filters.get("price_max"),
                "brand": brand_filter if isinstance(brand_filter, str) else None,
                "brands": brand_filter if isinstance(brand_filter, list) else None,
                "city": filters.get("city"),
                "fuel_type": filters.get("fuel_type"),
                "transmission": filters.get("transmission"),
                "body_types": body_types or None,
                "excluded_body_types": excluded_body_types,
                "excluded_brands": excluded_brands,
                "excluded_models": excluded_models,
            })
            if isinstance(mcp_results, list):
                results = mcp_results
        except Exception as e:
            logger.warning("MCP search_cars failed, falling back to direct: %s", e)

    if not results:
        vector = embedder.encode(search_query)
        results = qdrant_search.hybrid_search(
            query_text=search_query,
            vector=vector,
            limit=SEARCH_INITIAL_LIMIT + 3,
            price_min=filters.get("price_min"),
            price_max=filters.get("price_max"),
            city=filters.get("city"),
            brand=brand_filter if isinstance(brand_filter, str) else None,
            brands=brand_filter if isinstance(brand_filter, list) else None,
            fuel_type=filters.get("fuel_type"),
            transmission=filters.get("transmission"),
            body_types=body_types or None,
            excluded_body_types=excluded_body_types,
            excluded_brands=excluded_brands,
            excluded_models=excluded_models,
        )

    results = verify_results(results)
    search_dcg = compute_dcg(results)

    # Step 2.5: Evaluate quality — retry with broader hybrid search if poor
    if not evaluate_search_quality(results):
        broader_results = []
        if mcp_registry:
            try:
                b = await mcp_registry.call_tool("search_cars", {
                    "query": search_query,
                    "limit": SEARCH_BROAD_LIMIT,
                    "brand": brand_filter if isinstance(brand_filter, str) else None,
                    "brands": brand_filter if isinstance(brand_filter, list) else None,
                    "excluded_body_types": excluded_body_types,
                    "excluded_brands": excluded_brands,
                    "excluded_models": excluded_models,
                })
                if isinstance(b, list):
                    broader_results = b
            except Exception:
                pass
        if not broader_results and qdrant_search:
            broader_results = qdrant_search.hybrid_search(
                query_text=search_query,
                vector=embedder.encode(search_query),
                limit=SEARCH_BROAD_LIMIT,
                brand=brand_filter if isinstance(brand_filter, str) else None,
                brands=brand_filter if isinstance(brand_filter, list) else None,
                excluded_body_types=excluded_body_types,
                excluded_brands=excluded_brands,
                excluded_models=excluded_models,
            )
        broader_results = verify_results(broader_results)
        broader_dcg = compute_dcg(broader_results)
        if broader_dcg > search_dcg:
            results = merge_dedup_results(broader_results, results, max_count=MERGE_MAX_COUNT)
        else:
            results = merge_dedup_results(results, broader_results, max_count=MERGE_MAX_COUNT)

    # Step 3: Fetch images and build ad list
    ad_ids = []
    for r in results:
        try:
            aid = UUID(r.get("ad_id", r["id"]))
            ad_ids.append(aid)
        except (ValueError, KeyError):
            continue

    images_map = {}
    if ad_ids:
        if mcp_registry:
            try:
                images_map = await mcp_registry.call_tool("get_car_images", {"ad_ids": [str(a) for a in ad_ids]})
                if not isinstance(images_map, dict):
                    images_map = {}
            except Exception as e:
                logger.warning("MCP get_car_images failed, falling back: %s", e)
                images_map = {}
        if not images_map and pool:
            from app.db.queries import get_ad_images_by_ids
            images_map = await get_ad_images_by_ids(pool, ad_ids)

    ads = []
    for r in results:
        aid = r.get("ad_id", r["id"])
        try:
            ad = {
                "id": aid,
                "brand": r.get("brand", ""),
                "model": r.get("model", ""),
                "year": r.get("year", 0),
                "price": float(r.get("price", 0)),
                "condition": r.get("condition", ""),
                "km_driven": r.get("km_driven", 0),
                "body_type": r.get("body_type", ""),
                "transmission": r.get("transmission", ""),
                "fuel_type": r.get("fuel_type", ""),
                "city": r.get("city", ""),
                "cover_image_url": r.get("cover_image_url", ""),
                "images": images_map.get(aid, []),
                "score": r.get("score", 0),
            }
            ads.append(ad)
        except (ValueError, KeyError):
            continue

    # Step 4: Draft conversational response (streaming)
    # Step 4: Draft conversational response (streaming)
    cars_summary = ""
    if ads:
        cities = set()
        body_types = set()
        prices = set()
        brands = set()
        for a in ads:
            if a.get("city"): cities.add(a["city"])
            if a.get("body_type"): body_types.add(a["body_type"])
            if a.get("price"): prices.add(a["price"])
            if a.get("brand"): brands.add(a["brand"])
        parts = [f"{len(ads)} car{'s' if len(ads) != 1 else ''} found"]
        if brands:
            parts.append(f"brands: {', '.join(sorted(brands))}")
        if cities:
            parts.append(f"in {', '.join(sorted(cities))}")
        if body_types:
            parts.append(f"(body types: {', '.join(sorted(body_types))})")
        if prices:
            parts.append(f"priced {min(prices):,.0f} – {max(prices):,.0f} EGP")
        cars_summary = " ".join(parts)

    streamed_text = ""
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

    return {
        "retrieved_ads": ads[:MERGE_MAX_COUNT],
        "node_response": streamed_text,
    }
