from fastapi import APIRouter, Request
from app.config import settings

router = APIRouter(prefix="/site-assets", tags=["site-assets"])


@router.get("")
async def get_site_assets(request: Request):
    bucket = settings.supabase_site_assets_bucket
    base = f"{settings.supabase_url}/storage/v1/object/public/{bucket}"
    return {
        "logo_url": f"{base}/logo.png",
        "wallpaper_url": f"{base}/wallpaper.jpg",
    }
