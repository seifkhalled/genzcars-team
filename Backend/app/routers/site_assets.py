from fastapi import APIRouter, Request
from app.config import settings

router = APIRouter(prefix="/site-assets", tags=["site-assets"])


@router.get("")
async def get_site_assets(request: Request):
    redis = getattr(request.app.state, "redis", None)
    if redis:
        cached = await redis.get_json("cache:site-assets")
        if cached is not None:
            return cached

    bucket = settings.supabase_site_assets_bucket
    base = f"{settings.supabase_url}/storage/v1/object/public/{bucket}"
    payload = {
        "logo_url": f"{base}/logo.png",
        "wallpaper_url": f"{base}/wallpaper.jpg",
    }
    if redis:
        await redis.set_json("cache:site-assets", payload, ttl=3600)
    return payload
