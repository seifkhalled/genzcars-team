import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.enums import TaskType
from app.graph.state import CarsChatState
from app.data.constants import RECOMMENDATION_LIMIT
from app.data.brand_origins import detect_origin_brands, detect_origin_label

logger = logging.getLogger(__name__)

RECOMMENDATION_SYSTEM = """The user asked for a specific car/brand/origin that is NOT
available in our catalogue. You need to recommend alternative cars that are
actually in stock.

CRITICAL MARKET CONTEXT — This is an Egyptian marketplace:
- Currency is ALWAYS EGP (Egyptian Pounds). NEVER use USD, dollars, $, or
  any non-Egyptian currency.
- Cities are ALWAYS Egyptian (e.g., Cairo, Alexandria, Giza, New Cairo).
  NEVER use non-Egyptian cities or states.

They wanted: {requested_description}
What they searched for: brands={brands_searched}, model={model}, year={year}, body_type={body_type}

{origin_context}

Available alternatives found:
{alternatives_summary}

Write a friendly 2-3 sentence response in the same language the user wrote in:
1. Acknowledge their specific request is not currently available
2. Briefly mention that alternatives exist (e.g. "There are some similar
   Toyotas and Hondas available"), but do NOT describe any individual car
3. End on a positive note
4. If no alternatives summary data is available, say you couldn't find
   alternatives — NEVER describe imagined listings.

CRITICAL — Your response MUST NOT contain any numbered lists, bullet points,
or individual car descriptions. The visual cards below will show each
alternative car. NEVER write anything like "Ad 1:", "1.", "Option 1:", or
similar enumeration."""


