"""Tests for Redis client wrapper with in-memory fallback."""

import pytest
import asyncio

from core.cache.redis_client import RedisClient, InMemoryBackend, get_redis_client, close_redis_client


@pytest.fixture
def mem_backend():
    return InMemoryBackend()


class TestInMemoryBackend:
    """Test the in-memory fallback."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, mem_backend):
        await mem_backend.set("key1", "value1")
        result = await mem_backend.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self, mem_backend):
        result = await mem_backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, mem_backend):
        await mem_backend.set("key1", "value1")
        deleted = await mem_backend.delete("key1")
        assert deleted == 1
        assert await mem_backend.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, mem_backend):
        deleted = await mem_backend.delete("nope")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_exists(self, mem_backend):
        await mem_backend.set("key1", "value1")
        assert await mem_backend.exists("key1") is True
        assert await mem_backend.exists("key2") is False

    @pytest.mark.asyncio
    async def test_expiry(self, mem_backend):
        # Manually set with a past expiry timestamp
        mem_backend._store["key1"] = ("value1", 0)  # epoch 0 = long past
        result = await mem_backend.get("key1")
        assert result is None
        # Key should be cleaned up
        assert "key1" not in mem_backend._store

    @pytest.mark.asyncio
    async def test_ping(self, mem_backend):
        assert await mem_backend.ping() is True

    @pytest.mark.asyncio
    async def test_close(self, mem_backend):
        await mem_backend.set("key1", "val")
        await mem_backend.close()
        assert await mem_backend.get("key1") is None

    def test_is_not_real_redis(self, mem_backend):
        assert mem_backend.is_real_redis is False


class TestRedisClient:
    """Test the RedisClient wrapper."""

    @pytest.mark.asyncio
    async def test_create_without_url_uses_memory(self):
        client = await RedisClient.create(url=None)
        assert client.is_real_redis is False
        await client.set("test", "value")
        assert await client.get("test") == "value"
        await client.close()

    @pytest.mark.asyncio
    async def test_create_with_bad_url_falls_back(self):
        client = await RedisClient.create(url="redis://localhost:59999")
        assert client.is_real_redis is False
        await client.close()

    @pytest.mark.asyncio
    async def test_singleton_lifecycle(self):
        # Clean slate
        await close_redis_client()

        client = await get_redis_client()
        assert client.is_real_redis is False

        # Same instance returned
        client2 = await get_redis_client()
        assert client is client2

        await close_redis_client()
