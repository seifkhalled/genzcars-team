import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
import asyncpg

from app.dependencies import get_db
from app.services.comparison import ComparisonService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare-ai", tags=["compare-ai"])


class CompareAiRequest(BaseModel):
    ad_id_1: str
    ad_id_2: str

    @field_validator("ad_id_1", "ad_id_2")
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        UUID(v)
        return v


@router.post("")
async def compare_ai(
    body: CompareAiRequest,
    request: Request,
    pool: asyncpg.Pool = Depends(get_db),
):
    redis = getattr(request.app.state, "redis", None)
    cache_key = f"cache:compare-ai:{body.ad_id_1}:{body.ad_id_2}"

    if redis:
        cached = await redis.get_json(cache_key)
        if cached is not None:
            async def stream_cached():
                for event in cached:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            return StreamingResponse(
                stream_cached(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    llm = request.app.state.llm
    service = ComparisonService(pool=pool, llm=llm)
    events = []

    async def event_stream():
        async for event in service.run(body.ad_id_1, body.ad_id_2):
            events.append(event)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        if redis:
            await redis.set_json(cache_key, events, ttl=1800)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
