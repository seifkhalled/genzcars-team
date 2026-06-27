from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Request
import asyncpg

from app.schemas.users import UserResponse, UserUpdate
from app.schemas.ads import AdListResponse
from app.dependencies import get_db, get_current_user, get_optional_user
from app.db.queries import users as users_queries
from app.db.queries import ads as ads_queries
from app.services.ads_service import batch_ad_response
from app.core.exceptions import NotFoundException, UnsupportedMediaTypeException, FileTooLargeException
from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/webp", "image/png"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


@router.get("/me", response_model=UserResponse)
async def get_me(
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    user = await users_queries.get_user_by_id(pool, user_id)
    if not user:
        raise NotFoundException("User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    user = await users_queries.update_user(
        pool, user_id, name=body.name, phone=body.phone, avatar_url=body.avatar_url
    )
    if not user:
        raise NotFoundException("User not found")
    return user


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
    request: Request = None,
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise UnsupportedMediaTypeException("Only JPEG, WebP, and PNG allowed")
    contents = await file.read()
    if len(contents) > MAX_AVATAR_SIZE:
        raise FileTooLargeException("Avatar must be under 5MB")

    supabase = request.app.state.supabase
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    path = f"avatars/{user_id}.{ext}"
    url = supabase.storage.from_(settings.supabase_storage_bucket).upload(
        path=path,
        file=contents,
        file_options={"content-type": file.content_type, "upsert": "true"},
    )
    public_url = supabase.storage.from_(settings.supabase_storage_bucket).get_public_url(path)

    await users_queries.update_user(pool, user_id, avatar_url=public_url)
    return {"avatar_url": public_url}


@router.get("/{user_id}/ads", response_model=AdListResponse)
async def get_user_ads(
    user_id: UUID,
    page: int = 1,
    limit: int = 12,
    pool: asyncpg.Pool = Depends(get_db),
    current_user: UUID | None = Depends(get_optional_user),
):
    result = await ads_queries.list_ads(pool, page=page, limit=limit, user_id=user_id)
    result["ads"] = await batch_ad_response(pool, result["ads"], current_user)
    return result
