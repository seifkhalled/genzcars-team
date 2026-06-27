import logging
import time
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from qdrant_client import QdrantClient

from app.config import settings
from app.core.llm import get_llm
from app.core.embedder import Embedder
from app.core.qdrant import QdrantSearch
from app.graph.builder import build_graph
from app.routers import chat as chat_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Chatbot service starting...")

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)
    app.state.pool = pool
    app.state.session_start = time.time()

    try:
        embedder = Embedder("all-MiniLM-L6-v2")
        logger.info("all-MiniLM-L6-v2 embedding model loaded")
    except Exception as e:
        embedder = None
        logger.warning("Failed to load embedding model: %s", e)
    app.state.embedder = embedder

    qdrant_client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
    qdrant_search = QdrantSearch(qdrant_client)
    app.state.qdrant_search = qdrant_search

    app.state.llm_fast = get_llm(streaming=False)
    app.state.llm_stream = get_llm(streaming=True)

    app.state.graph = build_graph()
    app.state.sse_queues = {}

    logger.info("Graph compiled with MemorySaver checkpointer")

    yield

    logger.info("Chatbot service shutting down...")
    if pool:
        await pool.close()


app = FastAPI(
    title="Cars Marketplace Chatbot",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(chat_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
