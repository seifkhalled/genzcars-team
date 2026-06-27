from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.http import models
import asyncpg

from app.config import settings


def build_embedding_text(ad_data: dict) -> str:
    fields = [
        ad_data.get("brand", ""),
        ad_data.get("model", ""),
        str(ad_data.get("year", "")),
        ad_data.get("body_type", ""),
        ad_data.get("fuel_type", ""),
        ad_data.get("transmission", ""),
        ad_data.get("condition", ""),
        ad_data.get("city", ""),
        ad_data.get("cc_range", ""),
        ad_data.get("description", ""),
        ad_data.get("special_conditions", ""),
    ]
    return " ".join(f for f in fields if f).lower()


def embed_text(embedder, text: str) -> list[float]:
    return list(next(embedder.embed([text])))


def build_payload(ad_data: dict, cover_image_url: str | None = None) -> dict:
    from datetime import datetime
    created = ad_data.get("created_at")
    if isinstance(created, datetime):
        ts = int(created.timestamp())
    else:
        ts = 0
    return {
        "ad_id": str(ad_data["id"]),
        "brand": ad_data.get("brand", ""),
        "model": ad_data.get("model", ""),
        "year": ad_data.get("year", 0),
        "price": float(ad_data.get("price", 0)),
        "condition": ad_data.get("condition", ""),
        "km_driven": ad_data.get("km_driven", 0),
        "fuel_type": ad_data.get("fuel_type", ""),
        "transmission": ad_data.get("transmission", ""),
        "body_type": ad_data.get("body_type", ""),
        "city": ad_data.get("city", ""),
        "cc_range": ad_data.get("cc_range", ""),
        "is_active": ad_data.get("is_active", True),
        "cover_image_url": cover_image_url or "",
        "created_at": ts,
    }


async def index_ad(
    pool: asyncpg.Pool,
    qdrant: QdrantClient,
    embedder,
    ad_id: UUID,
    ad_data: dict,
    cover_image_url: str | None = None,
) -> None:
    text = build_embedding_text(ad_data)
    vector = embed_text(embedder, text)
    payload = build_payload(ad_data, cover_image_url)

    qdrant.upsert(
        collection_name=settings.qdrant_collection,
        points=[models.PointStruct(id=str(ad_id), vector=vector, payload=payload)],
    )

    from app.db.queries.ads import set_qdrant_synced
    await set_qdrant_synced(pool, ad_id, True)


async def delete_ad_from_qdrant(
    pool: asyncpg.Pool,
    qdrant: QdrantClient,
    ad_id: UUID,
) -> None:
    qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.PointIdsList(points=[str(ad_id)]),
    )

    from app.db.queries.ads import set_qdrant_synced
    await set_qdrant_synced(pool, ad_id, False)
