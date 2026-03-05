# backend/app/services/cache_service.py
"""
Redis cache service for JRO caching and Pub/Sub job progress events.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as redis
from app.config import settings
from app.schemas.jro_schema import JROSchema


class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(str(settings.REDIS_URL), decode_responses=True)

    async def get_jro(self, key: str) -> JROSchema | None:
        """Fetch a cached JRO by key."""
        data = await self.redis_client.get(f"jro:{key}")
        if data:
            return JROSchema.model_validate_json(data)
        return None

    async def set_jro(self, key: str, jro: JROSchema, ttl: int = settings.JRO_CACHE_TTL_SECONDS) -> bool:
        """Cache a JRO with a specific TTL."""
        await self.redis_client.set(f"jro:{key}", jro.model_dump_json(), ex=ttl)
        return True

    async def invalidate_jro(self, key: str) -> bool:
        """Remove a cached JRO."""
        await self.redis_client.delete(f"jro:{key}")
        return True

    async def publish_progress(self, job_id: str, event_dict: dict[str, Any]) -> None:
        """Publish a job progress event via Redis Pub/Sub."""
        await self.redis_client.publish(f"job:{job_id}:progress", json.dumps(event_dict))

    async def subscribe_progress(self, job_id: str) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to job progress events via Redis Pub/Sub."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"job:{job_id}:progress")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"job:{job_id}:progress")
            await pubsub.close()


# Singleton
cache_service = CacheService()
