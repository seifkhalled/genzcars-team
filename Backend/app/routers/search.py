from uuid import UUID
from fastapi import APIRouter, Depends, Request
from typing import Optional, List
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
import asyncpg

from app.config import settings
from app.dependencies import get_db, get_qdrant, get_embedder, get_optional_user
from app.db.queries import ads as ads_queries
from app.services.ads_service import batch_ad_response
from app.services.indexing_pipeline import embed_text

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str,
    limit: int = 10,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    city: Optional[str] = None,
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    transmission: Optional[str] = None,
    body_type: Optional[str] = None,
    pool: asyncpg.Pool = Depends(get_db),
    qdrant: QdrantClient = Depends(get_qdrant),
    embedder = Depends(get_embedder),
    current_user: UUID | None = Depends(get_optional_user),
):
    if limit > 30:
        limit = 30

    vector = embed_text(embedder, q.lower())

    must_conditions = [qmodels.FieldCondition(
        key="is_active", match=qmodels.MatchValue(value=True)
    )]
    if price_min is not None:
        must_conditions.append(qmodels.FieldCondition(
            key="price", range=qmodels.Range(gte=price_min)
        ))
    if price_max is not None:
        must_conditions.append(qmodels.FieldCondition(
            key="price", range=qmodels.Range(lte=price_max)
        ))
    if city:
        must_conditions.append(qmodels.FieldCondition(
            key="city", match=qmodels.MatchValue(value=city)
        ))
    if brand:
        must_conditions.append(qmodels.FieldCondition(
            key="brand", match=qmodels.MatchValue(value=brand)
        ))
    if fuel_type:
        must_conditions.append(qmodels.FieldCondition(
            key="fuel_type", match=qmodels.MatchValue(value=fuel_type)
        ))
    if transmission:
        must_conditions.append(qmodels.FieldCondition(
            key="transmission", match=qmodels.MatchValue(value=transmission)
        ))
    if body_type:
        must_conditions.append(qmodels.FieldCondition(
            key="body_type", match=qmodels.MatchValue(value=body_type)
        ))

    query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

    search_result = qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

    ad_ids = []
    score_map = {}
    for point in search_result:
        aid = UUID(point.payload.get("ad_id", point.id))
        ad_ids.append(aid)
        score_map[str(aid)] = point.score

    ads = await ads_queries.get_ads_by_ids(pool, ad_ids)
    ad_responses = await batch_ad_response(pool, ads, current_user)

    ad_map = {a["id"]: a for a in ad_responses}
    results = []
    for aid in ad_ids:
        aid_str = str(aid)
        if aid_str in ad_map:
            results.append({"score": score_map[aid_str], "ad": ad_map[aid_str]})

    return {"query": q, "ads": [r["ad"] for r in results], "total": len(results)}
