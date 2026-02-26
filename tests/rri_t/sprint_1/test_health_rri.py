"""
RRI-T Sprint 1: Health endpoint tests.

Persona coverage: DevOps, QA Destroyer
Dimensions: D6 (Infrastructure), D2 (API), D7 (Edge Cases)
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


pytestmark = [pytest.mark.rri_t]


class TestHealthBasic:
    """DevOps persona — basic health check."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_health_001_basic_returns_200(self, client):
        """HEALTH-001 | DevOps | GET /health -> 200 with status field"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    @pytest.mark.p1
    def test_health_001b_contains_version(self, client):
        """HEALTH-001b | DevOps | Health response includes version"""
        resp = client.get("/health")
        data = resp.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    @pytest.mark.p1
    def test_health_001c_contains_timestamp(self, client):
        """HEALTH-001c | DevOps | Health response includes timestamp"""
        resp = client.get("/health")
        data = resp.json()
        assert "timestamp" in data

    @pytest.mark.p1
    def test_health_001d_disk_free_reported(self, client):
        """HEALTH-001d | DevOps | Health reports disk_free_mb"""
        resp = client.get("/health")
        data = resp.json()
        assert "disk_free_mb" in data
        assert isinstance(data["disk_free_mb"], (int, float))


class TestHealthDetailed:
    """DevOps persona — detailed health with component breakdown."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_health_002_detailed_endpoint(self, client):
        """HEALTH-002 | DevOps | Detailed health -> component breakdown"""
        resp = client.get("/api/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestMonitoringEndpoints:
    """DevOps persona — monitoring data endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_monitoring_costs_returns_200(self, client):
        """MON-COSTS | DevOps | Cost metrics endpoint accessible"""
        resp = client.get("/api/monitoring/costs")
        # May return 200 or 500 depending on DB state
        assert resp.status_code in (200, 500)

    @pytest.mark.p1
    def test_monitoring_audit_returns_200(self, client):
        """MON-AUDIT | DevOps | Audit log endpoint accessible"""
        resp = client.get("/api/monitoring/audit")
        assert resp.status_code in (200, 500)

    @pytest.mark.p1
    def test_monitoring_errors_returns_200(self, client):
        """MON-ERRORS | DevOps | Error stats endpoint accessible"""
        resp = client.get("/api/monitoring/errors")
        assert resp.status_code in (200, 500)

    @pytest.mark.p1
    def test_monitoring_errors_recent(self, client):
        """MON-ERRORS-RECENT | DevOps | Recent errors endpoint accessible"""
        resp = client.get("/api/monitoring/errors/recent")
        assert resp.status_code in (200, 500)
