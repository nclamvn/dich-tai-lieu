"""
Shared state and dependency getters for API route modules.

Module-level singletons imported by route files.
`processor` uses getter/setter since it's mutable.
"""

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
    """
    Manage WebSocket connections for real-time updates.

    Handles client connections and broadcasts job progress, status
    changes, and queue statistics to all connected clients.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug("WebSocket send failed (client may have disconnected): %s", e)


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
