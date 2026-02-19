"""
Unit tests for api/services/cost_dashboard.py + api/routes/dashboard.py.

Target: 90%+ coverage.
"""

import pytest

from api.services.provider_stats import ProviderStatsTracker, CallRecord
from api.services.cost_dashboard import (
    CostDashboard,
    CostOverview,
    ProviderCostSummary,
    CostEstimate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    """Fresh in-memory tracker."""
    return ProviderStatsTracker()


@pytest.fixture
def tracker_with_data(tracker):
    """Tracker with sample call records."""
    # OpenAI calls
    tracker.record(CallRecord(
        provider="openai", language_pair="en→vi", document_type="general",
        success=True, latency_ms=1000, quality_score=0.85,
        cost_usd=0.003, input_tokens=500, output_tokens=800,
    ))
    tracker.record(CallRecord(
        provider="openai", language_pair="en→vi", document_type="general",
        success=True, latency_ms=1200, quality_score=0.90,
        cost_usd=0.004, input_tokens=600, output_tokens=900,
    ))
    # Anthropic calls
    tracker.record(CallRecord(
        provider="anthropic", language_pair="en→vi", document_type="academic",
        success=True, latency_ms=1500, quality_score=0.95,
        cost_usd=0.005, input_tokens=700, output_tokens=1000,
    ))
    # Failed call
    tracker.record(CallRecord(
        provider="openai", language_pair="en→ja", document_type="general",
        success=False, latency_ms=500, quality_score=0.0,
    ))
    return tracker


@pytest.fixture
def dashboard(tracker_with_data):
    return CostDashboard(tracker_with_data)


@pytest.fixture
def empty_dashboard(tracker):
    return CostDashboard(tracker)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class TestDataClasses:
    def test_cost_overview_to_dict(self):
        o = CostOverview(
            total_cost_usd=0.012, total_calls=3, total_tokens=3500,
            avg_cost_per_call=0.004, avg_cost_per_1k_tokens=0.003429,
            provider_count=2, language_pairs=["en→vi"],
        )
        d = o.to_dict()
        assert d["total_cost_usd"] == 0.012
        assert d["total_calls"] == 3
        assert isinstance(d["language_pairs"], list)

    def test_provider_summary_to_dict(self):
        s = ProviderCostSummary(
            provider="openai", total_cost_usd=0.007, total_calls=3,
            success_rate=0.667, avg_latency_ms=1100, avg_quality=0.875,
            cost_per_1k_tokens=0.0025, total_input_tokens=1100,
            total_output_tokens=1700,
        )
        d = s.to_dict()
        assert d["provider"] == "openai"
        assert d["total_calls"] == 3

    def test_cost_estimate_to_dict(self):
        e = CostEstimate(
            estimated_tokens=5000, estimated_cost_usd=0.015,
            provider="openai", cost_per_1k_tokens=0.003,
            confidence="high",
        )
        d = e.to_dict()
        assert d["estimated_tokens"] == 5000
        assert d["confidence"] == "high"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class TestOverview:
    def test_overview_with_data(self, dashboard):
        overview = dashboard.get_overview()
        assert overview.total_cost_usd > 0
        assert overview.total_calls >= 3
        assert overview.total_tokens > 0
        assert overview.provider_count == 2
        assert len(overview.language_pairs) >= 1

    def test_overview_empty(self, empty_dashboard):
        overview = empty_dashboard.get_overview()
        assert overview.total_cost_usd == 0.0
        assert overview.total_calls == 0
        assert overview.provider_count == 0

    def test_avg_cost_per_call(self, dashboard):
        overview = dashboard.get_overview()
        assert overview.avg_cost_per_call > 0

    def test_avg_cost_per_1k_tokens(self, dashboard):
        overview = dashboard.get_overview()
        assert overview.avg_cost_per_1k_tokens > 0


# ---------------------------------------------------------------------------
# Provider breakdown
# ---------------------------------------------------------------------------

class TestProviderBreakdown:
    def test_breakdown_providers(self, dashboard):
        breakdown = dashboard.get_provider_breakdown()
        providers = {s.provider for s in breakdown}
        assert "openai" in providers
        assert "anthropic" in providers

    def test_breakdown_empty(self, empty_dashboard):
        assert empty_dashboard.get_provider_breakdown() == []

    def test_openai_summary(self, dashboard):
        breakdown = dashboard.get_provider_breakdown()
        openai = next(s for s in breakdown if s.provider == "openai")
        assert openai.total_calls >= 2  # 2 success + 1 failure
        assert openai.total_cost_usd > 0
        assert 0 < openai.success_rate < 1  # has failures

    def test_anthropic_summary(self, dashboard):
        breakdown = dashboard.get_provider_breakdown()
        anthropic = next(s for s in breakdown if s.provider == "anthropic")
        assert anthropic.success_rate == 1.0
        assert anthropic.avg_quality > 0


# ---------------------------------------------------------------------------
# Language pair costs
# ---------------------------------------------------------------------------

class TestLanguagePairCosts:
    def test_costs_by_pair(self, dashboard):
        costs = dashboard.get_language_pair_costs()
        assert "en→vi" in costs
        assert costs["en→vi"] > 0

    def test_empty(self, empty_dashboard):
        assert empty_dashboard.get_language_pair_costs() == {}


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

class TestCostEstimation:
    def test_estimate_with_data(self, dashboard):
        est = dashboard.estimate_cost(pages=10, language_pair="en→vi")
        assert est.estimated_tokens == 5000
        assert est.estimated_cost_usd > 0
        assert est.confidence in ("high", "medium")

    def test_estimate_fallback(self, empty_dashboard):
        est = empty_dashboard.estimate_cost(pages=10)
        assert est.estimated_tokens == 5000
        assert est.estimated_cost_usd > 0
        assert est.confidence == "low"
        assert est.provider == "unknown"

    def test_estimate_with_provider(self, dashboard):
        est = dashboard.estimate_cost(pages=5, provider="openai")
        assert est.provider == "openai"

    def test_estimate_custom_pages(self, dashboard):
        est1 = dashboard.estimate_cost(pages=1)
        est10 = dashboard.estimate_cost(pages=10)
        assert est10.estimated_tokens > est1.estimated_tokens


# ---------------------------------------------------------------------------
# Cheapest / Best value
# ---------------------------------------------------------------------------

class TestProviderSelection:
    def test_cheapest_provider(self, dashboard):
        cheapest = dashboard.get_cheapest_provider()
        assert cheapest is not None
        assert cheapest.provider in ("openai", "anthropic")

    def test_cheapest_empty(self, empty_dashboard):
        assert empty_dashboard.get_cheapest_provider() is None

    def test_best_value_provider(self, dashboard):
        best = dashboard.get_best_value_provider()
        assert best is not None

    def test_best_value_empty(self, empty_dashboard):
        assert empty_dashboard.get_best_value_provider() is None

    def test_cheapest_with_language_filter(self, dashboard):
        cheapest = dashboard.get_cheapest_provider(language_pair="en→vi")
        assert cheapest is not None


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

class TestDashboardRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_overview_endpoint(self, client):
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data
        assert "total_calls" in data

    def test_providers_endpoint(self, client):
        resp = client.get("/api/dashboard/providers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_language_pairs_endpoint(self, client):
        resp = client.get("/api/dashboard/language-pairs")
        assert resp.status_code == 200

    def test_estimate_endpoint(self, client):
        resp = client.get("/api/dashboard/estimate?pages=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "estimated_tokens" in data
        assert "estimated_cost_usd" in data

    def test_cheapest_endpoint(self, client):
        resp = client.get("/api/dashboard/cheapest")
        assert resp.status_code == 200

    def test_best_value_endpoint(self, client):
        resp = client.get("/api/dashboard/best-value")
        assert resp.status_code == 200
