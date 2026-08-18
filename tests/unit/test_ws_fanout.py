"""
Unit tests for cross-worker WebSocket fan-out via Redis pub/sub (#6 Pha 1).

Covers:
- Local-only broadcast when Redis is not configured (single-worker behaviour).
- disconnect() is safe on a websocket that was never connected.
- broadcast() falls back to local delivery when a Redis publish raises.
- Cross-worker fan-out: a message published by manager A reaches a client
  connected to manager B (requires a reachable redis-server).
- No double delivery: the publishing manager delivers a message exactly once
  (via the subscription, not also locally).

The Redis-backed tests SKIP (truthfully) when redis-server is unreachable, so
CI without redis still passes. Uses asyncio_mode=auto (see pytest.ini), so the
async tests need no explicit marker.
"""

import os
import asyncio

import pytest

from api.deps import ConnectionManager


# Test redis endpoint (a redis-server runs on 6399 in the dev/CI harness here).
REDIS_URL = os.environ.get("REDIS_TEST_URL", "redis://localhost:6399")

# Module-level counter -> a UNIQUE pub/sub channel per test (no time/random, per
# spec), so concurrent/repeated runs never cross-talk on a shared channel.
_channel_counter = 0


def _unique_channel() -> str:
    global _channel_counter
    _channel_counter += 1
    return f"aps:test:fanout:{_channel_counter}"


def _redis_available(url: str) -> bool:
    """Truthful reachability probe via a synchronous ping."""
    try:
        import redis  # redis-py (sync client)

        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        try:
            client.ping()
        finally:
            client.close()
        return True
    except Exception:
        return False


@pytest.fixture
def redis_url():
    """Provide the test Redis URL, skipping the test if it is unreachable."""
    if not _redis_available(REDIS_URL):
        pytest.skip("redis unavailable")
    return REDIS_URL


async def _wait_for_subscriber(client, channel: str, tries: int = 40) -> bool:
    """Poll PUBSUB NUMSUB until >=1 subscriber is registered for ``channel``.

    Redis pub/sub has no persistence: a message published before the subscriber
    loop finishes SUBSCRIBE is dropped forever. start_redis() launches that loop
    via create_task without awaiting the subscribe round-trip, so we confirm the
    subscription is live on the server before publishing — deterministic, no
    arbitrary sleeps.
    """
    for _ in range(tries):
        try:
            res = await client.pubsub_numsub(channel)
        except Exception:
            res = None
        if res and int(res[0][1]) >= 1:
            return True
        await asyncio.sleep(0.05)
    return False


class _FakeWS:
    def __init__(self):
        self.sent = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, msg):
        self.sent.append(msg)


# --------------------------------------------------------------------------- #
# Local-only (no Redis) — current single-worker behaviour                      #
# --------------------------------------------------------------------------- #

async def test_local_broadcast_without_redis():
    mgr = ConnectionManager()
    ws = _FakeWS()
    await mgr.connect(ws)
    await mgr.broadcast({"a": 1})
    assert ws.sent == [{"a": 1}]


async def test_disconnect_is_safe():
    mgr = ConnectionManager()
    ws = _FakeWS()

    # Never connected -> disconnect must not raise.
    mgr.disconnect(ws)

    # Connect then disconnect removes it.
    await mgr.connect(ws)
    assert ws in mgr.active_connections
    mgr.disconnect(ws)
    assert ws not in mgr.active_connections


async def test_publish_failure_falls_back_to_local():
    mgr = ConnectionManager()

    class _BadRedis:
        async def publish(self, channel, data):
            raise RuntimeError("boom")

    # Simulate "Redis configured" but publish blows up -> broadcast must fall
    # back to local delivery so the client still receives the message.
    mgr._redis = _BadRedis()
    ws = _FakeWS()
    await mgr.connect(ws)
    await mgr.broadcast({"x": 1})
    assert ws.sent == [{"x": 1}]


# --------------------------------------------------------------------------- #
# Redis-backed (skip if unreachable)                                          #
# --------------------------------------------------------------------------- #

async def test_cross_worker_fanout_via_redis(redis_url):
    channel = _unique_channel()
    a = ConnectionManager()
    b = ConnectionManager()
    await a.start_redis(redis_url, channel)
    await b.start_redis(redis_url, channel)

    # start_redis never raises; confirm both sides actually enabled Redis (else
    # this would silently degrade to a local-only test and prove nothing).
    assert a._redis is not None, "manager A did not enable Redis"
    assert b._redis is not None, "manager B did not enable Redis"

    b_ws = _FakeWS()
    await b.connect(b_ws)
    try:
        # Ensure B's subscription is live before A publishes (pub/sub is lossy).
        assert await _wait_for_subscriber(a._redis, channel), "subscriber not ready"

        await a.broadcast({"event": "progress", "p": 42})

        for _ in range(40):  # poll up to ~2s
            if b_ws.sent:
                break
            await asyncio.sleep(0.05)

        assert b_ws.sent == [{"event": "progress", "p": 42}]
    finally:
        await a.stop_redis()
        await b.stop_redis()


async def test_no_double_delivery_via_redis(redis_url):
    channel = _unique_channel()
    a = ConnectionManager()
    await a.start_redis(redis_url, channel)
    assert a._redis is not None, "manager A did not enable Redis"

    a_ws = _FakeWS()
    await a.connect(a_ws)
    try:
        # A's own subscription must be live before A publishes.
        assert await _wait_for_subscriber(a._redis, channel), "subscriber not ready"

        await a.broadcast({"n": 1})

        for _ in range(40):  # poll until received
            if a_ws.sent:
                break
            await asyncio.sleep(0.05)

        # Give any (erroneous) second delivery a chance to land before asserting.
        await asyncio.sleep(0.2)

        # Exactly once: the publisher delivers via the subscription only, NOT
        # also locally in broadcast().
        assert a_ws.sent == [{"n": 1}]
    finally:
        await a.stop_redis()
