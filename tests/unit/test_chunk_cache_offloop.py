"""Off-loop + thread-safety test for ChunkCache access via run_blocking.

The orchestrator now does `await run_blocking(chunk_cache.get/set, ...)` so the
per-chunk sqlite I/O runs in worker threads instead of on the event loop. This
verifies:
  (a) concurrent access through run_blocking is CORRECT and raises no sqlite
      thread/lock error — ChunkCache uses thread-local connections + WAL, so
      each worker thread gets its own connection and concurrent writers wait
      (default busy timeout) rather than erroring; and
  (b) a slow cache op does not freeze the event loop.
"""
import asyncio
import time

import pytest

from core.cache.chunk_cache import ChunkCache
from core_v2.aio_utils import run_blocking


@pytest.mark.asyncio
async def test_chunk_cache_concurrent_via_run_blocking(tmp_path):
    cache = ChunkCache(tmp_path / "chunks.db")
    n = 24

    # Concurrent writes dispatched to worker threads.
    await asyncio.gather(*[
        run_blocking(cache.set, f"k{i}", f"v{i}", "en", "vi", mode="essay")
        for i in range(n)
    ])
    # Concurrent reads dispatched to worker threads.
    results = await asyncio.gather(*[
        run_blocking(cache.get, f"k{i}") for i in range(n)
    ])

    assert results == [f"v{i}" for i in range(n)]
    # A miss returns None, not an error.
    assert await run_blocking(cache.get, "does-not-exist") is None


@pytest.mark.asyncio
async def test_cache_op_does_not_block_the_loop(tmp_path):
    cache = ChunkCache(tmp_path / "chunks.db")
    await run_blocking(cache.set, "x", "translated", "en", "vi", mode="essay")

    class _SlowCache:
        def get(self, key):
            time.sleep(0.2)  # simulate a slow/contended sqlite read
            return cache.get(key)

    slow = _SlowCache()
    ticks = []

    async def ticker():
        for _ in range(6):
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    value, _ = await asyncio.gather(run_blocking(slow.get, "x"), ticker())

    assert value == "translated"
    gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
    # An on-loop 0.2s read would show up as one ~0.2s gap.
    assert max(gaps) < 0.15, f"event loop was blocked by the cache op; gaps={gaps}"
