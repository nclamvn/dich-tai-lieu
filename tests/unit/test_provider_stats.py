"""
Unit tests for api/services/provider_stats.py — ProviderStatsTracker.

Target: 90%+ coverage of ProviderMetrics, CallRecord, ProviderStatsTracker.
"""

import json
import pytest
from pathlib import Path

from api.services.provider_stats import (
    ProviderStatsTracker,
    ProviderMetrics,
    CallRecord,
)


# ---------------------------------------------------------------------------
# ProviderMetrics
# ---------------------------------------------------------------------------

class TestProviderMetrics:
    def test_empty_metrics(self):
        m = ProviderMetrics(provider="openai", language_pair="*", document_type="*")
        assert m.total_calls == 0
        assert m.success_rate == 0.0
        assert m.avg_latency_ms == 0.0
        assert m.avg_quality == 0.0
        assert m.cost_per_1k_tokens == 0.0

    def test_single_success(self):
        m = ProviderMetrics(
            provider="openai", language_pair="en→vi", document_type="general",
            success_count=1, total_latency_ms=800.0,
            total_quality_score=0.85, total_cost_usd=0.003,
            total_input_tokens=500, total_output_tokens=800,
        )
        assert m.total_calls == 1
        assert m.success_rate == 1.0
        assert m.avg_latency_ms == 800.0
        assert m.avg_quality == 0.85
        assert m.cost_per_1k_tokens == pytest.approx(0.003 / 1300 * 1000, rel=1e-3)

    def test_mixed_success_failure(self):
        m = ProviderMetrics(
            provider="anthropic", language_pair="*", document_type="*",
            success_count=7, failure_count=3,
        )
        assert m.total_calls == 10
        assert m.success_rate == 0.7

    def test_to_dict(self):
        m = ProviderMetrics(
            provider="deepseek", language_pair="zh→en", document_type="technical",
            success_count=10, failure_count=2, total_latency_ms=10000,
            total_quality_score=7.5, total_cost_usd=0.05,
            total_input_tokens=5000, total_output_tokens=8000,
        )
        d = m.to_dict()
        assert d["provider"] == "deepseek"
        assert d["language_pair"] == "zh→en"
        assert d["document_type"] == "technical"
        assert d["success_count"] == 10
        assert d["failure_count"] == 2
        assert d["success_rate"] == 0.8333
        assert d["avg_latency_ms"] == 1000.0
        assert d["total_calls"] == 12

    def test_zero_tokens_cost(self):
        m = ProviderMetrics(
            provider="openai", language_pair="*", document_type="*",
            success_count=1, total_cost_usd=0.01,
            total_input_tokens=0, total_output_tokens=0,
        )
        assert m.cost_per_1k_tokens == 0.0


# ---------------------------------------------------------------------------
# CallRecord
# ---------------------------------------------------------------------------

class TestCallRecord:
    def test_defaults(self):
        r = CallRecord(
            provider="openai", language_pair="en→vi",
            document_type="general", success=True, latency_ms=500,
        )
        assert r.provider == "openai"
        assert r.quality_score == 0.0
        assert r.timestamp > 0

    def test_custom_timestamp(self):
        r = CallRecord(
            provider="anthropic", language_pair="*",
            document_type="*", success=False, latency_ms=0,
            timestamp=1234567890.0,
        )
        assert r.timestamp == 1234567890.0


# ---------------------------------------------------------------------------
# ProviderStatsTracker — recording
# ---------------------------------------------------------------------------

class TestTrackerRecording:
    def test_record_single(self):
        tracker = ProviderStatsTracker()
        tracker.record(CallRecord(
            provider="openai", language_pair="en→vi", document_type="general",
            success=True, latency_ms=800, quality_score=0.85, cost_usd=0.003,
            input_tokens=500, output_tokens=800,
        ))
        m = tracker.get_metrics("openai", "en→vi", "general")
        assert m is not None
        assert m.success_count == 1
        assert m.avg_quality == 0.85

    def test_record_multiple_same_key(self):
        tracker = ProviderStatsTracker()
        for i in range(5):
            tracker.record(CallRecord(
                provider="openai", language_pair="en→vi", document_type="general",
                success=True, latency_ms=800 + i * 100,
                quality_score=0.8 + i * 0.02,
                cost_usd=0.003, input_tokens=500, output_tokens=800,
            ))
        m = tracker.get_metrics("openai", "en→vi", "general")
        assert m.success_count == 5
        assert m.avg_quality == pytest.approx(0.84, rel=1e-2)
        assert m.avg_latency_ms == pytest.approx(1000, rel=1e-2)

    def test_record_failure(self):
        tracker = ProviderStatsTracker()
        tracker.record(CallRecord(
            provider="anthropic", language_pair="en→ja", document_type="academic",
            success=False, latency_ms=0,
        ))
        m = tracker.get_metrics("anthropic", "en→ja", "academic")
        assert m.failure_count == 1
        assert m.success_count == 0
        assert m.success_rate == 0.0

    def test_record_different_keys(self):
        tracker = ProviderStatsTracker()
        tracker.record(CallRecord(
            provider="openai", language_pair="en→vi", document_type="general",
            success=True, latency_ms=800,
        ))
        tracker.record(CallRecord(
            provider="anthropic", language_pair="ja→en", document_type="academic",
            success=True, latency_ms=1200,
        ))
        assert tracker.get_metrics("openai", "en→vi", "general") is not None
        assert tracker.get_metrics("anthropic", "ja→en", "academic") is not None
        assert tracker.get_metrics("deepseek", "en→vi", "general") is None


