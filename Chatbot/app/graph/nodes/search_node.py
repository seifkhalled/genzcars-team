import json
from uuid import UUID
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.graph.state import CarsChatState
from app.core.hallucination_guard import verify_results


QUERY_BUILDER_SYSTEM = """You are a search query builder for a car marketplace vector database.
Given the user's message and their accumulated preferences, build the best
possible search query string that will retrieve relevant car listings.

Combine: user's current request + relevant preferences (budget, brands,
city, use case, transmission preference, fuel preference).

Also extract any hard filters that should narrow the vector search results:
price_min, price_max, brand, city, fuel_type, transmission, body_type.

Return ONLY valid JSON:
{{
  "search_query": "family SUV automatic petrol Cairo under 500k good condition",
  "filters": {{
    "price_max": 500000,
    "city": "Cairo",
    "fuel_type": "petrol",
    "transmission": "automatic",
    "body_type": "suv"
  }}
}}

User message: "{message}"
Accumulated preferences: {preferences_json}"""


RESPONSE_SYSTEM = """You are a helpful car marketplace assistant.
You have just searched the listings and found the following cars that match
the user's request. Write a natural, friendly 2-3 sentence response
introducing the results. Mention key matching points (city, price range,
body type, etc.) that make these results relevant.
Do NOT list the cars — they will be shown as visual cards below your message.
Always respond in the same language the user wrote in (Arabic or English).

Found cars summary:
{cars_summary}

User message: "{message}"
"""


async def search_node(state: CarsChatState, config: RunnableConfig) -> dict:
    llm_fast = config["configurable"]["llm_fast"]
    llm_stream = config["configurable"]["llm_stream"]
    embedder = config["configurable"]["embedder"]
    qdrant_search = config["configurable"]["qdrant_search"]
    pool = config["configurable"].get("db_pool")

    last_message = state["messages"][-1].content if state.get("messages") else ""
    prefs = state.get("preferences", {})

    # Step 1: Build enhanced search query
    prefs_json = json.dumps(prefs, ensure_ascii=False, default=str)
    query_response = await llm_fast.ainvoke([
        SystemMessage(content=QUERY_BUILDER_SYSTEM.format(
            message=last_message,
            preferences_json=prefs_json,
        )),
        HumanMessage(content=last_message),
    ])

    try:
        parsed = json.loads(query_response.content.strip().removeprefix("```json").removesuffix("```").strip())
        search_query = parsed.get("search_query", last_message)
        filters = parsed.get("filters", {})
    except (json.JSONDecodeError, AttributeError):
        search_query = last_message
        filters = {}

    # Step 2: Embed and search Qdrant
    vector = embedder.encode(search_query)
    results = qdrant_search.search(
        vector=vector,
        limit=5,
        price_min=filters.get("price_min"),
        price_max=filters.get("price_max"),
        city=filters.get("city"),
        brand=filters.get("brand"),
        fuel_type=filters.get("fuel_type"),
        transmission=filters.get("transmission"),
        body_type=filters.get("body_type"),
        year_min=prefs.get("year_min"),
        year_max=prefs.get("year_max"),
    )

    results = verify_results(results)

    ad_ids = []
    for r in results:
        try:
            aid = UUID(r.get("ad_id", r["id"]))
            ad_ids.append(aid)
        except (ValueError, KeyError):
            continue

    ads = []
    if ad_ids and pool:
        from app.db.queries import get_ad_images_by_ids
        images_map = await get_ad_images_by_ids(pool, ad_ids)
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

    # Step 3: Draft conversational response (streaming)
    count = len(ads)
    cars_summary = f"{count} car{'s' if count != 1 else ''} found"
    if prefs.get("preferred_cities"):
        cars_summary += f" in {', '.join(prefs['preferred_cities'])}"

    streamed_text = ""
    async for chunk in llm_stream.astream([
        SystemMessage(content=RESPONSE_SYSTEM.format(
            message=last_message,
            cars_summary=cars_summary,
        )),
        HumanMessage(content=last_message),
    ]):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        streamed_text += content

    # Step 4: Proactive new-match check
    new_match_ads = []
    try:
        if pool and prefs:
            from app.db.queries import get_new_matching_ads
            import time
            created_at_dt = None
            session_start = config["configurable"].get("session_start")
            if session_start:
                import datetime
                created_at_dt = datetime.datetime.fromtimestamp(session_start)
            if created_at_dt:
                new_ads = await get_new_matching_ads(pool, created_at_dt, prefs)
                for a in new_ads:
                    ad = {
                        "id": str(a["id"]),
                        "brand": a["brand"],
                        "model": a["model"],
                        "year": a["year"],
                        "price": float(a["price"]),
                        "city": a["city"],
                        "_is_new_match": True,
                    }
                    new_match_ads.append(ad)
    except Exception:
        pass

    all_ads = ads + new_match_ads

    return {
        "retrieved_ads": all_ads,
        "node_response": streamed_text,
    }
