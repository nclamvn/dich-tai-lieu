"""
Unit tests for api/services/provider_router.py — ProviderRouter.

Target: 90%+ coverage of ProviderRouter, RoutingDecision, RoutingMode.
"""

import pytest

from api.services.provider_stats import ProviderStatsTracker, CallRecord
from api.services.provider_router import (
    ProviderRouter,
    RoutingMode,
    RoutingDecision,
    COLD_START_DEFAULTS,
    LANGUAGE_AFFINITIES,
    KNOWN_PROVIDERS,
)


# ---------------------------------------------------------------------------
# RoutingDecision
# ---------------------------------------------------------------------------

class TestRoutingDecision:
    def test_to_dict(self):
        d = RoutingDecision(
            provider="openai",
            mode=RoutingMode.BALANCED,
            score=0.85,
            reason="Best option",
            candidates=[{"provider": "openai", "score": 0.85}],
        )
        result = d.to_dict()
        assert result["provider"] == "openai"
        assert result["mode"] == "balanced"
        assert result["score"] == 0.85
        assert len(result["candidates"]) == 1


# ---------------------------------------------------------------------------
# RoutingMode
# ---------------------------------------------------------------------------

class TestRoutingMode:
    def test_values(self):
        assert RoutingMode.BEST_QUALITY.value == "best_quality"
        assert RoutingMode.CHEAPEST_GOOD_ENOUGH.value == "cheapest_good_enough"
        assert RoutingMode.BALANCED.value == "balanced"

    def test_string_enum(self):
        assert isinstance(RoutingMode.BALANCED, str)


# ---------------------------------------------------------------------------
# Cold start — no historical data
# ---------------------------------------------------------------------------

class TestColdStart:
    def test_cold_start_returns_provider(self):
        router = ProviderRouter()
        decision = router.select()
        assert decision.provider in KNOWN_PROVIDERS
        assert decision.score > 0

    def test_cold_start_all_candidates(self):
        router = ProviderRouter()
        decision = router.select()
        assert len(decision.candidates) == 3

    def test_cold_start_best_quality(self):
        router = ProviderRouter(mode=RoutingMode.BEST_QUALITY)
        decision = router.select()
        # Top providers should be openai or anthropic (both high quality)
        assert decision.provider in ("openai", "anthropic")

    def test_cold_start_cheapest(self):
        router = ProviderRouter(mode=RoutingMode.CHEAPEST_GOOD_ENOUGH)
        decision = router.select()
        # DeepSeek is cheapest
        assert decision.provider == "deepseek"

    def test_cold_start_with_language_affinity(self):
        router = ProviderRouter(mode=RoutingMode.BEST_QUALITY)
        decision = router.select(language_pair="zh→en")
        # DeepSeek has affinity for zh→en
        candidates = {c["provider"]: c["quality"] for c in decision.candidates}
        # DeepSeek gets quality boost for Chinese
        assert candidates["deepseek"] > COLD_START_DEFAULTS["deepseek"]["quality"]

    def test_cold_start_academic_boost(self):
        router = ProviderRouter(mode=RoutingMode.BEST_QUALITY)
        decision = router.select(document_type="academic")
        # Anthropic has "academic" in strengths
        assert decision.provider == "anthropic"


# ---------------------------------------------------------------------------
# Data-driven routing
# ---------------------------------------------------------------------------

