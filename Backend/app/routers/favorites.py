from uuid import UUID
from fastapi import APIRouter, Depends
import asyncpg

from app.schemas.ads import AdListResponse
from app.dependencies import get_db, get_current_user
from app.db.queries import favorites as fav_queries
from app.db.queries import ads as ads_queries
from app.services.ads_service import batch_ad_response
from app.core.exceptions import NotFoundException

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/{ad_id}")
async def add_favorite(
    ad_id: UUID,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    ad = await ads_queries.get_ad_by_id(pool, ad_id)
    if not ad or not ad["is_active"]:
        raise NotFoundException("Ad not found")
    await fav_queries.add_favorite(pool, user_id, ad_id)
    return {"message": "saved"}


@router.delete("/{ad_id}")
async def remove_favorite(
    ad_id: UUID,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    await fav_queries.remove_favorite(pool, user_id, ad_id)
    return {"message": "removed"}


@router.get("", response_model=AdListResponse)
async def get_favorites(
    page: int = 1,
    limit: int = 12,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    result = await fav_queries.get_user_favorites(pool, user_id, page=page, limit=limit)
    result["ads"] = await batch_ad_response(pool, result["ads"], user_id)
    return result
