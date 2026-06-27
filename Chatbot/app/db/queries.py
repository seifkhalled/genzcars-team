import asyncpg
from typing import List
from uuid import UUID


async def upsert_user_preferences(pool: asyncpg.Pool, session_token: str, user_id: str | None, prefs: dict) -> None:
    fields = {
        "user_id": user_id,
        "budget_min": prefs.get("budget_min"),
        "budget_max": prefs.get("budget_max"),
        "preferred_brands": prefs.get("preferred_brands"),
        "preferred_body_types": prefs.get("preferred_body_types"),
        "preferred_fuel_types": prefs.get("preferred_fuel_types"),
        "preferred_transmission": prefs.get("preferred_transmission"),
        "preferred_cities": prefs.get("preferred_cities"),
        "max_km_driven": prefs.get("max_km_driven"),
        "year_min": prefs.get("year_min"),
        "year_max": prefs.get("year_max"),
        "use_case": prefs.get("use_case"),
        "is_seller": prefs.get("is_seller", False),
        "seller_car_brand": prefs.get("seller_car_brand"),
        "seller_car_model": prefs.get("seller_car_model"),
        "seller_car_year": prefs.get("seller_car_year"),
        "seller_asking_price": prefs.get("seller_asking_price"),
        "seller_intent": prefs.get("seller_intent"),
        "intent_history": prefs.get("intent_history"),
        "turn_count": prefs.get("turn_count", 0),
    }

    col_names = list(fields.keys())
    placeholders = [f"${i+1}" for i in range(len(col_names))]
    updates = [f"{k} = EXCLUDED.{k}" for k in col_names]

    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO user_preferences (session_token, {', '.join(col_names)})
            VALUES ($1, {', '.join(placeholders)})
            ON CONFLICT (session_token)
            DO UPDATE SET {', '.join(updates)}
            """,
            session_token,
            *[fields[k] for k in col_names],
        )


async def insert_chat_message(
    pool: asyncpg.Pool,
    session_token: str,
    role: str,
    content: str,
    node_used: str | None = None,
    referenced_ad_ids: List[str] | None = None,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (session_token, role, content, node_used, referenced_ad_ids) "
            "VALUES ($1, $2, $3, $4, $5)",
            session_token, role, content, node_used, referenced_ad_ids,
        )


async def get_chat_history(pool: asyncpg.Pool, session_token: str) -> List[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content, node_used, created_at FROM chat_messages "
            "WHERE session_token = $1 ORDER BY created_at",
            session_token,
        )
        return [dict(r) for r in rows]


async def get_preferences(pool: asyncpg.Pool, session_token: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_preferences WHERE session_token = $1",
            session_token,
        )
        return dict(row) if row else None


async def get_new_matching_ads(
    pool: asyncpg.Pool,
    session_created_at,
    prefs: dict,
) -> List[dict]:
    conditions = ["is_active = TRUE", "created_at > $1"]
    params = [session_created_at]
    idx = 2
    if prefs.get("preferred_brands"):
        conditions.append(f"brand = ANY(${idx}::varchar[])")
        params.append(prefs["preferred_brands"])
        idx += 1
    if prefs.get("preferred_cities"):
        conditions.append(f"city = ANY(${idx}::varchar[])")
        params.append(prefs["preferred_cities"])
        idx += 1
    if prefs.get("budget_max"):
        conditions.append(f"price <= ${idx}")
        params.append(prefs["budget_max"])
        idx += 1
    if prefs.get("budget_min"):
        conditions.append(f"price >= ${idx}")
        params.append(prefs["budget_min"])
        idx += 1

    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT id, brand, model, year, price, city, condition, body_type, "
            f"transmission, fuel_type, km_driven, created_at FROM ads WHERE {where} "
            f"ORDER BY created_at DESC LIMIT 5",
            *params,
        )
        return [dict(r) for r in rows]


async def get_ad_images_by_ids(pool: asyncpg.Pool, ad_ids: List[UUID]) -> dict:
    if not ad_ids:
        return {}
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, ad_id, url, order_index FROM ad_images "
            "WHERE ad_id = ANY($1::uuid[]) ORDER BY order_index",
            ad_ids,
        )
    result: dict = {}
    for r in rows:
        d = dict(r)
        aid = str(d["ad_id"])
        if aid not in result:
            result[aid] = []
        result[aid].append({"id": str(d["id"]), "url": d["url"], "order_index": d["order_index"]})
    return result