# ---------------------------------------------------------------------------
# ProviderStatsTracker — queries
# ---------------------------------------------------------------------------

class TestTrackerQueries:
    def setup_method(self):
        self.tracker = ProviderStatsTracker()
        # Seed data
        for provider, lp, dt in [
            ("openai", "en→vi", "general"),
            ("openai", "en→ja", "academic"),
            ("anthropic", "en→vi", "general"),
            ("deepseek", "zh→en", "general"),
        ]:
            self.tracker.record(CallRecord(
                provider=provider, language_pair=lp, document_type=dt,
                success=True, latency_ms=800, quality_score=0.8,
                cost_usd=0.003, input_tokens=500, output_tokens=800,
            ))

    def test_get_provider_summary(self):
        summary = self.tracker.get_provider_summary("openai")
        assert summary.success_count == 2
        assert summary.provider == "openai"
        assert summary.language_pair == "*"

    def test_get_provider_summary_empty(self):
        summary = self.tracker.get_provider_summary("gemini")
        assert summary.total_calls == 0

    def test_get_all_metrics(self):
        all_m = self.tracker.get_all_metrics()
        assert len(all_m) == 4

    def test_get_providers_for_language(self):
        results = self.tracker.get_providers_for(language_pair="en→vi")
        providers = {m.provider for m in results}
        assert "openai" in providers
        assert "anthropic" in providers
        assert "deepseek" not in providers

    def test_get_providers_for_wildcard(self):
        results = self.tracker.get_providers_for(language_pair="*")
        assert len(results) == 4

    def test_to_dict(self):
        d = self.tracker.to_dict()
        assert d["total_providers"] == 3
        assert d["total_records"] == 4
        assert len(d["metrics"]) == 4

    def test_clear(self):
        self.tracker.clear()
        assert len(self.tracker.get_all_metrics()) == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "stats.json")
        tracker = ProviderStatsTracker(persist_path=path)
        tracker.record(CallRecord(
            provider="openai", language_pair="en→vi", document_type="general",
            success=True, latency_ms=800, quality_score=0.85,
            cost_usd=0.003, input_tokens=500, output_tokens=800,
        ))

        # Load in a new tracker
        tracker2 = ProviderStatsTracker(persist_path=path)
        m = tracker2.get_metrics("openai", "en→vi", "general")
        assert m is not None
        assert m.success_count == 1
        assert m.avg_quality == 0.85

    def test_load_missing_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.json")
        tracker = ProviderStatsTracker(persist_path=path)
        assert len(tracker.get_all_metrics()) == 0

    def test_save_creates_directories(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "stats.json")
        tracker = ProviderStatsTracker(persist_path=path)
        tracker.record(CallRecord(
            provider="openai", language_pair="*", document_type="*",
            success=True, latency_ms=500,
        ))
        assert Path(path).exists()

    def test_corrupted_json_handled(self, tmp_path):
        path = tmp_path / "stats.json"
        path.write_text("not json!!!")
        tracker = ProviderStatsTracker(persist_path=str(path))
        # Should not raise, just log warning
        assert len(tracker.get_all_metrics()) == 0

    def test_clear_persists(self, tmp_path):
        path = str(tmp_path / "stats.json")
        tracker = ProviderStatsTracker(persist_path=path)
        tracker.record(CallRecord(
            provider="openai", language_pair="*", document_type="*",
            success=True, latency_ms=500,
        ))
        tracker.clear()

        tracker2 = ProviderStatsTracker(persist_path=path)
        assert len(tracker2.get_all_metrics()) == 0