async def recommendation_node(state: CarsChatState, config: RunnableConfig) -> dict:
    multi_llm = config["configurable"].get("multi_llm")
    llm_fast = config["configurable"]["llm_fast"]
    llm_stream = config["configurable"]["llm_stream"]
    embedder = config["configurable"]["embedder"]
    qdrant_search = config["configurable"]["qdrant_search"]
    pool = config["configurable"].get("db_pool")

    last_message = state["messages"][-1].content if state.get("messages") else ""
    catalogue = state.get("catalogue_check", {})

    brands_searched = catalogue.get("brands_searched", [])
    model = catalogue.get("model")
    year = catalogue.get("year")
    body_type = catalogue.get("body_type")
    request_label = catalogue.get("requested", last_message)
    origin_label = catalogue.get("requested_origin")

    # Deterministic origin detection — the single source of truth
    origin_brands = detect_origin_brands(last_message)
    if not origin_label:
        origin_label = detect_origin_label(last_message)

    # Build relaxed search query
    query_parts = []
    if brands_searched:
        query_parts.extend(brands_searched)
    if model:
        query_parts.append(model)
    if body_type:
        query_parts.append(body_type)
    if year:
        query_parts.append(str(year))

    search_text = " ".join(query_parts) if query_parts else last_message
    mcp_registry = config["configurable"].get("mcp_registry")

    body_types = [body_type] if body_type else None
    # Strict: use origin brands if detected, otherwise fall back to catalogue brands
    brands_filter = origin_brands if origin_brands else (brands_searched if brands_searched else None)

    # Search via MCP or direct
    results = []
    if mcp_registry:
        try:
            mcp_results = await mcp_registry.call_tool("search_cars", {
                "query": search_text,
                "limit": RECOMMENDATION_LIMIT + 3,
                "brands": brands_filter,
                "body_types": body_types,
                "year_min": year - 3 if year else None,
                "year_max": year + 3 if year else None,
            })
            if isinstance(mcp_results, list):
                results = mcp_results
        except Exception as e:
            logger.warning("MCP search_cars in recommendation_node failed, falling back: %s", e)

    if not results and qdrant_search:
        vector = embedder.encode(search_text)
        results = qdrant_search.hybrid_search(
            query_text=search_text,
            vector=vector,
            limit=RECOMMENDATION_LIMIT + 3,
            brands=brands_filter,
            body_types=body_types,
            year_min=year - 3 if year else None,
            year_max=year + 3 if year else None,
        )

    # Strict: only retry WITHOUT brand filter if we genuinely have zero
    # results AND the brand filter was set. This ensures we always try
    # the requested origin first, and only fall back when truly empty.
    used_fallback = False
    if not results and brands_filter and qdrant_search:
        logger.info("No listings matched brands %s; retrying without brand filter", brands_filter)
        vector = embedder.encode(search_text)
        results = qdrant_search.hybrid_search(
            query_text=search_text,
            vector=vector,
            limit=RECOMMENDATION_LIMIT + 3,
            body_types=body_types,
            year_min=year - 3 if year else None,
            year_max=year + 3 if year else None,
        )
        used_fallback = True

    # Build alternative ads list
    from app.core.hallucination_guard import verify_results
    results = verify_results(results)

    # Enforce brand constraint when the brand filter was applied
    # (skip when used_fallback=True because we intentionally dropped the filter)
    if not used_fallback and brands_filter:
        allowed = {b.lower() for b in brands_filter if isinstance(b, str)}
        if allowed:
            pre_count = len(results)
            results = [r for r in results if r.get("brand", "").lower() in allowed]
            if len(results) < pre_count:
                logger.info(
                    "Recommendation brand enforcement: kept %d/%d results matching %s",
                    len(results), pre_count, allowed,
                )

    images_map = {}
    if results:
        ad_ids = []
        from uuid import UUID
        for r in results:
            try:
                aid = UUID(r.get("ad_id", r["id"]))
                ad_ids.append(aid)
            except (ValueError, KeyError):
                continue
        if ad_ids:
            if mcp_registry:
                try:
                    images_map = await mcp_registry.call_tool("get_car_images", {"ad_ids": [str(a) for a in ad_ids]})
                    if not isinstance(images_map, dict):
                        images_map = {}
                except Exception:
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

    # Generate response text
    # Generate response text
    alternatives_summary = ""
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
        parts = [f"{len(ads)} alternative car{'s' if len(ads) != 1 else ''} found"]
        if brands:
            parts.append(f"brands: {', '.join(sorted(brands))}")
        if cities:
            parts.append(f"in {', '.join(sorted(cities))}")
        if body_types:
            parts.append(f"({', '.join(sorted(body_types))})")
        if prices:
            parts.append(f"priced {min(prices):,.0f} – {max(prices):,.0f} EGP")
        alternatives_summary = " ".join(parts)
    brands_str = ", ".join(brands_searched) if brands_searched else "unknown"
    model_str = model or "any"

    streamed_text = ""
    if not ads:
        if origin_label:
            streamed_text = f"We don't currently have any {origin_label} cars listed in our catalogue. Try checking back later — new ads are added regularly."
        else:
            streamed_text = f"I checked our catalogue but {request_label or 'the car you requested'} is not currently available, and I couldn't find any alternative listings matching your preferences. Try a different brand or model, or check back later."
    else:
        # Build origin context for the response LLM
        origin_context = ""
        if origin_label and origin_brands:
            origin_result_brands = [
                a["brand"] for a in ads if a.get("brand") in origin_brands
            ]
            non_origin_brands = [
                a["brand"] for a in ads if a.get("brand") not in origin_brands
            ]
            if origin_result_brands:
                origin_context = (
                    f"The user asked for {origin_label} cars. The {origin_label} brands "
                    f"found in results are: {', '.join(sorted(set(origin_result_brands)))}. "
                    f"If these {origin_label} brands are present, describe them as the main "
                    f"recommendation. The following non-{origin_label} brands are also shown "
                    f"as alternatives: {', '.join(sorted(set(non_origin_brands))) or 'none'}."
                )
            elif used_fallback:
                origin_context = (
                    f"The user asked for {origin_label} cars, but none are currently "
                    f"available. The alternatives shown are from other brands."
                )
        response_msgs = [
            SystemMessage(content=RECOMMENDATION_SYSTEM.format(
                requested_description=request_label,
                brands_searched=brands_str,
                model=model_str,
                year=year or "any",
                body_type=body_type or "any",
                alternatives_summary=alternatives_summary,
                origin_context=origin_context,
            )),
            HumanMessage(content=last_message),
        ]
        if multi_llm:
            async for chunk in multi_llm.astream_task(TaskType.RECOMMENDATION, response_msgs):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                streamed_text += content
        else:
            async for chunk in llm_stream.astream(response_msgs):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                streamed_text += content

    return {
        "retrieved_ads": ads[:2],
        "recommendations": ads[:2],
        "node_response": streamed_text,
    }
