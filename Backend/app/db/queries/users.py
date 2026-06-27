import asyncpg
from uuid import UUID


async def insert_user(
    pool: asyncpg.Pool,
    name: str,
    email: str,
    phone: str | None,
    password_hash: str,
) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (name, email, phone, password_hash)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, email, phone, avatar_url, created_at
            """,
            name, email, phone, password_hash,
        )
        return dict(row) if row else None


async def get_user_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email
        )
        return dict(row) if row else None


async def get_user_by_id(pool: asyncpg.Pool, user_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, phone, avatar_url, created_at FROM users WHERE id = $1",
            user_id,
        )
        return dict(row) if row else None


async def update_user(
    pool: asyncpg.Pool,
    user_id: UUID,
    name: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
) -> dict | None:
    sets = []
    values = []
    idx = 1
    if name is not None:
        sets.append(f"name = ${idx}")
        values.append(name)
        idx += 1
    if phone is not None:
        sets.append(f"phone = ${idx}")
        values.append(phone)
        idx += 1
    if avatar_url is not None:
        sets.append(f"avatar_url = ${idx}")
        values.append(avatar_url)
        idx += 1
    if not sets:
        return await get_user_by_id(pool, user_id)
    values.append(user_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE users SET {', '.join(sets)} WHERE id = ${idx} "
            "RETURNING id, name, email, phone, avatar_url, created_at",
            *values,
        )
        return dict(row) if row else None
