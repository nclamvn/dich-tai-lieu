"""Tests for core_v2.aio_utils.run_blocking."""
import asyncio
import threading
import time

import pytest

from core_v2.aio_utils import run_blocking


@pytest.mark.asyncio
async def test_run_blocking_returns_value():
    assert await run_blocking(lambda: 41 + 1) == 42


@pytest.mark.asyncio
async def test_run_blocking_passes_args():
    assert await run_blocking(lambda a, b, c=0: a + b + c, 1, 2, c=3) == 6


@pytest.mark.asyncio
async def test_run_blocking_propagates_exception():
    def boom():
        raise ValueError("kaboom")

    with pytest.raises(ValueError):
        await run_blocking(boom)


@pytest.mark.asyncio
async def test_run_blocking_runs_off_the_calling_thread():
    main_ident = threading.get_ident()

    def worker():
        return threading.get_ident()

    worker_ident = await run_blocking(worker)
    assert worker_ident != main_ident


@pytest.mark.asyncio
async def test_run_blocking_keeps_loop_responsive():
    from core_v2.aio_utils import run_blocking
    ticks = []

    async def ticker():
        for _ in range(6):
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    def block():
        time.sleep(0.25)   # simulates a sync render/extract
        return "done"

    result, _ = await asyncio.gather(run_blocking(block), ticker())
    assert result == "done"
    assert len(ticks) == 6
    gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
    # If the loop had been blocked by block(), one gap would be ~0.25s.
    assert max(gaps) < 0.15, f"event loop was blocked; gaps={gaps}"
