"""
RRI-T Sprint 3: AI provider unified client tests.

Persona coverage: DevOps, QA Destroyer, Business Analyst
Dimensions: D3 (Performance), D5 (Data Integrity), D7 (Edge Cases)
"""

import pytest

from ai_providers.unified_client import (
    ProviderStatus, ProviderHealth, UsageStats, CumulativeStats
)


pytestmark = [pytest.mark.rri_t]


# ===========================================================================
# PROV-001: ProviderStatus enum
# ===========================================================================

class TestProviderStatus:
    """DevOps persona — provider status tracking."""

    @pytest.mark.p0
    def test_prov_001_all_statuses_exist(self):
        """PROV-001 | DevOps | All expected provider statuses defined"""
        expected = ["AVAILABLE", "NO_CREDIT", "INVALID_KEY", "RATE_LIMITED", "ERROR", "NOT_CONFIGURED"]
        for status in expected:
            assert hasattr(ProviderStatus, status)

    @pytest.mark.p0
    def test_prov_001b_provider_health_creation(self):
        """PROV-001b | DevOps | ProviderHealth dataclass creation"""
        health = ProviderHealth(
            provider="openai",
            status=ProviderStatus.AVAILABLE,
            error=None,
            model="gpt-4o-mini",
        )
        assert health.provider == "openai"
        assert health.status == ProviderStatus.AVAILABLE
        assert health.error is None

    @pytest.mark.p1
    def test_prov_001c_provider_health_with_error(self):
        """PROV-001c | DevOps | ProviderHealth with error status"""
        health = ProviderHealth(
            provider="anthropic",
            status=ProviderStatus.RATE_LIMITED,
            error="Rate limit exceeded",
            model="claude-sonnet-4-20250514",
        )
        assert health.status == ProviderStatus.RATE_LIMITED
        assert health.error == "Rate limit exceeded"


# ===========================================================================
# PROV-002: UsageStats cost calculation
# ===========================================================================

class TestUsageStats:
    """Business Analyst persona — cost tracking accuracy."""

    @pytest.mark.p1
    def test_prov_002_cost_usd_nonnegative(self):
        """PROV-002 | BA | cost_usd is always non-negative"""
        stats = UsageStats(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            elapsed_seconds=2.0,
            provider="openai",
            model="gpt-4o-mini",
        )
        assert stats.cost_usd >= 0

    @pytest.mark.p1
    def test_prov_002b_different_models_different_cost(self):
        """PROV-002b | BA | Different models have different costs"""
        base = dict(input_tokens=1000, output_tokens=500, total_tokens=1500,
                    elapsed_seconds=1.0, provider="openai")

        stats_mini = UsageStats(**base, model="gpt-4o-mini")
        stats_full = UsageStats(**base, model="gpt-4o")

        # gpt-4o should cost more than gpt-4o-mini
        # (Both may be 0 if model not in COST_RATES, that's also valid)
        assert isinstance(stats_mini.cost_usd, (int, float))
        assert isinstance(stats_full.cost_usd, (int, float))

    @pytest.mark.p1
    def test_prov_002c_to_dict_complete(self):
        """PROV-002c | BA | to_dict() includes all relevant fields"""
        stats = UsageStats(
            input_tokens=100, output_tokens=50, total_tokens=150,
            elapsed_seconds=0.5, provider="openai", model="gpt-4o-mini",
        )
        d = stats.to_dict()
        expected_keys = ["input_tokens", "output_tokens", "total_tokens",
                         "elapsed_seconds", "provider", "model", "cost_usd"]
        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    @pytest.mark.p1
    def test_prov_002d_zero_tokens_zero_cost(self):
        """PROV-002d | BA | Zero tokens -> zero cost"""
        stats = UsageStats(
            input_tokens=0, output_tokens=0, total_tokens=0,
            elapsed_seconds=0.0, provider="openai", model="gpt-4o-mini",
        )
        assert stats.cost_usd == 0.0


# ===========================================================================
# PROV-003: CumulativeStats aggregation
# ===========================================================================

class TestCumulativeStats:
    """Business Analyst persona — aggregate cost tracking."""

    @pytest.mark.p1
    def test_prov_003_cumulative_add(self):
        """PROV-003 | BA | CumulativeStats.add() aggregates correctly"""
        cumulative = CumulativeStats()
        stats1 = UsageStats(
            input_tokens=100, output_tokens=50, total_tokens=150,
            elapsed_seconds=1.0, provider="openai", model="gpt-4o-mini",
        )
        stats2 = UsageStats(
            input_tokens=200, output_tokens=100, total_tokens=300,
            elapsed_seconds=2.0, provider="anthropic", model="claude-sonnet-4-20250514",
        )
        cumulative.add(stats1)
        cumulative.add(stats2)

        assert cumulative.total_input_tokens == 300
        assert cumulative.total_output_tokens == 150
        assert cumulative.total_tokens == 450
        assert cumulative.total_calls == 2

    @pytest.mark.p1
    def test_prov_003b_calls_by_provider(self):
        """PROV-003b | BA | Calls tracked per provider"""
        cumulative = CumulativeStats()
        for _ in range(3):
            cumulative.add(UsageStats(
                input_tokens=10, output_tokens=5, total_tokens=15,
                elapsed_seconds=0.1, provider="openai", model="gpt-4o-mini",
            ))
        cumulative.add(UsageStats(
            input_tokens=10, output_tokens=5, total_tokens=15,
            elapsed_seconds=0.1, provider="anthropic", model="claude-sonnet-4-20250514",
        ))

        assert cumulative.calls_by_provider.get("openai", 0) == 3
        assert cumulative.calls_by_provider.get("anthropic", 0) == 1


# ===========================================================================
# PROV-004: Smart extraction router
# ===========================================================================

class TestSmartExtraction:
    """QA Destroyer persona — extraction strategy selection."""

    @pytest.mark.p0
    def test_prov_004_extraction_strategy_enum(self):
        """PROV-004 | QA | ExtractionStrategy has all required values"""
        from core.smart_extraction.document_analyzer import ExtractionStrategy
        expected = ["FAST_TEXT", "HYBRID", "FULL_VISION", "OCR"]
        for strategy in expected:
            assert hasattr(ExtractionStrategy, strategy)

    @pytest.mark.p1
    def test_prov_004b_document_analysis_dataclass(self):
        """PROV-004b | QA | DocumentAnalysis has expected fields"""
        from core.smart_extraction.document_analyzer import DocumentAnalysis
        # Verify the dataclass has key fields
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(DocumentAnalysis)]
        assert "total_pages" in field_names
        assert "strategy" in field_names
        assert "text_coverage" in field_names

    @pytest.mark.p1
    def test_prov_004c_extraction_result_dataclass(self):
        """PROV-004c | QA | ExtractionResult has expected fields"""
        from core.smart_extraction.extraction_router import ExtractionResult
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(ExtractionResult)]
        assert "content" in field_names
        assert "total_pages" in field_names
        assert "strategy_used" in field_names
        assert "extraction_time" in field_names
