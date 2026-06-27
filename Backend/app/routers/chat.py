from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncpg
import httpx
import json
import secrets

from app.dependencies import get_db, get_optional_user

router = APIRouter(prefix="/chat", tags=["chat"])
CHATBOT_URL = "http://chatbot:8001"


class SessionRequest(BaseModel):
    context_ad_id: str | None = None


class MessageRequest(BaseModel):
    session_token: str
    message: str
    context_ad_id: str | None = None


@router.post("/session")
async def create_session(
    body: SessionRequest,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID | None = Depends(get_optional_user),
):
    if user_id:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT session_token FROM chat_sessions "
                "WHERE user_id = $1 AND last_active > NOW() - INTERVAL '24 hours' "
                "ORDER BY last_active DESC LIMIT 1",
                user_id,
            )
            if row:
                return {"session_token": row["session_token"], "is_new": False}

    session_token = secrets.token_urlsafe(48)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_sessions (user_id, session_token, context_ad_id) "
            "VALUES ($1, $2, $3)",
            user_id, session_token, body.context_ad_id,
        )
    return {"session_token": session_token, "is_new": True}


@router.post("/message")
async def send_message(
    body: MessageRequest,
    pool: asyncpg.Pool = Depends(get_db),
    user_id: UUID | None = Depends(get_optional_user),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM chat_sessions WHERE session_token = $1",
            body.session_token,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        await conn.execute(
            "UPDATE chat_sessions SET last_active = NOW() WHERE session_token = $1",
            body.session_token,
        )

    async def generate():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"{CHATBOT_URL}/message",
                json={
                    "session_token": body.session_token,
                    "message": body.message,
                    "context_ad_id": body.context_ad_id,
                    "user_id": str(user_id) if user_id else None,
                },
            ) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        yield f"data: {chunk}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history/{session_token}")
async def get_history(
    session_token: str,
    pool: asyncpg.Pool = Depends(get_db),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM chat_sessions WHERE session_token = $1",
            session_token,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CHATBOT_URL}/history/{session_token}")
        resp.raise_for_status()
        return resp.json()
