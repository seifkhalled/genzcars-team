import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None

    async def init(self):
        self._client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._client.ping()
            logger.info("Connected to Redis at %s", self.redis_url)
        except Exception as e:
            logger.warning("Redis connection failed — caching disabled: %s", e)
            self._client = None

    async def close(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Optional[str]:
        if not self._client:
            return None
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        if not self._client:
            return
        await self._client.set(key, value, ex=ttl)

    async def get_json(self, key: str) -> Any:
        val = await self.get(key)
        return json.loads(val) if val else None

    async def set_json(self, key: str, value: Any, ttl: int = 300):
        await self.set(key, json.dumps(value, ensure_ascii=False, default=str), ttl=ttl)

    async def delete_pattern(self, pattern: str):
        if not self._client:
            return
        keys = await self._client.keys(pattern)
        if keys:
            await self._client.delete(*keys)
            logger.info("Deleted %d Redis keys matching %s", len(keys), pattern)
