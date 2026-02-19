"""
Redis client wrapper with in-memory fallback.

When Redis is available, uses it for caching, pub/sub, and distributed state.
When Redis is unavailable, falls back to a simple in-memory dict so the
application never crashes due to missing Redis.

Usage:
    from core.cache.redis_client import get_redis_client

    redis = await get_redis_client()
    await redis.set("key", "value", ex=300)
    value = await redis.get("key")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory fallback (single-process only)
# ---------------------------------------------------------------------------

class InMemoryBackend:
    """Dict-based fallback that mimics a tiny subset of the Redis async API."""

    def __init__(self):
        self._store: dict[str, tuple[Any, Optional[float]]] = {}  # key -> (value, expire_ts)

    async def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires is not None and time.time() > expires:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        expires = (time.time() + ex) if ex else None
        self._store[key] = (value, expires)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def exists(self, key: str) -> bool:
        val = await self.get(key)  # triggers expiry check
        return val is not None

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._store.clear()

    @property
    def is_real_redis(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Redis wrapper
# ---------------------------------------------------------------------------

class RedisClient:
    """
    Async Redis client that auto-falls back to InMemoryBackend.

    Call ``await RedisClient.create(url)`` to construct.
    """

    def __init__(self, backend: Any, *, is_real: bool):
        self._backend = backend
        self._is_real = is_real

    @classmethod
    async def create(cls, url: Optional[str] = None) -> "RedisClient":
        """
        Factory: try connecting to Redis, fall back to in-memory.

        Args:
            url: Redis URL (e.g. ``redis://localhost:6379/0``).
                 If None, skips Redis entirely and uses in-memory.
        """
        if url:
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(url, decode_responses=True)
                await client.ping()
                logger.info("Redis connected: %s", url)
                return cls(client, is_real=True)
            except Exception as exc:
                logger.warning("Redis unavailable (%s), using in-memory fallback", exc)

        return cls(InMemoryBackend(), is_real=False)

    # -- delegate common operations -----------------------------------------

    async def get(self, key: str) -> Optional[str]:
        return await self._backend.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        return await self._backend.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        return await self._backend.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self._backend.exists(key)

    async def ping(self) -> bool:
        return await self._backend.ping()

    async def close(self) -> None:
        await self._backend.close()

    @property
    def is_real_redis(self) -> bool:
        return self._is_real


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_redis_client: Optional[RedisClient] = None


async def get_redis_client(url: Optional[str] = None) -> RedisClient:
    """Get or create the global Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await RedisClient.create(url)
    return _redis_client


async def close_redis_client() -> None:
    """Shut down the global Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
