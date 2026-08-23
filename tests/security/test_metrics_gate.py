"""Behavioral tests for the /metrics gate (_metrics_guard).

Contract:
- METRICS_TOKEN set   → 401 without/with wrong bearer, 200 with the right one
  (any security mode — a configured token is always enforced).
- METRICS_TOKEN empty → 200 in development, 403 in production (fail-closed:
  the path/latency/error tables are a recon map of the API surface).

The guard reads ``get_settings()`` at request time, so tests toggle attributes
on the live settings singleton via monkeypatch (restored automatically).
"""

import pytest

from config.settings import settings


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # Baseline: dev mode, no token — each test overrides what it needs.
    monkeypatch.setattr(settings, "metrics_token", "")
    monkeypatch.setattr(settings, "security_mode", "development")
    yield


def test_dev_without_token_is_open(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


def test_production_without_token_is_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "security_mode", "production")
    resp = client.get("/metrics")
    assert resp.status_code == 403


def test_token_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "scrape-secret-123")
    assert client.get("/metrics").status_code == 401
    assert client.get(
        "/metrics", headers={"Authorization": "Bearer wrong"}
    ).status_code == 401
    ok = client.get(
        "/metrics", headers={"Authorization": "Bearer scrape-secret-123"}
    )
    assert ok.status_code == 200
    assert "app_uptime_seconds" in ok.text


def test_token_enforced_even_in_development(client, monkeypatch):
    # A configured token is never ignored, whatever the mode.
    monkeypatch.setattr(settings, "metrics_token", "tok")
    monkeypatch.setattr(settings, "security_mode", "development")
    assert client.get("/metrics").status_code == 401
