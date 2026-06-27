from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
