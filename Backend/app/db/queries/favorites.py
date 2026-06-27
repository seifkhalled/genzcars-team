import asyncpg
from uuid import UUID


async def add_favorite(pool: asyncpg.Pool, user_id: UUID, ad_id: UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO favorites (user_id, ad_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            user_id, ad_id,
        )


async def remove_favorite(pool: asyncpg.Pool, user_id: UUID, ad_id: UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM favorites WHERE user_id = $1 AND ad_id = $2",
            user_id, ad_id,
        )


async def is_favorited(pool: asyncpg.Pool, user_id: UUID, ad_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchval(
            "SELECT 1 FROM favorites WHERE user_id = $1 AND ad_id = $2",
            user_id, ad_id,
        )
        return row is not None


async def get_user_favorites(
    pool: asyncpg.Pool,
    user_id: UUID,
    page: int = 1,
    limit: int = 12,
) -> dict:
    offset = (page - 1) * limit
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM favorites WHERE user_id = $1", user_id
        ) or 0
        rows = await conn.fetch(
            """
            SELECT a.* FROM ads a
            JOIN favorites f ON f.ad_id = a.id
            WHERE f.user_id = $1 AND a.is_active = TRUE
            ORDER BY f.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset,
        )
    items = [dict(r) for r in rows]
    pages = (total + limit - 1) // limit
    return {"ads": items, "total": total, "page": page, "limit": limit, "total_pages": pages}
