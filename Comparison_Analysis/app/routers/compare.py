import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.request import CompareRequest
from app.pipeline.runner import run

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])


@router.post("/compare")
async def compare_ads(request: CompareRequest, req: Request):
    async def event_stream():
        try:
            async for event in run(request, req.app.state):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Comparison pipeline failed")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An unexpected error occurred'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': None})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def health():
    return {"status": "ok"}
