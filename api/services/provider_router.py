"""
Quality-Aware Provider Router (QAPR).

Selects the best AI provider for a translation job based on:
  - Historical performance (from ProviderStatsTracker)
  - Language pair affinity
  - Document type suitability
  - Cost constraints

Three routing modes:
  - BEST_QUALITY:         Maximise EQS score regardless of cost
  - CHEAPEST_GOOD_ENOUGH: Minimise cost among providers above quality threshold
  - BALANCED:             Weighted blend of quality, cost, and latency

Standalone module — does not import translation or extraction code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from api.services.provider_stats import ProviderStatsTracker, ProviderMetrics
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class RoutingMode(str, Enum):
    BEST_QUALITY = "best_quality"
    CHEAPEST_GOOD_ENOUGH = "cheapest_good_enough"
    BALANCED = "balanced"


@dataclass
class RoutingDecision:
    """Result of a provider selection."""

    provider: str
    mode: RoutingMode
    score: float  # composite routing score (higher = better pick)
    reason: str
    candidates: List[Dict] = field(default_factory=list)  # all scored candidates

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "mode": self.mode.value,
            "score": round(self.score, 4),
            "reason": self.reason,
            "candidates": self.candidates,
        }


# ---------------------------------------------------------------------------
# Cold-start defaults — used when no historical data available
# ---------------------------------------------------------------------------

# Based on known provider characteristics
COLD_START_DEFAULTS: Dict[str, Dict] = {
    "openai": {
        "quality": 0.82,
        "cost_per_1k": 0.0125,  # ~$2.50/1M in + $10/1M out averaged
        "latency_ms": 800,
        "strengths": {"en→*", "general", "technical"},
    },
    "anthropic": {
        "quality": 0.85,
        "cost_per_1k": 0.018,  # ~$3/1M in + $15/1M out averaged
        "latency_ms": 1000,
        "strengths": {"*→en", "academic", "creative"},
    },
    "deepseek": {
        "quality": 0.75,
        "cost_per_1k": 0.00042,  # ~$0.14/1M in + $0.28/1M out averaged
        "latency_ms": 1200,
        "strengths": {"zh→*", "*→zh", "general"},
    },
}

# Known provider affinities for language pairs
LANGUAGE_AFFINITIES: Dict[str, List[str]] = {
    "openai": ["en→vi", "en→ja", "en→zh", "en→ko", "en→de", "en→fr"],
    "anthropic": ["en→vi", "ja→en", "de→en", "fr→en", "academic"],
    "deepseek": ["zh→en", "en→zh", "zh→vi", "zh→ja"],
}

# Quality threshold for "good enough"
DEFAULT_QUALITY_THRESHOLD = 0.6

# Available providers (must match UnifiedLLMClient.PROVIDER_ORDER)
KNOWN_PROVIDERS = ["openai", "anthropic", "deepseek"]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ProviderRouter:
    """Quality-aware provider selection.

    Usage::

        router = ProviderRouter(stats_tracker=tracker, mode=RoutingMode.BALANCED)

        decision = router.select(
            language_pair="en→vi",
            document_type="academic",
        )
        print(decision.provider)   # "anthropic"
        print(decision.reason)     # "Best quality for en→vi academic"
    """

    def __init__(
        self,
        stats_tracker: Optional[ProviderStatsTracker] = None,
        mode: RoutingMode = RoutingMode.BALANCED,
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
        available_providers: Optional[List[str]] = None,
    ):
        self.stats = stats_tracker or ProviderStatsTracker()
        self.mode = mode
        self.quality_threshold = quality_threshold
        self.available_providers = available_providers or list(KNOWN_PROVIDERS)

    def select(
        self,
        language_pair: str = "*",
        document_type: str = "*",
        mode: Optional[RoutingMode] = None,
        exclude_providers: Optional[List[str]] = None,
    ) -> RoutingDecision:
        """Select the best provider for given context.

        Args:
            language_pair: Source→target language pair (e.g. "en→vi").
            document_type: Document type (e.g. "academic", "general").
            mode: Override the default routing mode for this call.
            exclude_providers: Providers to exclude (e.g. already failed).

        Returns:
            RoutingDecision with selected provider and reasoning.
        """
        effective_mode = mode or self.mode
        excluded = set(exclude_providers or [])
        candidates = [p for p in self.available_providers if p not in excluded]

        if not candidates:
            # Fallback: use first available provider
            return RoutingDecision(
                provider=self.available_providers[0] if self.available_providers else "openai",
                mode=effective_mode,
                score=0.0,
                reason="No candidates available, using fallback",
            )

        # Score each candidate
        scored = []
        for provider in candidates:
            score_info = self._score_provider(
                provider, language_pair, document_type, effective_mode,
            )
            scored.append(score_info)

        # Sort by composite score (descending)
        scored.sort(key=lambda x: x["composite"], reverse=True)

        best = scored[0]
        return RoutingDecision(
            provider=best["provider"],
            mode=effective_mode,
            score=best["composite"],
            reason=best["reason"],
            candidates=[
                {
                    "provider": s["provider"],
                    "score": round(s["composite"], 4),
                    "quality": round(s["quality"], 4),
                    "cost": round(s["cost_score"], 4),
                    "latency": round(s["latency_score"], 4),
                    "data_points": s["data_points"],
                }
                for s in scored
            ],
        )

    def _score_provider(
        self,
        provider: str,
        language_pair: str,
        document_type: str,
        mode: RoutingMode,
    ) -> Dict:
        """Score a single provider for the given context."""

        # Try to get specific metrics first, then broader
        metrics = self._get_best_metrics(provider, language_pair, document_type)
        data_points = 0

        if metrics and metrics.total_calls >= 3:
            # Enough data — use historical metrics
            quality = metrics.avg_quality
            cost_rate = metrics.cost_per_1k_tokens
            latency = metrics.avg_latency_ms
            success_rate = metrics.success_rate
            data_points = metrics.total_calls
        else:
            # Cold start — use defaults + affinities
            defaults = COLD_START_DEFAULTS.get(provider, {
                "quality": 0.7, "cost_per_1k": 0.01, "latency_ms": 1000,
                "strengths": set(),
            })
            quality = defaults["quality"]
            cost_rate = defaults["cost_per_1k"]
            latency = defaults["latency_ms"]
            success_rate = 0.95  # assume high success for cold start

            # Affinity boost
            affinities = LANGUAGE_AFFINITIES.get(provider, [])
            if language_pair in affinities:
                quality += 0.05
            if document_type in defaults.get("strengths", set()):
                quality += 0.03

            # If we have *some* data (1-2 calls), blend with defaults
            if metrics and metrics.total_calls > 0:
                blend = metrics.total_calls / 3  # 0.33 or 0.67
                quality = quality * (1 - blend) + metrics.avg_quality * blend
                if metrics.success_count > 0:
                    cost_rate = cost_rate * (1 - blend) + metrics.cost_per_1k_tokens * blend
                    latency = latency * (1 - blend) + metrics.avg_latency_ms * blend
                data_points = metrics.total_calls

        # Normalise scores to 0.0-1.0 range
        quality_score = min(quality, 1.0)
        cost_score = self._normalise_cost(cost_rate)
        latency_score = self._normalise_latency(latency)
        success_score = success_rate

        # Composite score based on mode
        composite, reason = self._compute_composite(
            provider, quality_score, cost_score, latency_score,
            success_score, mode, language_pair, document_type,
        )

        return {
            "provider": provider,
            "composite": composite,
            "quality": quality_score,
            "cost_score": cost_score,
            "latency_score": latency_score,
            "success_rate": success_rate,
            "data_points": data_points,
            "reason": reason,
        }

    def _compute_composite(
        self,
        provider: str,
        quality: float,
        cost: float,
        latency: float,
        success: float,
        mode: RoutingMode,
        language_pair: str,
        document_type: str,
    ) -> tuple:
        """Compute composite score and reason string based on mode."""

        if mode == RoutingMode.BEST_QUALITY:
            # Quality dominates, cost irrelevant
            composite = quality * 0.6 + success * 0.25 + latency * 0.15
            reason = f"Best quality for {language_pair} {document_type}"

        elif mode == RoutingMode.CHEAPEST_GOOD_ENOUGH:
            if quality < self.quality_threshold:
                # Below threshold — heavily penalise
                composite = quality * 0.1
                reason = f"Below quality threshold ({quality:.2f} < {self.quality_threshold})"
            else:
                # Above threshold — cost dominates
                composite = cost * 0.5 + quality * 0.2 + success * 0.2 + latency * 0.1
                reason = f"Cheapest above threshold for {language_pair}"

        else:  # BALANCED
            composite = quality * 0.35 + cost * 0.25 + latency * 0.15 + success * 0.25
            reason = f"Balanced for {language_pair} {document_type}"

        return composite, reason

    def _get_best_metrics(
        self,
        provider: str,
        language_pair: str,
        document_type: str,
    ) -> Optional[ProviderMetrics]:
        """Get the most specific metrics available.

        Tries in order:
          1. Exact (provider, lang_pair, doc_type)
          2. (provider, lang_pair, "*")
          3. (provider, "*", doc_type)
          4. (provider, "*", "*") — overall provider summary
        """
        # Exact match
        m = self.stats.get_metrics(provider, language_pair, document_type)
        if m and m.total_calls > 0:
            return m

        # Language pair only
        m = self.stats.get_metrics(provider, language_pair, "*")
        if m and m.total_calls > 0:
            return m

        # Doc type only
        m = self.stats.get_metrics(provider, "*", document_type)
        if m and m.total_calls > 0:
            return m

        # Provider summary (aggregate)
        summary = self.stats.get_provider_summary(provider)
        if summary.total_calls > 0:
            return summary

        return None

    @staticmethod
    def _normalise_cost(cost_per_1k: float) -> float:
        """Normalise cost to 0.0-1.0 where 1.0 = cheapest.

        Reference: DeepSeek ~$0.0004/1k (cheap), Anthropic ~$0.018/1k (expensive).
        """
        if cost_per_1k <= 0:
            return 1.0
        # Inverse scale: cheaper = higher score
        # $0.001/1k → 0.95, $0.01/1k → 0.5, $0.02/1k → 0.33
        return min(1.0, 0.01 / (cost_per_1k + 0.001))

    @staticmethod
    def _normalise_latency(latency_ms: float) -> float:
        """Normalise latency to 0.0-1.0 where 1.0 = fastest.

        Reference: 500ms (fast) to 3000ms (slow).
        """
        if latency_ms <= 0:
            return 1.0
        # 500ms → 0.95, 1000ms → 0.67, 2000ms → 0.40, 3000ms → 0.29
        return min(1.0, 800 / (latency_ms + 200))

    def to_dict(self) -> dict:
        """Export router state."""
        return {
            "mode": self.mode.value,
            "quality_threshold": self.quality_threshold,
            "available_providers": self.available_providers,
            "stats": self.stats.to_dict(),
        }
