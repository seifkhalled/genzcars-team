import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient
from app.core.embedder import Embedder
from app.core.qdrant_client import QdrantSearch
from app.core.hallucination_guard import build_grounding_block, validate_response
import asyncpg


async def handle(
    message: str,
    session: dict,
    llm: GeminiClient,
    embedder: Embedder,
    qdrant: QdrantSearch,
    pool: asyncpg.Pool,
    ad_payload: dict,
) -> AsyncGenerator[str, None]:
    grounding = build_grounding_block(ad_payload)
    system = (
        f"{grounding}\n\n"
        "You are a car advisor. Answer questions about this specific car using ONLY the verified data above. "
        "If asked about things not in the data, say you don't have that information. "
        "Always respond in the same language the user is writing in."
    )

    full_response = ""
    async for chunk in llm.stream(system, session.get("history", []), message):
        full_response += chunk
        yield json.dumps({"type": "token", "content": chunk})

    full_response = validate_response(full_response, ad_payload)

    try:
        text_to_embed = (
            f"{ad_payload.get('brand', '')} {ad_payload.get('model', '')} "
            f"{ad_payload.get('year', '')} {ad_payload.get('body_type', '')}"
        ).lower()
        vector = embedder.encode(text_to_embed)
        similar = qdrant.search(
            vector=vector,
            limit=3,
            exclude_ad_id=str(ad_payload.get("ad_id", "")),
        )
        similar_ads = []
        for s in similar[:2]:
            similar_ads.append({
                "id": s.get("ad_id", s["id"]),
                "brand": s.get("brand", ""),
                "model": s.get("model", ""),
                "year": s.get("year", 0),
                "price": float(s.get("price", 0)),
                "city": s.get("city", ""),
                "cover_image_url": s.get("cover_image_url", ""),
                "condition": s.get("condition", ""),
            })
        if similar_ads:
            yield json.dumps({"type": "similar_cars", "content": similar_ads})
    except Exception:
        pass

    yield json.dumps({"type": "done", "content": None})
