"""
RRI-T Sprint 5: System & Dashboard API route tests.

Persona coverage: DevOps, Business Analyst
Dimensions: D2 (API), D6 (Infrastructure), D5 (Data Integrity)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
import api.deps as deps


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# SYS-001: Queue stats
# ===========================================================================

class TestQueueStats:
    """DevOps persona — queue monitoring."""

    @pytest.mark.p0
    def test_sys_001_queue_stats(self, client):
        """SYS-001 | DevOps | /api/queue/stats -> 200 with counts"""
        with patch.object(deps.queue, "get_queue_stats", return_value={
            "total": 10,
        }):
            resp = client.get("/api/queue/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    @pytest.mark.p1
    def test_sys_001b_system_info(self, client):
        """SYS-001b | DevOps | /api/system/info -> version + uptime"""
        with patch.object(deps.queue, "get_queue_stats", return_value={"total": 0}):
            with patch("api.routes.system.get_processor", return_value=None):
                resp = client.get("/api/system/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


# ===========================================================================
# SYS-002: System status & engines
# ===========================================================================

class TestSystemStatus:
    """DevOps persona — system capabilities."""

    @pytest.mark.p1
    def test_sys_002_system_status(self, client):
        """SYS-002 | DevOps | /api/system/status -> feature flags"""
        resp = client.get("/api/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "supported_formats" in data
        assert "docx" in data["supported_formats"]

    @pytest.mark.p1
    def test_sys_002b_engines_endpoint(self, client):
        """SYS-002b | DevOps | /api/engines -> list of engines"""
        resp = client.get("/api/engines")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


# ===========================================================================
# SYS-003: Cache management
# ===========================================================================

class TestCacheRoutes:
    """DevOps persona — cache operations."""

    @pytest.mark.p1
    def test_sys_003_cache_stats(self, client):
        """SYS-003 | DevOps | /api/cache/stats -> 200"""
        with patch.object(deps.chunk_cache, "stats", return_value={
            "total_entries": 0, "hits": 0, "misses": 0,
            "hit_rate": 0.0, "db_size_mb": 0.01,
        }):
            resp = client.get("/api/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "stats" in data

    @pytest.mark.p1
    def test_sys_003b_cache_clear(self, client):
        """SYS-003b | DevOps | /api/cache/clear -> 200"""
        with patch.object(deps.chunk_cache, "clear"):
            with patch.object(deps.chunk_cache, "stats", return_value={
                "total_entries": 0, "hits": 0, "misses": 0,
                "hit_rate": 0.0, "db_size_mb": 0.0,
            }):
                resp = client.post("/api/cache/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Cache cleared successfully"


# ===========================================================================
# SYS-004: Processor lifecycle
# ===========================================================================

class TestProcessorRoutes:
    """DevOps persona — processor control."""

    @pytest.mark.p1
    def test_sys_004_stop_not_running(self, client):
        """SYS-004 | DevOps | Stop when not running -> 400"""
        with patch("api.routes.system.get_processor", return_value=None):
            resp = client.post("/api/processor/stop")
        assert resp.status_code == 400

    @pytest.mark.p1
    def test_sys_004b_start_already_running(self, client):
        """SYS-004b | DevOps | Start when already running -> 400"""
        mock_proc = MagicMock()
        mock_proc.is_running = True
        with patch("api.routes.system.get_processor", return_value=mock_proc):
            resp = client.post("/api/processor/start")
        assert resp.status_code == 400


# ===========================================================================
# DASH-001: Dashboard overview
# ===========================================================================

class TestDashboardRoutes:
    """Business Analyst persona — cost analytics."""

    @pytest.mark.p1
    def test_dash_001_overview(self, client):
        """DASH-001 | BA | /api/dashboard/overview -> cost summary"""
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data
        assert "total_calls" in data
        assert "total_tokens" in data

    @pytest.mark.p1
    def test_dash_001b_providers(self, client):
        """DASH-001b | BA | /api/dashboard/providers -> list"""
        resp = client.get("/api/dashboard/providers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.p1
    def test_dash_001c_language_pairs(self, client):
        """DASH-001c | BA | /api/dashboard/language-pairs -> dict"""
        resp = client.get("/api/dashboard/language-pairs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    @pytest.mark.p1
    def test_dash_001d_estimate(self, client):
        """DASH-001d | BA | /api/dashboard/estimate -> cost estimate"""
        resp = client.get("/api/dashboard/estimate?pages=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "estimated_tokens" in data
        assert "estimated_cost_usd" in data
        assert "confidence" in data

    @pytest.mark.p1
    def test_dash_001e_cheapest(self, client):
        """DASH-001e | BA | /api/dashboard/cheapest -> provider or null"""
        resp = client.get("/api/dashboard/cheapest")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_dash_001f_best_value(self, client):
        """DASH-001f | BA | /api/dashboard/best-value -> provider or null"""
        resp = client.get("/api/dashboard/best-value")
        assert resp.status_code == 200


# ===========================================================================
# DASH-002: Cost dashboard data models
# ===========================================================================

class TestDashboardModels:
    """Business Analyst persona — data model validation."""

    @pytest.mark.p0
    def test_dash_002_cost_overview_to_dict(self):
        """DASH-002 | BA | CostOverview.to_dict() has all fields"""
        from api.services.cost_dashboard import CostOverview
        overview = CostOverview(
            total_cost_usd=1.5,
            total_calls=100,
            total_tokens=50000,
            avg_cost_per_call=0.015,
            avg_cost_per_1k_tokens=0.03,
            provider_count=2,
            language_pairs=["en→vi", "en→fr"],
        )
        d = overview.to_dict()
        expected_keys = [
            "total_cost_usd", "total_calls", "total_tokens",
            "avg_cost_per_call", "avg_cost_per_1k_tokens",
            "provider_count", "language_pairs",
        ]
        for key in expected_keys:
            assert key in d

    @pytest.mark.p0
    def test_dash_002b_provider_summary_to_dict(self):
        """DASH-002b | BA | ProviderCostSummary.to_dict() has all fields"""
        from api.services.cost_dashboard import ProviderCostSummary
        summary = ProviderCostSummary(
            provider="openai",
            total_cost_usd=0.5,
            total_calls=50,
            success_rate=0.98,
            avg_latency_ms=200.0,
            avg_quality=0.85,
            cost_per_1k_tokens=0.01,
            total_input_tokens=20000,
            total_output_tokens=10000,
        )
        d = summary.to_dict()
        assert d["provider"] == "openai"
        assert "total_cost_usd" in d
        assert "success_rate" in d

    @pytest.mark.p1
    def test_dash_002c_cost_estimate_to_dict(self):
        """DASH-002c | BA | CostEstimate.to_dict() has all fields"""
        from api.services.cost_dashboard import CostEstimate
        estimate = CostEstimate(
            estimated_tokens=5000,
            estimated_cost_usd=0.015,
            provider="openai",
            cost_per_1k_tokens=0.003,
            confidence="high",
        )
        d = estimate.to_dict()
        assert d["estimated_tokens"] == 5000
        assert d["confidence"] == "high"
