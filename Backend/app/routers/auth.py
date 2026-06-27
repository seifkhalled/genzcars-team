from fastapi import APIRouter, Depends, Response, Request
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.dependencies import get_db
from app.services.auth_service import register_user, login_user
from app.core.security import decode_token, create_access_token
from app.core.exceptions import UnauthorizedException
from app.config import settings
import asyncpg

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_KWARGS = {
    "path": "/",
    "httponly": True,
    "secure": settings.environment == "production",
    "samesite": "lax",
}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(key="access_token", value=access_token, max_age=3600, **COOKIE_KWARGS)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=2592000, **COOKIE_KWARGS)


@router.post(
    "/register",
    status_code=201,
    response_model=TokenResponse,
    responses={409: {"model": ErrorResponse}},
)
async def register(body: RegisterRequest, response: Response, pool: asyncpg.Pool = Depends(get_db)):
    result = await register_user(pool, body.name, body.email, body.phone, body.password)
    set_auth_cookies(response, result["access_token"], result["refresh_token"])
    return result


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(body: LoginRequest, response: Response, pool: asyncpg.Pool = Depends(get_db)):
    result = await login_user(pool, body.email, body.password)
    set_auth_cookies(response, result["access_token"], result["refresh_token"])
    return result


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, pool: asyncpg.Pool = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise UnauthorizedException("No refresh token")
    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid or expired refresh token")
    new_access = create_access_token(payload["sub"])
    response.set_cookie(key="access_token", value=new_access, max_age=3600, **COOKIE_KWARGS)
    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", **COOKIE_KWARGS)
    response.delete_cookie(key="refresh_token", **COOKIE_KWARGS)
    return {"message": "logged out"}
