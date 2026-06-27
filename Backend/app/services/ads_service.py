from uuid import UUID
import asyncpg
from typing import List
from app.db.queries import ads as ads_queries
from app.db.queries import favorites as fav_queries


async def get_ad_response(
    pool: asyncpg.Pool,
    ad: dict,
    current_user_id: UUID | None = None,
    include_seller: bool = True,
) -> dict:
    ad_id = ad["id"]
    images = await ads_queries.get_ad_images(pool, ad_id)
    cover = images[0]["url"] if images else None

    is_fav = False
    if current_user_id:
        is_fav = await fav_queries.is_favorited(pool, current_user_id, ad_id)

    result = {
        "id": str(ad["id"]),
        "user_id": str(ad["user_id"]),
        "brand": ad["brand"],
        "model": ad["model"],
        "year": ad["year"],
        "price": float(ad["price"]),
        "condition": ad["condition"],
        "km_driven": ad["km_driven"],
        "color": ad.get("color"),
        "body_type": ad["body_type"],
        "transmission": ad["transmission"],
        "fuel_type": ad["fuel_type"],
        "cc_range": ad.get("cc_range"),
        "special_conditions": ad.get("special_conditions"),
        "description": ad.get("description"),
        "city": ad["city"],
        "cover_image_url": cover,
        "images": images,
        "views_count": ad["views_count"],
        "is_favorited": is_fav,
        "qdrant_synced": ad["qdrant_synced"],
        "created_at": ad["created_at"],
        "updated_at": ad["updated_at"],
    }

    if include_seller:
        from app.db.queries.users import get_user_by_id
        seller = await get_user_by_id(pool, ad["user_id"])
        result["seller"] = {
            "name": seller["name"] if seller else "Unknown",
            "phone": seller.get("phone"),
            "avatar_url": seller.get("avatar_url"),
        }

    return result


async def batch_ad_response(
    pool: asyncpg.Pool,
    ads: List[dict],
    current_user_id: UUID | None = None,
) -> List[dict]:
    if not ads:
        return []
    ad_ids = [a["id"] for a in ads]
    images_map = await ads_queries.batch_get_ad_images(pool, ad_ids)
    results = []
    for ad in ads:
        aid = str(ad["id"])
        images = images_map.get(aid, [])
        cover = images[0]["url"] if images else None
        is_fav = False
        if current_user_id:
            is_fav = await fav_queries.is_favorited(pool, current_user_id, ad["id"])
        results.append({
            "id": aid,
            "user_id": str(ad["user_id"]),
            "brand": ad["brand"],
            "model": ad["model"],
            "year": ad["year"],
            "price": float(ad["price"]),
            "condition": ad["condition"],
            "km_driven": ad["km_driven"],
            "color": ad.get("color"),
            "body_type": ad["body_type"],
            "transmission": ad["transmission"],
            "fuel_type": ad["fuel_type"],
            "cc_range": ad.get("cc_range"),
            "special_conditions": ad.get("special_conditions"),
            "description": ad.get("description"),
            "city": ad["city"],
            "cover_image_url": cover,
            "images": images,
            "views_count": ad["views_count"],
            "is_favorited": is_fav,
            "qdrant_synced": ad["qdrant_synced"],
            "created_at": ad["created_at"],
            "updated_at": ad["updated_at"],
        })
    return results
