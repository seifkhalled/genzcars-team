from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from qdrant_client.http import models as qmodels

from app.config import settings
from app.core.middleware import setup_cors
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    FileTooLargeException,
    UnsupportedMediaTypeException,
)
from app.schemas.common import ErrorResponse
from app.db.client import create_pool, create_supabase_client, create_qdrant_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    app.state.db = await create_pool()
    app.state.supabase = create_supabase_client()
    app.state.qdrant = create_qdrant_client()
    collections = app.state.qdrant.get_collections()
    if settings.qdrant_collection not in [c.name for c in collections.collections]:
        app.state.qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", settings.qdrant_collection)
    try:
        from fastembed import TextEmbedding
        app.state.embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        logger.info("all-MiniLM-L6-v2 embedding model loaded via fastembed")
    except Exception as e:
        app.state.embedder = None
        logger.warning("Failed to load embedding model: %s", e)
    yield
    logger.info("Shutting down...")
    if app.state.db:
        await app.state.db.close()


app = FastAPI(
    title="Cars Marketplace API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

setup_cors(app)


@app.exception_handler(NotFoundException)
async def not_found_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="not_found",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(UnauthorizedException)
async def unauthorized_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="unauthorized",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(ForbiddenException)
async def forbidden_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="forbidden",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(ConflictException)
async def conflict_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="conflict",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(FileTooLargeException)
async def file_too_large_handler(request: Request, exc: FileTooLargeException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="file_too_large",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(UnsupportedMediaTypeException)
async def unsupported_media_handler(request: Request, exc: UnsupportedMediaTypeException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="unsupported_media_type",
            message=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def internal_handler(request: Request, exc: Exception):
    logger.exception("Internal error")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred",
            status_code=500,
        ).model_dump(),
    )


from app.routers import auth, users, ads, favorites, search, chat, compare

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(ads.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(compare.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
