"""Tests for Prometheus metrics endpoint (/metrics)."""

import pytest


class TestMetricsEndpoint:
    """GET /metrics — Prometheus exposition format."""

    def test_metrics_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        response = client.get("/metrics")
        ct = response.headers.get("content-type", "")
        assert "text/plain" in ct

    def test_metrics_has_uptime(self, client):
        response = client.get("/metrics")
        assert "app_uptime_seconds" in response.text

    def test_metrics_has_request_count(self, client):
        # Make a request first to populate metrics
        client.get("/health")
        response = client.get("/metrics")
        assert "http_requests_total" in response.text

    def test_metrics_has_duration(self, client):
        client.get("/health")
        response = client.get("/metrics")
        assert "http_request_duration_seconds" in response.text

    def test_metrics_has_type_annotations(self, client):
        response = client.get("/metrics")
        assert "# TYPE" in response.text
        assert "# HELP" in response.text
