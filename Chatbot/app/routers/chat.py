import json
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_token: str
    message: str
    user_id: str | None = None
    context_ad_id: str | None = None


@router.post("/message")
async def chat_message(request: ChatRequest, req: Request):
    app = req.app

    async def event_stream():
        session_token = request.session_token
        queue = asyncio.Queue()
        app.state.sse_queues[session_token] = queue

        try:
            config = {
                "configurable": {
                    "thread_id": request.session_token,
                    "llm_fast": app.state.llm_fast,
                    "llm_stream": app.state.llm_stream,
                    "embedder": app.state.embedder,
                    "qdrant_search": app.state.qdrant_search,
                    "db_pool": getattr(app.state, "pool", None),
                    "sse_queue": queue,
                    "session_start": getattr(app.state, "session_start", None),
                }
            }

            input_state = {
                "messages": [HumanMessage(content=request.message)],
                "session_token": request.session_token,
                "user_id": request.user_id,
                "context_ad_id": request.context_ad_id,
                "preferences": {},
                "next_node": "",
                "intent": "",
                "retrieved_ads": [],
                "similar_ads": [],
                "price_analysis": None,
                "node_response": "",
                "turn_count": 0,
                "intent_history": [],
            }

            graph = app.state.graph

            async def run_graph():
                async for _ in graph.astream(input_state, config=config, stream_mode="updates"):
                    pass

            run_task = asyncio.ensure_future(run_graph())

            done_count = 0
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    if event.get("type") == "done":
                        done_count += 1
                        if done_count >= 1:
                            yield f"data: {json.dumps(event)}\n\n"
                            break
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Request timed out'})}\n\n"
                    break

            await run_task

        finally:
            app.state.sse_queues.pop(session_token, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{session_token}")
async def get_history(session_token: str, req: Request):
    from app.db.queries import get_chat_history, get_preferences

    pool = req.app.state.pool
    messages = await get_chat_history(pool, session_token)
    prefs = await get_preferences(pool, session_token)
    return {
        "session_token": session_token,
        "messages": [
            {
                "role": m["role"],
                "content": m["content"],
                "node_used": m.get("node_used"),
                "created_at": m["created_at"].isoformat() if m.get("created_at") else None,
            }
            for m in messages
        ],
        "preferences": dict(prefs) if prefs else {},
        "turn_count": dict(prefs).get("turn_count", 0) if prefs else 0,
    }
