import asyncpg
from supabase import Client, create_client
from qdrant_client import QdrantClient

from app.config import settings


async def create_pool() -> asyncpg.Pool:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    return pool


def create_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def create_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
