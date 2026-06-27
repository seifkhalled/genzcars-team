from uuid import UUID
from fastapi import Depends, Request
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException


async def get_db(request: Request):
    return request.app.state.db


async def get_qdrant(request: Request):
    return request.app.state.qdrant


async def get_embedder(request: Request):
    return request.app.state.embedder


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    return request.cookies.get("access_token")


async def get_current_user(request: Request):
    token = _extract_token(request)
    if not token:
        raise UnauthorizedException("Not authenticated")
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise UnauthorizedException("Invalid or expired token")
    return UUID(payload["sub"])


async def get_optional_user(request: Request) -> UUID | None:
    token = _extract_token(request)
    if not token:
        return None
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    return UUID(payload["sub"])
