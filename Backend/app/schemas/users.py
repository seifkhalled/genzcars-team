from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
