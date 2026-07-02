import asyncpg
from fastapi import APIRouter, Depends
from app.dependencies import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats(pool: asyncpg.Pool = Depends(get_db)):
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

    return {
        "total_ads": total_ads_row or 0,
        "total_cities": total_cities_row or 0,
        "total_users": total_users_row or 0,
        "total_chat_sessions": chat_sessions_row or 0,
    }
