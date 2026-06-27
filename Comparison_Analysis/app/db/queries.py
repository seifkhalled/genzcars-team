import asyncpg


async def fetch_ads_for_comparison(pool: asyncpg.Pool, ad_ids: list[str]) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                a.*,
                i.url AS cover_image_url
            FROM ads a
            LEFT JOIN ad_images i ON i.ad_id = a.id AND i.order_index = 0
            WHERE a.id = ANY($1::uuid[])
              AND a.is_active = TRUE
            """,
            ad_ids,
        )
    result = [dict(r) for r in rows]

    found_ids = {str(r["id"]) for r in result}
    missing = [aid for aid in ad_ids if aid not in found_ids]
    if missing:
        raise ValueError(
            f"Ads not found or inactive: {', '.join(missing)}"
        )

    return result
