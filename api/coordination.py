"""Cross-worker job coordination — shared job-state, Pha 2 + Pha 3.

Two things break when uvicorn runs with more than one worker; each has a
Redis-backed implementation and a safe LOCAL fallback (no Redis URL, or Redis
unreachable => today's single-worker behaviour, unchanged):

  Pha 2 — GLOBAL concurrency limit. `asyncio.Semaphore` only bounds one process,
          so N workers would allow N x max_jobs simultaneous jobs. The Redis
          impl uses a sorted-set lease (member = job_id, score = expiry time):
          a crashed worker's slot is auto-reclaimed on the next acquire (its
          lease expires), and a heartbeat refreshes the lease while a job runs.

  Pha 3 — cross-worker CANCEL. A cancel request can land on any worker, but the
          asyncio.Task lives on the worker that started the job. The Redis impl
          publishes a cancel event on a channel every worker subscribes to; the
          worker that owns the task cancels it.

start_redis() never raises — on any problem it logs and stays local-only.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Callable, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

# Atomic acquire: prune expired leases, then take a slot iff we already hold one
# or there is room. Runs as a single Redis script so concurrent acquirers can't
# race past the capacity check (ZCARD then ZADD across awaits is NOT atomic).
#   KEYS[1] = lease key
#   ARGV[1] = now   ARGV[2] = expiry(now+ttl)   ARGV[3] = global_max   ARGV[4] = job_id
_ACQUIRE_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
local held = redis.call('ZSCORE', KEYS[1], ARGV[4])
local count = redis.call('ZCARD', KEYS[1])
if held or count < tonumber(ARGV[3]) then
    redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
    return 1
end
return 0
"""


class JobCoordinator:
    """Global concurrency slots + cross-worker cancel, Redis-backed with a
    local fallback. One instance per worker process."""

    def __init__(self, local_max_jobs: int):
        self._local_max = max(1, int(local_max_jobs))
        self._local_sem = asyncio.Semaphore(self._local_max)
        self._redis = None                    # redis.asyncio client, or None
        self._global_max = self._local_max
        self._lease_key = "aps:slots"
        self._cancel_channel = "aps:cancel"
        self._lease_ttl = 60.0                # seconds a slot lease stays valid
        self._heartbeat_interval = 20.0       # refresh comfortably within ttl
        self._acquire_poll = 0.5              # poll interval while at capacity
        self._cancel_task: Optional[asyncio.Task] = None
        self._cancel_handler: Optional[Callable[[str], None]] = None

    # ------------------------------------------------------------------ setup
    def set_cancel_handler(self, fn: Callable[[str], None]) -> None:
        """Register the per-worker function that cancels a locally-owned job
        (e.g. `lambda jid: self._job_tasks[jid].cancel()`). Called for both the
        local fast-path and cross-worker cancel signals."""
        self._cancel_handler = fn

    async def start_redis(
        self,
        url: str,
        global_max: int,
        lease_key: str = "aps:slots",
        cancel_channel: str = "aps:cancel",
    ) -> None:
        """Enable Redis-backed coordination. No-op / local-only when `url` is
        empty or Redis is unreachable. Never raises."""
        self._global_max = max(1, int(global_max))
        if not url:
            logger.info("JobCoordinator: local-only (ws_redis_url empty), max=%d", self._local_max)
            return
        try:
            import redis.asyncio as aioredis

            self._lease_key = lease_key
            self._cancel_channel = cancel_channel
            self._redis = aioredis.from_url(url, socket_connect_timeout=2)
            await self._redis.ping()
            self._cancel_task = asyncio.create_task(self._cancel_subscribe_loop())
            logger.info(
                "JobCoordinator: Redis enabled (global_max=%d, lease=%s, cancel=%s)",
                self._global_max, lease_key, cancel_channel,
            )
        except Exception as e:  # pragma: no cover - exercised via unreachable-redis path
            logger.warning("JobCoordinator: Redis unavailable (%s) - local-only", e)
            self._redis = None

    # -------------------------------------------------- Pha 2: concurrency slot
    @contextlib.asynccontextmanager
    async def acquire_slot(self, job_id: str):
        """Hold one global concurrency slot for the duration of the `async with`.
        Local fallback = `asyncio.Semaphore`. Redis = sorted-set lease + heartbeat."""
        if self._redis is None:
            async with self._local_sem:
                yield
            return

        await self._redis_acquire(job_id)
        hb = asyncio.create_task(self._heartbeat(job_id))
        try:
            yield
        finally:
            hb.cancel()
            with contextlib.suppress(Exception):
                await hb
            with contextlib.suppress(Exception):
                await self._redis.zrem(self._lease_key, job_id)

    async def _redis_acquire(self, job_id: str) -> None:
        """Block until a slot is free, then take a lease. The capacity check +
        lease insert run atomically (Lua) so concurrent acquirers can't both
        pass the check. Re-acquiring a slot already held by this job_id is
        idempotent (refreshes the lease)."""
        while True:
            now = time.time()
            ok = await self._redis.eval(
                _ACQUIRE_LUA, 1, self._lease_key,
                now, now + self._lease_ttl, self._global_max, job_id,
            )
            if ok == 1:
                return
            await asyncio.sleep(self._acquire_poll)

    async def _heartbeat(self, job_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                with contextlib.suppress(Exception):
                    await self._redis.zadd(
                        self._lease_key, {job_id: time.time() + self._lease_ttl}
                    )
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------ Pha 3: cross cancel
    async def request_cancel(self, job_id: str) -> None:
        """Cancel `job_id` wherever it runs: fire the local handler (fast path,
        no-op if this worker doesn't own it) and publish so the owner worker
        cancels it too."""
        self._fire_local_cancel(job_id)
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.publish(self._cancel_channel, json.dumps({"job_id": job_id}))

    def _fire_local_cancel(self, job_id: str) -> None:
        if self._cancel_handler is not None:
            with contextlib.suppress(Exception):
                self._cancel_handler(job_id)

    async def _cancel_subscribe_loop(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._cancel_channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    job_id = json.loads(message["data"]).get("job_id")
                except Exception:
                    continue
                if job_id:
                    self._fire_local_cancel(job_id)
        except asyncio.CancelledError:
            pass
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(self._cancel_channel)
                await pubsub.aclose()

    # ---------------------------------------------------------------- teardown
    async def stop_redis(self) -> None:
        if self._cancel_task is not None:
            self._cancel_task.cancel()
            with contextlib.suppress(Exception):
                await self._cancel_task
            self._cancel_task = None
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.aclose()
            self._redis = None
