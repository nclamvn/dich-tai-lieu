"""
Unit tests for api/deps.py — shared state singletons and ConnectionManager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from api.deps import (
    queue, manager, chunk_cache, start_time,
    get_processor, set_processor, ConnectionManager,
)
from core.job_queue import JobQueue
from core.cache.chunk_cache import ChunkCache


class TestSingletons:
    """Test module-level singleton instances."""

    def test_queue_is_job_queue(self):
        assert isinstance(queue, JobQueue)

    def test_manager_is_connection_manager(self):
        assert isinstance(manager, ConnectionManager)

    def test_chunk_cache_is_chunk_cache(self):
        assert isinstance(chunk_cache, ChunkCache)

    def test_start_time_is_float(self):
        assert isinstance(start_time, float)
        assert start_time > 0


class TestProcessor:
    """Test processor getter/setter."""

    def teardown_method(self):
        set_processor(None)

    def test_initial_processor_is_none(self):
        set_processor(None)
        assert get_processor() is None

    def test_set_and_get_processor(self):
        mock_proc = MagicMock()
        set_processor(mock_proc)
        assert get_processor() is mock_proc

    def test_overwrite_processor(self):
        p1, p2 = MagicMock(), MagicMock()
        set_processor(p1)
        set_processor(p2)
        assert get_processor() is p2

    def test_reset_processor_to_none(self):
        set_processor(MagicMock())
        set_processor(None)
        assert get_processor() is None


class TestConnectionManager:
    """Test WebSocket ConnectionManager."""

    def test_initial_empty(self):
        cm = ConnectionManager()
        assert cm.active_connections == []

    @pytest.mark.asyncio
    async def test_connect(self):
        cm = ConnectionManager()
        ws = AsyncMock()
        await cm.connect(ws)
        assert ws in cm.active_connections
        ws.accept.assert_awaited_once()

    def test_disconnect(self):
        cm = ConnectionManager()
        ws = MagicMock()
        cm.active_connections.append(ws)
        cm.disconnect(ws)
        assert ws not in cm.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        cm = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        cm.active_connections = [ws1, ws2]
        msg = {"event": "test"}
        await cm.broadcast(msg)
        ws1.send_json.assert_awaited_once_with(msg)
        ws2.send_json.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_connection(self):
        cm = ConnectionManager()
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("disconnected")
        cm.active_connections = [ws_bad, ws_good]
        await cm.broadcast({"event": "test"})
        ws_good.send_json.assert_awaited_once()
