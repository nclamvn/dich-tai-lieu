"""
Shared state and dependency getters for API route modules.

Module-level singletons imported by route files.
`processor` uses getter/setter since it's mutable.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Optional

from fastapi import Header, WebSocket

from core.job_queue import JobQueue
from core.cache.chunk_cache import ChunkCache
from config.logging_config import get_logger

logger = get_logger(__name__)

# --- Singletons ---

queue = JobQueue()
start_time = time.time()

# Chunk cache
cache_db_path = Path(__file__).parent.parent / "data" / "cache" / "chunks.db"
chunk_cache = ChunkCache(cache_db_path)


# --- WebSocket Manager ---

class ConnectionManager:
    """Manage WebSocket connections + cross-worker fan-out.

    broadcast() is the single entry point used everywhere. When Redis is
    configured (start_redis succeeded), broadcast PUBLISHES the message and a
    per-worker subscriber loop delivers it to that worker's local clients — so
    a job running on worker A reaches clients connected to worker B, and this
    worker's own clients receive it via the subscription (NOT double-sent).
    When Redis is absent/unreachable, broadcast delivers locally (current
    single-worker behaviour).
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._redis = None            # redis.asyncio client or None (local-only)
        self._pubsub_task = None
        self._channel = "aps:events"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _local_broadcast(self, message: dict):
        """Send to THIS worker's connected clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug("WebSocket send failed (client may have disconnected): %s", e)

    async def broadcast(self, message: dict):
        if self._redis is not None:
            try:
                await self._redis.publish(self._channel, json.dumps(message))
                return
            except Exception as e:
                logger.warning("Redis publish failed, falling back to local broadcast: %s", e)
        await self._local_broadcast(message)

    async def start_redis(self, url: str, channel: str = "aps:events"):
        """Enable cross-worker fan-out. No-op (stays local-only) if url is empty
        or the connection fails — never raises."""
        if not url:
            logger.info("WS fan-out: local-only (ws_redis_url empty)")
            return
        try:
            import redis.asyncio as aioredis
            self._channel = channel
            self._redis = aioredis.from_url(url, socket_connect_timeout=2)
            await self._redis.ping()
            self._pubsub_task = asyncio.create_task(self._subscribe_loop())
            logger.info("WS fan-out: Redis pub/sub enabled (%s, channel=%s)", url, channel)
        except Exception as e:
            logger.warning("WS fan-out: Redis unavailable (%s) - local-only", e)
            self._redis = None

    async def _subscribe_loop(self):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                except Exception:
                    continue
                await self._local_broadcast(data)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await pubsub.unsubscribe(self._channel)
                await pubsub.aclose()
            except Exception:
                pass

    async def stop_redis(self):
        if self._pubsub_task is not None:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except Exception:
                pass
            self._pubsub_task = None
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None


manager = ConnectionManager()


# --- Processor (mutable) ---

_processor = None


def get_processor():
    return _processor


def set_processor(p):
    global _processor
    _processor = p


# --- APS Service ---

from api.aps_service import get_aps_service

_aps_service = get_aps_service(
    job_queue=queue,
    batch_processor=None,  # Will be set when processor starts
    websocket_manager=manager,
)
logger.info("APS Service pre-initialized (awaiting BatchProcessor)")


# --- User ID helper (multi-tenancy) ---

async def get_current_user_id(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
) -> str:
    """
    FastAPI dependency: extract user_id from session token.

    Returns "default_user" when auth is disabled or no token provided.
    """
    if not x_session_token:
        return "default_user"

    try:
        from config.settings import get_settings
        if not get_settings().session_auth_enabled:
            return "default_user"
    except Exception:
        return "default_user"

    try:
        from api.security import security_manager
        session = security_manager.validate_session(x_session_token)
        return session.user_id
    except Exception:
        return "default_user"
