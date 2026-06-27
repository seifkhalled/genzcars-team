from typing import Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_token: str
    message: str
    user_id: str | None = None
    context_ad_id: str | None = None


class SSEEvent(BaseModel):
    type: str
    content: Any = None
