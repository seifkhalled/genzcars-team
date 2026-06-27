from uuid import UUID
import asyncpg
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.queries.users import get_user_by_email, insert_user


async def register_user(
    pool: asyncpg.Pool,
    name: str,
    email: str,
    phone: str | None,
    password: str,
) -> dict:
    existing = await get_user_by_email(pool, email)
    if existing:
        from app.core.exceptions import ConflictException
        raise ConflictException("Email already exists")

    pw_hash = hash_password(password)
    user = await insert_user(pool, name, email, phone, pw_hash)
    user_id = user["id"]
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "avatar_url": user.get("avatar_url"),
        },
    }


async def login_user(
    pool: asyncpg.Pool,
    email: str,
    password: str,
) -> dict:
    from app.core.exceptions import UnauthorizedException
    user = await get_user_by_email(pool, email)
    if not user or not verify_password(password, user["password_hash"]):
        raise UnauthorizedException("Invalid email or password")

    user_id = user["id"]
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "avatar_url": user.get("avatar_url"),
        },
    }
