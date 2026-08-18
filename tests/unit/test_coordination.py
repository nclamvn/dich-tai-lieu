"""JobCoordinator tests — Pha 2 (global concurrency) + Pha 3 (cross-worker cancel).

Redis-backed tests use a real redis-server and SKIP truthfully when it is
unreachable (so CI without redis still passes). Each redis test uses unique
lease keys / cancel channels so concurrent/tests never interfere.
"""
import asyncio
import contextlib
import os

import pytest

from api.coordination import JobCoordinator

REDIS_URL = os.environ.get("REDIS_TEST_URL", "redis://localhost:6399")
_counter = {"n": 0}


def _unique(prefix: str) -> str:
    _counter["n"] += 1
    return f"test:{prefix}:{_counter['n']}"


def _redis_ok() -> bool:
    try:
        import redis
        redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


requires_redis = pytest.mark.skipif(not _redis_ok(), reason="redis unavailable")


async def _try_acquire_within(coord, job_id, timeout):
    """True if acquire_slot enters within `timeout`, else False (still blocked)."""
    entered = asyncio.Event()

    async def run():
        async with coord.acquire_slot(job_id):
            entered.set()
            await asyncio.sleep(1.0)

    task = asyncio.create_task(run())
    try:
        await asyncio.wait_for(entered.wait(), timeout)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        task.cancel()
        # CancelledError subclasses BaseException, so suppress(Exception) misses it.
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def _wait_subscribed(coord, channel, timeout=2.0):
    """Wait until the coordinator's cancel subscriber is registered on `channel`
    (start_redis launches the subscribe loop without awaiting the SUBSCRIBE
    round-trip, and pub/sub is non-persistent, so publishing too early is lost)."""
    for _ in range(int(timeout / 0.02)):
        res = await coord._redis.pubsub_numsub(channel)
        if res and int(res[0][1]) >= 1:
            return
        await asyncio.sleep(0.02)


# --------------------------------------------------------------- Pha 2 (local)
@pytest.mark.asyncio
async def test_local_semaphore_limits_concurrency():
    coord = JobCoordinator(local_max_jobs=2)
    active = 0
    peak = 0

    async def job(i):
        nonlocal active, peak
        async with coord.acquire_slot(f"j{i}"):
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(*[job(i) for i in range(6)])
    assert peak <= 2, f"local semaphore exceeded: peak={peak}"


# --------------------------------------------------------------- Pha 2 (redis)
@pytest.mark.asyncio
@requires_redis
async def test_global_semaphore_across_two_coordinators():
    key = _unique("slots")
    a = JobCoordinator(local_max_jobs=99)  # high local cap => redis is the binding limit
    b = JobCoordinator(local_max_jobs=99)
    await a.start_redis(REDIS_URL, global_max=2, lease_key=key, cancel_channel=_unique("c"))
    await b.start_redis(REDIS_URL, global_max=2, lease_key=key, cancel_channel=_unique("c"))
    a._acquire_poll = b._acquire_poll = 0.03  # snappier waits for the test
    try:
        active = 0
        peak = 0
        lock = asyncio.Lock()

        async def job(coord, i):
            nonlocal active, peak
            async with coord.acquire_slot(f"j{i}"):
                async with lock:
                    active += 1
                    peak = max(peak, active)
                await asyncio.sleep(0.15)
                async with lock:
                    active -= 1

        await asyncio.gather(*[job(a if i % 2 == 0 else b, i) for i in range(6)])
        assert peak <= 2, f"global limit exceeded across workers: peak={peak}"
    finally:
        await a.stop_redis()
        await b.stop_redis()


@pytest.mark.asyncio
@requires_redis
async def test_crashed_worker_lease_is_reclaimed():
    key = _unique("slots")
    holder = JobCoordinator(local_max_jobs=99)
    await holder.start_redis(REDIS_URL, global_max=1, lease_key=key, cancel_channel=_unique("c"))
    holder._lease_ttl = 0.3  # simulate a crash: short lease, no heartbeat, never released
    other = JobCoordinator(local_max_jobs=99)
    await other.start_redis(REDIS_URL, global_max=1, lease_key=key, cancel_channel=_unique("c"))
    try:
        await holder._redis_acquire("crashed")               # take the only slot, hold it
        assert await _try_acquire_within(other, "new", 0.15) is False   # full
        await asyncio.sleep(0.35)                            # lease expires
        assert await _try_acquire_within(other, "new", 0.5) is True     # reclaimed
    finally:
        await holder.stop_redis()
        await other.stop_redis()


# --------------------------------------------------------------- Pha 3 (cancel)
@pytest.mark.asyncio
async def test_cancel_fallback_local_without_redis():
    coord = JobCoordinator(local_max_jobs=4)
    cancelled = []
    coord.set_cancel_handler(lambda jid: cancelled.append(jid))
    await coord.request_cancel("job-1")
    assert cancelled == ["job-1"]


@pytest.mark.asyncio
@requires_redis
async def test_cross_worker_cancel_via_pubsub():
    chan = _unique("cancel")
    a = JobCoordinator(local_max_jobs=4)   # owns the job
    b = JobCoordinator(local_max_jobs=4)   # receives the cancel request
    cancelled = []
    a.set_cancel_handler(lambda jid: cancelled.append(jid))
    await a.start_redis(REDIS_URL, global_max=4, lease_key=_unique("s"), cancel_channel=chan)
    await b.start_redis(REDIS_URL, global_max=4, lease_key=_unique("s"), cancel_channel=chan)
    try:
        await _wait_subscribed(a, chan)
        await b.request_cancel("job-xyz")
        for _ in range(40):
            if cancelled:
                break
            await asyncio.sleep(0.05)
        assert cancelled == ["job-xyz"], "cross-worker cancel did not reach the owner"
    finally:
        await a.stop_redis()
        await b.stop_redis()
