import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient
from app.core.embedder import Embedder
from app.core.qdrant_client import QdrantSearch
from app.core.hallucination_guard import verify_results
import asyncpg
from uuid import UUID


async def handle(
    message: str,
    session: dict,
    llm: GeminiClient,
    embedder: Embedder,
    qdrant: QdrantSearch,
    pool: asyncpg.Pool,
) -> AsyncGenerator[str, None]:
    yield json.dumps({"type": "status", "content": "Searching listings..."})

    prefs = session.get("preferences", {})
    enhanced_query_parts = [message]
    if prefs.get("preferred_cities"):
        enhanced_query_parts.append("in " + " ".join(prefs["preferred_cities"]))
    if prefs.get("budget_max"):
        enhanced_query_parts.append(f"under {prefs['budget_max']}")
    if prefs.get("preferred_brands"):
        enhanced_query_parts.append(" ".join(prefs["preferred_brands"]))
    if prefs.get("use_case"):
        enhanced_query_parts.append(prefs["use_case"])
    enhanced_query = " ".join(enhanced_query_parts).lower()

    vector = embedder.encode(enhanced_query)

    results = qdrant.search(
        vector=vector,
        limit=5,
        price_min=prefs.get("budget_min"),
        price_max=prefs.get("budget_max"),
        city=prefs.get("preferred_cities", [None])[0] if prefs.get("preferred_cities") else None,
        brand=prefs.get("preferred_brands", [None])[0] if prefs.get("preferred_brands") else None,
        year_min=prefs.get("year_min"),
        year_max=prefs.get("year_max"),
    )

    results = verify_results(results)

    ad_ids = []
    for r in results:
        try:
            ad_ids.append(UUID(r.get("ad_id", r["id"])))
        except (ValueError, KeyError):
            continue

    ads = []
    if ad_ids:
        from app.db.queries import get_ad_images_by_ids
        images_map = await get_ad_images_by_ids(pool, ad_ids)
        for r in results:
            aid = r.get("ad_id", r["id"])
            try:
                ad = {
                    "id": aid,
                    "user_id": str(r.get("user_id", "")),
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
                    "cc_range": r.get("cc_range", ""),
                    "cover_image_url": r.get("cover_image_url", ""),
                    "images": images_map.get(aid, []),
                    "views_count": 0,
                    "score": r.get("score", 0),
                }
                ads.append(ad)
            except (ValueError, KeyError):
                continue

    count = len(ads)
    intro = f"I found {count} great option{'s' if count != 1 else ''} for you"
    if prefs.get("preferred_cities"):
        intro += f" in {', '.join(prefs['preferred_cities'])}"

    system = (
        "You are a helpful car marketplace assistant. Generate a short conversational "
        "intro (2-3 sentences) about the search results. "
        "Always respond in the same language the user is writing in."
    )
    async for chunk in llm.stream(system, [], f"User searched: {message}. Found {count} cars. Say a friendly intro."):
        yield json.dumps({"type": "token", "content": chunk})

    yield json.dumps({"type": "cars", "content": ads})

    try:
        from app.db.queries import get_new_matching_ads
        prefs = session.get("preferences", {})
        created_at_dt = None
        if session.get("created_at"):
            import datetime
            created_at_dt = datetime.datetime.fromtimestamp(session["created_at"])
        if created_at_dt and prefs:
            new_ads = await get_new_matching_ads(pool, created_at_dt, prefs)
            if new_ads:
                yield json.dumps({"type": "new_match", "content": [
                    {
                        "id": str(a["id"]),
                        "brand": a["brand"],
                        "model": a["model"],
                        "year": a["year"],
                        "price": float(a["price"]),
                        "city": a["city"],
                    } for a in new_ads
                ]})
    except Exception:
        pass

    yield json.dumps({"type": "done", "content": None})
