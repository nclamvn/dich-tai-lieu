"""
Unit tests for api/routes/health.py — health and monitoring endpoints.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


class TestHealthCheck:
    """Test GET /health."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_fields(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.4.0"
        assert "timestamp" in data
        assert isinstance(data["timestamp"], float)


class TestDetailedHealth:
    """Test GET /api/health/detailed."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("api.routes.health.get_health_monitor", create=True)
    def test_detailed_health_success(self, mock_get_monitor, client):
        mock_health = MagicMock()
        mock_health.status = "healthy"
        mock_health.timestamp = time.time()
        mock_health.uptime_seconds = 100.0
        mock_health.components = {"db": "ok"}

        mock_monitor = MagicMock()
        mock_monitor.check_health.return_value = mock_health

        # Patch the import inside the route function
        with patch("core.health_monitor.get_health_monitor", return_value=mock_monitor):
            resp = client.get("/api/health/detailed")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_detailed_health_error_path(self, client):
        with patch("core.health_monitor.get_health_monitor", side_effect=RuntimeError("boom")):
            resp = client.get("/api/health/detailed")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert "boom" in data["error"]


class TestCostMetrics:
    """Test GET /api/monitoring/costs."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_costs_success(self, client):
        mock_metrics = MagicMock()
        mock_metrics.total_tokens_used = 1000
        mock_metrics.total_cost_usd = 0.05
        mock_metrics.cost_by_provider = {"openai": 0.05}
        mock_metrics.cost_by_model = {"gpt-4o": 0.05}
        mock_metrics.average_cost_per_job = 0.05
        mock_metrics.jobs_processed = 1
        mock_metrics.time_period = "24h"

        mock_monitor = MagicMock()
        mock_monitor.get_cost_metrics.return_value = mock_metrics

        with patch("core.health_monitor.get_health_monitor", return_value=mock_monitor):
            resp = client.get("/api/monitoring/costs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tokens_used"] == 1000
        assert data["total_cost_usd"] == 0.05

    def test_costs_error(self, client):
        with patch("core.health_monitor.get_health_monitor", side_effect=RuntimeError("fail")):
            resp = client.get("/api/monitoring/costs")
        assert resp.status_code == 500


class TestErrorStats:
    """Test GET /api/monitoring/errors."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_error_stats_success(self, client):
        mock_stats = {"total": 5, "by_severity": {"high": 2, "low": 3}}
        mock_tracker = MagicMock()
        mock_tracker.get_statistics.return_value = mock_stats

        with patch("core.error_tracker.get_error_tracker", return_value=mock_tracker):
            resp = client.get("/api/monitoring/errors")

        assert resp.status_code == 200
        assert resp.json()["total"] == 5

    def test_error_stats_error(self, client):
        with patch("core.error_tracker.get_error_tracker", side_effect=RuntimeError("db down")):
            resp = client.get("/api/monitoring/errors")
        assert resp.status_code == 500


class TestRecentErrors:
    """Test GET /api/monitoring/errors/recent."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_recent_errors_success(self, client):
        mock_error = MagicMock()
        mock_error.id = "err-1"
        mock_error.error_type = "ValueError"
        mock_error.error_message = "bad value"
        mock_error.severity.value = "high"
        mock_error.category.value = "translation"
        mock_error.last_seen = 1000.0
        mock_error.occurrence_count = 3
        mock_error.resolved = False

        mock_tracker = MagicMock()
        mock_tracker.get_recent_errors.return_value = [mock_error]

        with patch("core.error_tracker.get_error_tracker", return_value=mock_tracker):
            resp = client.get("/api/monitoring/errors/recent?limit=10")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "err-1"
        assert data[0]["severity"] == "high"

    def test_recent_errors_with_severity_filter(self, client):
        mock_tracker = MagicMock()
        mock_tracker.get_recent_errors.return_value = []

        with patch("core.error_tracker.get_error_tracker", return_value=mock_tracker):
            resp = client.get("/api/monitoring/errors/recent?severity=critical")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_recent_errors_error(self, client):
        with patch("core.error_tracker.get_error_tracker", side_effect=RuntimeError("fail")):
            resp = client.get("/api/monitoring/errors/recent")
        assert resp.status_code == 500