class TestDataDrivenRouting:
    def _seed_tracker(self, tracker, provider, lang_pair, quality, cost, n=10):
        for _ in range(n):
            tracker.record(CallRecord(
                provider=provider, language_pair=lang_pair,
                document_type="general", success=True,
                latency_ms=800, quality_score=quality,
                cost_usd=cost, input_tokens=500, output_tokens=800,
            ))

    def test_prefers_higher_quality_provider(self):
        tracker = ProviderStatsTracker()
        self._seed_tracker(tracker, "openai", "en→vi", quality=0.9, cost=0.01)
        self._seed_tracker(tracker, "anthropic", "en→vi", quality=0.7, cost=0.01)

        router = ProviderRouter(stats_tracker=tracker, mode=RoutingMode.BEST_QUALITY)
        decision = router.select(language_pair="en→vi")
        assert decision.provider == "openai"

    def test_prefers_cheaper_when_both_good(self):
        tracker = ProviderStatsTracker()
        # Big cost gap: openai $0.05/call vs deepseek $0.001/call
        self._seed_tracker(tracker, "openai", "en→vi", quality=0.85, cost=0.05)
        self._seed_tracker(tracker, "deepseek", "en→vi", quality=0.80, cost=0.001)

        router = ProviderRouter(
            stats_tracker=tracker,
            mode=RoutingMode.CHEAPEST_GOOD_ENOUGH,
            quality_threshold=0.6,
        )
        decision = router.select(language_pair="en→vi")
        assert decision.provider == "deepseek"

    def test_rejects_below_threshold(self):
        tracker = ProviderStatsTracker()
        self._seed_tracker(tracker, "deepseek", "en→vi", quality=0.3, cost=0.0001)
        self._seed_tracker(tracker, "openai", "en→vi", quality=0.8, cost=0.01)

        router = ProviderRouter(
            stats_tracker=tracker,
            mode=RoutingMode.CHEAPEST_GOOD_ENOUGH,
            quality_threshold=0.6,
        )
        decision = router.select(language_pair="en→vi")
        # DeepSeek is below threshold, openai should be picked
        assert decision.provider == "openai"

    def test_balanced_mode_weights(self):
        tracker = ProviderStatsTracker()
        # Openai: good quality, expensive
        self._seed_tracker(tracker, "openai", "en→vi", quality=0.9, cost=0.02)
        # Deepseek: decent quality, very cheap
        self._seed_tracker(tracker, "deepseek", "en→vi", quality=0.75, cost=0.0005)

        router = ProviderRouter(stats_tracker=tracker, mode=RoutingMode.BALANCED)
        decision = router.select(language_pair="en→vi")
        # Balanced should consider both quality and cost
        assert decision.provider in ["openai", "deepseek"]
        assert len(decision.candidates) >= 2

    def test_blends_with_few_data_points(self):
        tracker = ProviderStatsTracker()
        # Only 2 calls (below 3 threshold)
        self._seed_tracker(tracker, "openai", "en→vi", quality=0.9, cost=0.01, n=2)

        router = ProviderRouter(stats_tracker=tracker, mode=RoutingMode.BEST_QUALITY)
        decision = router.select(language_pair="en→vi")
        # Should still work, blending cold start with partial data
        assert decision.provider in KNOWN_PROVIDERS
        openai_info = next(c for c in decision.candidates if c["provider"] == "openai")
        assert openai_info["data_points"] == 2


# ---------------------------------------------------------------------------
# Provider exclusion
# ---------------------------------------------------------------------------

class TestExclusion:
    def test_exclude_provider(self):
        router = ProviderRouter()
        decision = router.select(exclude_providers=["openai", "anthropic"])
        assert decision.provider == "deepseek"

    def test_exclude_all_fallback(self):
        router = ProviderRouter()
        decision = router.select(exclude_providers=["openai", "anthropic", "deepseek"])
        # Should fallback gracefully
        assert decision.provider == "openai"  # first in available_providers
        assert decision.score == 0.0

    def test_custom_available_providers(self):
        router = ProviderRouter(available_providers=["anthropic", "deepseek"])
        decision = router.select()
        assert decision.provider in ["anthropic", "deepseek"]
        assert len(decision.candidates) == 2


# ---------------------------------------------------------------------------
# Mode override
# ---------------------------------------------------------------------------

class TestModeOverride:
    def test_override_mode_per_call(self):
        router = ProviderRouter(mode=RoutingMode.BALANCED)
        d1 = router.select(mode=RoutingMode.BEST_QUALITY)
        d2 = router.select(mode=RoutingMode.CHEAPEST_GOOD_ENOUGH)
        assert d1.mode == RoutingMode.BEST_QUALITY
        assert d2.mode == RoutingMode.CHEAPEST_GOOD_ENOUGH


# ---------------------------------------------------------------------------
# Normalisation functions
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_normalise_cost_cheap(self):
        score = ProviderRouter._normalise_cost(0.0004)
        assert score > 0.8  # very cheap = high score

    def test_normalise_cost_expensive(self):
        score = ProviderRouter._normalise_cost(0.02)
        assert score < 0.5  # expensive = low score

    def test_normalise_cost_zero(self):
        score = ProviderRouter._normalise_cost(0.0)
        assert score == 1.0

    def test_normalise_latency_fast(self):
        score = ProviderRouter._normalise_latency(500)
        assert score > 0.8

    def test_normalise_latency_slow(self):
        score = ProviderRouter._normalise_latency(3000)
        assert score < 0.3

    def test_normalise_latency_zero(self):
        score = ProviderRouter._normalise_latency(0)
        assert score == 1.0


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestExport:
    def test_to_dict(self):
        router = ProviderRouter(mode=RoutingMode.BALANCED)
        d = router.to_dict()
        assert d["mode"] == "balanced"
        assert d["quality_threshold"] == 0.6
        assert len(d["available_providers"]) == 3
        assert "stats" in d


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_cold_start_defaults_all_providers(self):
        for p in KNOWN_PROVIDERS:
            assert p in COLD_START_DEFAULTS
            assert "quality" in COLD_START_DEFAULTS[p]
            assert "cost_per_1k" in COLD_START_DEFAULTS[p]

    def test_known_providers(self):
        assert KNOWN_PROVIDERS == ["openai", "anthropic", "deepseek"]
