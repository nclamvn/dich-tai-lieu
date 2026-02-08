"""
Cost Dashboard — Aggregate and analyze provider cost data.

Wraps ProviderStatsTracker to provide dashboard-ready analytics:
- Per-provider cost summaries
- Language pair cost comparison
- Time-based cost estimates
- Budget tracking

Standalone module — only imports from api/services/provider_stats.py.

Usage::

    from api.services.provider_stats import ProviderStatsTracker
    from api.services.cost_dashboard import CostDashboard

    tracker = ProviderStatsTracker()
    dashboard = CostDashboard(tracker)

    # Get overview
    overview = dashboard.get_overview()

    # Per-provider breakdown
    breakdown = dashboard.get_provider_breakdown()

    # Cost estimate
    estimate = dashboard.estimate_cost(pages=100, language_pair="en→vi")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import logging

from api.services.provider_stats import ProviderStatsTracker, ProviderMetrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CostOverview:
    """Dashboard overview summary."""

    total_cost_usd: float
    total_calls: int
    total_tokens: int
    avg_cost_per_call: float
    avg_cost_per_1k_tokens: float
    provider_count: int
    language_pairs: List[str]

    def to_dict(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "avg_cost_per_call": round(self.avg_cost_per_call, 6),
            "avg_cost_per_1k_tokens": round(self.avg_cost_per_1k_tokens, 6),
            "provider_count": self.provider_count,
            "language_pairs": self.language_pairs,
        }


@dataclass
class ProviderCostSummary:
    """Cost summary for one provider."""

    provider: str
    total_cost_usd: float
    total_calls: int
    success_rate: float
    avg_latency_ms: float
    avg_quality: float
    cost_per_1k_tokens: float
    total_input_tokens: int
    total_output_tokens: int

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_calls": self.total_calls,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_quality": round(self.avg_quality, 4),
            "cost_per_1k_tokens": round(self.cost_per_1k_tokens, 6),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }


@dataclass
class CostEstimate:
    """Estimated cost for a translation job."""

    estimated_tokens: int
    estimated_cost_usd: float
    provider: str
    cost_per_1k_tokens: float
    confidence: str  # "high", "medium", "low"

    def to_dict(self) -> dict:
        return {
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "provider": self.provider,
            "cost_per_1k_tokens": round(self.cost_per_1k_tokens, 6),
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# CostDashboard
# ---------------------------------------------------------------------------

class CostDashboard:
    """Cost analytics dashboard over ProviderStatsTracker data."""

    # Average tokens per page (rough estimate)
    TOKENS_PER_PAGE = 500

    def __init__(self, tracker: ProviderStatsTracker) -> None:
        self._tracker = tracker

    def get_overview(self) -> CostOverview:
        """Get high-level cost overview."""
        all_metrics = self._tracker.get_all_metrics()

        if not all_metrics:
            return CostOverview(
                total_cost_usd=0.0,
                total_calls=0,
                total_tokens=0,
                avg_cost_per_call=0.0,
                avg_cost_per_1k_tokens=0.0,
                provider_count=0,
                language_pairs=[],
            )

        total_cost = sum(m.total_cost_usd for m in all_metrics)
        total_calls = sum(m.total_calls for m in all_metrics)
        total_tokens = sum(
            m.total_input_tokens + m.total_output_tokens
            for m in all_metrics
        )
        providers = {m.provider for m in all_metrics}
        lang_pairs = sorted({m.language_pair for m in all_metrics})

        return CostOverview(
            total_cost_usd=total_cost,
            total_calls=total_calls,
            total_tokens=total_tokens,
            avg_cost_per_call=total_cost / total_calls if total_calls > 0 else 0.0,
            avg_cost_per_1k_tokens=(total_cost / total_tokens * 1000) if total_tokens > 0 else 0.0,
            provider_count=len(providers),
            language_pairs=lang_pairs,
        )

    def get_provider_breakdown(self) -> List[ProviderCostSummary]:
        """Get per-provider cost breakdown."""
        all_metrics = self._tracker.get_all_metrics()

        # Group by provider
        provider_data: Dict[str, List[ProviderMetrics]] = {}
        for m in all_metrics:
            provider_data.setdefault(m.provider, []).append(m)

        summaries = []
        for provider, metrics_list in sorted(provider_data.items()):
            total_cost = sum(m.total_cost_usd for m in metrics_list)
            total_success = sum(m.success_count for m in metrics_list)
            total_failure = sum(m.failure_count for m in metrics_list)
            total_calls = total_success + total_failure
            total_latency = sum(m.total_latency_ms for m in metrics_list)
            total_quality = sum(m.total_quality_score for m in metrics_list)
            total_input = sum(m.total_input_tokens for m in metrics_list)
            total_output = sum(m.total_output_tokens for m in metrics_list)
            total_tokens = total_input + total_output

            summaries.append(ProviderCostSummary(
                provider=provider,
                total_cost_usd=total_cost,
                total_calls=total_calls,
                success_rate=total_success / total_calls if total_calls > 0 else 0.0,
                avg_latency_ms=total_latency / total_success if total_success > 0 else 0.0,
                avg_quality=total_quality / total_success if total_success > 0 else 0.0,
                cost_per_1k_tokens=(total_cost / total_tokens * 1000) if total_tokens > 0 else 0.0,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
            ))

        return summaries

    def get_language_pair_costs(self) -> Dict[str, float]:
        """Get total cost per language pair."""
        all_metrics = self._tracker.get_all_metrics()
        costs: Dict[str, float] = {}
        for m in all_metrics:
            costs[m.language_pair] = costs.get(m.language_pair, 0.0) + m.total_cost_usd
        return {k: round(v, 4) for k, v in sorted(costs.items())}

    def estimate_cost(
        self,
        pages: int = 1,
        language_pair: str = "*",
        provider: Optional[str] = None,
    ) -> CostEstimate:
        """Estimate cost for a translation job.

        Uses historical data to project cost. Falls back to rough
        estimates if no data available.
        """
        estimated_tokens = pages * self.TOKENS_PER_PAGE

        # Try to use historical data
        all_metrics = self._tracker.get_all_metrics()
        relevant = [
            m for m in all_metrics
            if (language_pair == "*" or m.language_pair == language_pair)
            and (provider is None or m.provider == provider)
        ]

        if relevant:
            total_cost = sum(m.total_cost_usd for m in relevant)
            total_tokens = sum(
                m.total_input_tokens + m.total_output_tokens
                for m in relevant
            )
            if total_tokens > 0:
                cost_per_1k = (total_cost / total_tokens) * 1000
                estimated_cost = (estimated_tokens / 1000) * cost_per_1k
                best_provider = max(relevant, key=lambda m: m.total_calls).provider

                return CostEstimate(
                    estimated_tokens=estimated_tokens,
                    estimated_cost_usd=estimated_cost,
                    provider=best_provider,
                    cost_per_1k_tokens=cost_per_1k,
                    confidence="high" if total_tokens > 10000 else "medium",
                )

        # Fallback: rough estimate
        default_cost_per_1k = 0.003  # ~$3/million tokens
        return CostEstimate(
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=(estimated_tokens / 1000) * default_cost_per_1k,
            provider=provider or "unknown",
            cost_per_1k_tokens=default_cost_per_1k,
            confidence="low",
        )

    def get_cheapest_provider(
        self, language_pair: str = "*",
    ) -> Optional[ProviderCostSummary]:
        """Find the cheapest provider for a language pair."""
        breakdown = self.get_provider_breakdown()
        if not breakdown:
            return None

        if language_pair != "*":
            # Filter to providers that handle this language pair
            relevant = self._tracker.get_providers_for(language_pair=language_pair)
            relevant_providers = {m.provider for m in relevant}
            breakdown = [s for s in breakdown if s.provider in relevant_providers]

        if not breakdown:
            return None

        # Cheapest by cost_per_1k_tokens (excluding zero-cost entries)
        with_cost = [s for s in breakdown if s.cost_per_1k_tokens > 0]
        if with_cost:
            return min(with_cost, key=lambda s: s.cost_per_1k_tokens)
        return breakdown[0]

    def get_best_value_provider(
        self, language_pair: str = "*",
    ) -> Optional[ProviderCostSummary]:
        """Find provider with best quality/cost ratio."""
        breakdown = self.get_provider_breakdown()
        if not breakdown:
            return None

        # Score = quality / cost (higher is better)
        def value_score(s: ProviderCostSummary) -> float:
            if s.cost_per_1k_tokens <= 0:
                return s.avg_quality * 1000  # free = high value
            return s.avg_quality / s.cost_per_1k_tokens

        return max(breakdown, key=value_score)
