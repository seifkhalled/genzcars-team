from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import asyncpg
import httpx
import json

from app.dependencies import get_db
from app.db.queries import ads as ads_queries
from app.core.exceptions import NotFoundException

router = APIRouter(prefix="/compare", tags=["compare"])
COMPARISON_URL = "http://comparison:8002"


class CompareRequest(BaseModel):
    ad_ids: List[str]


@router.post("")
async def compare_ads(
    body: CompareRequest,
    pool: asyncpg.Pool = Depends(get_db),
):
    if len(body.ad_ids) < 2 or len(body.ad_ids) > 3:
        raise NotFoundException("Provide 2 or 3 ad IDs")

    ads = []
    for aid in body.ad_ids:
        ad = await ads_queries.get_ad_by_id(pool, UUID(aid))
        if not ad or not ad["is_active"]:
            raise NotFoundException(f"Ad {aid} not found")
        images = await ads_queries.get_ad_images(pool, ad["id"])
        ad_dict = dict(ad)
        ad_dict["images"] = images
        ads.append(ad_dict)

    async def generate():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{COMPARISON_URL}/compare",
                json={"ads": [
                    {
                        "id": str(a["id"]),
                        "brand": a["brand"],
                        "model": a["model"],
                        "year": a["year"],
                        "price": float(a["price"]),
                        "condition": a["condition"],
                        "km_driven": a["km_driven"],
                        "fuel_type": a["fuel_type"],
                        "transmission": a["transmission"],
                        "body_type": a["body_type"],
                        "city": a["city"],
                        "description": a.get("description"),
                        "images": a.get("images", []),
                    }
                    for a in ads
                ]},
            ) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        yield f"data: {chunk}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
