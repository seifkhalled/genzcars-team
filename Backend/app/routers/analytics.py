import asyncpg
from fastapi import APIRouter, Depends, Request
from app.dependencies import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats(
    pool: asyncpg.Pool = Depends(get_db),
    request: Request = None,
):
    redis = getattr(request.app.state, "redis", None) if request else None
    if redis:
        cached = await redis.get_json("cache:analytics-stats")
        if cached is not None:
            return cached

    async with pool.acquire() as conn:
        total_ads_row = await conn.fetchval(
            "SELECT COUNT(*) FROM ads WHERE is_active = TRUE"
        )
        total_cities_row = await conn.fetchval(
            "SELECT COUNT(DISTINCT city) FROM ads WHERE is_active = TRUE AND city IS NOT NULL"
        )
        total_users_row = await conn.fetchval(
            "SELECT COUNT(*) FROM users"
        )
        chat_sessions_row = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_sessions"
        )

    payload = {
        "total_ads": total_ads_row or 0,
        "total_cities": total_cities_row or 0,
        "total_users": total_users_row or 0,
        "total_chat_sessions": chat_sessions_row or 0,
    }
    if redis:
        await redis.set_json("cache:analytics-stats", payload, ttl=300)
    return payload
