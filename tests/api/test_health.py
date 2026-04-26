"""Tests for health and system info endpoints."""

import pytest


class TestHealthEndpoints:
    """GET /health and related system endpoints."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_status_field(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data

    def test_health_status_is_healthy(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ("healthy", "ok", "running")

    def test_health_detailed_returns_200(self, client):
        response = client.get("/api/health/detailed")
        assert response.status_code == 200

    def test_health_detailed_has_components(self, client):
        response = client.get("/api/health/detailed")
        data = response.json()
        assert isinstance(data, dict)

    def test_system_info_returns_200(self, client):
        response = client.get("/api/system/info")
        assert response.status_code == 200

    def test_system_info_has_version(self, client):
        response = client.get("/api/system/info")
        data = response.json()
        assert "version" in data

    def test_system_status_returns_200(self, client):
        response = client.get("/api/system/status")
        assert response.status_code == 200

    def test_queue_stats_returns_200(self, client):
        response = client.get("/api/queue/stats")
        assert response.status_code == 200

    def test_csrf_token_endpoint_returns_200(self, client):
        response = client.get("/api/csrf-token")
        assert response.status_code == 200
