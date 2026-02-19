"""
Unit tests for api/routes/system.py — system, cache, processor, engine endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient

from api.main import app
from api import deps


class TestQueueStats:
    """Test GET /api/queue/stats."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_queue_stats_response(self, client):
        resp = client.get("/api/queue/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total", "pending", "queued", "running", "completed", "failed", "cancelled"):
            assert key in data
            assert isinstance(data[key], int)


class TestSystemInfo:
    """Test GET /api/system/info."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_system_info_no_processor(self, client):
        with patch("api.routes.system.get_processor", return_value=None):
            resp = client.get("/api/system/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "2.4.0"
        assert data["processor_running"] is False
        assert data["current_jobs"] == 0
        assert "queue_stats" in data

    def test_system_info_with_processor(self, client):
        mock_proc = MagicMock()
        mock_proc.is_running = True
        mock_proc.current_jobs = ["j1", "j2"]
        with patch("api.routes.system.get_processor", return_value=mock_proc):
            resp = client.get("/api/system/info")
        data = resp.json()
        assert data["processor_running"] is True
        assert data["current_jobs"] == 2

    def test_system_info_uptime(self, client):
        resp = client.get("/api/system/info")
        assert resp.json()["uptime_seconds"] > 0


class TestEngines:
    """Test GET /api/engines."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_engines_success(self, client):
        mock_engines = [{"id": "cloud_api_auto", "name": "Cloud API", "available": True}]
        mock_mgr = MagicMock()
        mock_mgr.get_available_engines.return_value = mock_engines

        with patch("api.routes.system.get_engine_manager", return_value=mock_mgr):
            resp = client.get("/api/engines")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "cloud_api_auto"

    def test_engines_fallback_on_error(self, client):
        with patch("api.routes.system.get_engine_manager", side_effect=RuntimeError("fail")):
            resp = client.get("/api/engines")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "cloud_api_auto"
        assert data[0]["available"] is True


class TestSystemStatus:
    """Test GET /api/system/status."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_system_status_with_pandoc(self, client):
        with patch("shutil.which", return_value="/usr/local/bin/pandoc"), \
             patch("os.path.exists", return_value=False):
            resp = client.get("/api/system/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pandoc_available"] is True
        assert "features" in data
        assert data["features"]["omml_equations"] is True

    def test_system_status_without_pandoc(self, client):
        with patch("shutil.which", return_value=None), \
             patch("os.path.exists", return_value=False):
            resp = client.get("/api/system/status")

        data = resp.json()
        assert data["pandoc_available"] is False
        assert data["features"]["omml_equations"] is False

    def test_system_status_supported_formats(self, client):
        resp = client.get("/api/system/status")
        data = resp.json()
        assert "docx" in data["supported_formats"]
        assert isinstance(data["supported_formats"], list)

    def test_system_status_feature_flags(self, client):
        resp = client.get("/api/system/status")
        data = resp.json()
        assert data["features"]["ast_pipeline"] is True
        assert data["features"]["professional_typography"] is True


class TestCacheStats:
    """Test GET /api/cache/stats."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_cache_stats_success(self, client):
        mock_stats = {"total_entries": 100, "hit_rate": 0.85}
        with patch.object(deps.chunk_cache, "stats", return_value=mock_stats):
            resp = client.get("/api/cache/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["stats"]["total_entries"] == 100

    def test_cache_stats_error(self, client):
        with patch.object(deps.chunk_cache, "stats", side_effect=RuntimeError("db locked")):
            resp = client.get("/api/cache/stats")
        assert resp.status_code == 500


class TestClearCache:
    """Test POST /api/cache/clear."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_clear_cache_success(self, client):
        mock_stats = {"total_entries": 0}
        with patch.object(deps.chunk_cache, "clear") as mock_clear, \
             patch.object(deps.chunk_cache, "stats", return_value=mock_stats):
            resp = client.post("/api/cache/clear")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Cache cleared successfully"
        mock_clear.assert_called_once()

    def test_clear_cache_error(self, client):
        with patch.object(deps.chunk_cache, "clear", side_effect=RuntimeError("fail")):
            resp = client.post("/api/cache/clear")
        assert resp.status_code == 500


class TestProcessorStart:
    """Test POST /api/processor/start."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_start_processor(self, client):
        import asyncio

        async def fake_start(continuous=False):
            pass

        with patch("api.routes.system.get_processor", return_value=None), \
             patch("api.routes.system.set_processor"), \
             patch("api.routes.system.BatchProcessor", create=True) as MockBP, \
             patch("core.batch_processor.BatchProcessor", MockBP), \
             patch("api.routes.system.get_aps_service", create=True):
            mock_bp = MagicMock()
            mock_bp.start = fake_start
            MockBP.return_value = mock_bp
            resp = client.post("/api/processor/start")

        assert resp.status_code == 200
        assert "started" in resp.json()["message"].lower()

    def test_start_processor_already_running(self, client):
        mock_proc = MagicMock()
        mock_proc.is_running = True
        with patch("api.routes.system.get_processor", return_value=mock_proc):
            resp = client.post("/api/processor/start")
        assert resp.status_code == 400
        assert "already running" in resp.json()["detail"]


class TestProcessorStop:
    """Test POST /api/processor/stop."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_stop_processor_success(self, client):
        mock_proc = MagicMock()
        mock_proc.is_running = True
        with patch("api.routes.system.get_processor", return_value=mock_proc):
            resp = client.post("/api/processor/stop")
        assert resp.status_code == 200
        mock_proc.stop.assert_called_once()

    def test_stop_processor_not_running(self, client):
        with patch("api.routes.system.get_processor", return_value=None):
            resp = client.post("/api/processor/stop")
        assert resp.status_code == 400
        assert "not running" in resp.json()["detail"]

    def test_stop_processor_exists_but_stopped(self, client):
        mock_proc = MagicMock()
        mock_proc.is_running = False
        with patch("api.routes.system.get_processor", return_value=mock_proc):
            resp = client.post("/api/processor/stop")
        assert resp.status_code == 400
