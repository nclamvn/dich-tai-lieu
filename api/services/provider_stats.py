"""
Provider Statistics Tracker — in-memory + JSON persistence.

Tracks per-(provider, language_pair, document_type) metrics:
  - success/failure counts
  - average latency
  - average quality (EQS) score
  - average cost per 1k tokens

Thread-safe, standalone module. No extraction/translation imports.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ProviderMetrics:
    """Aggregated metrics for one (provider, lang_pair, doc_type) combo."""

    provider: str
    language_pair: str  # e.g. "en→vi", "ja→en", "*" for any
    document_type: str  # e.g. "academic", "general", "*" for any

    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    total_quality_score: float = 0.0  # sum of EQS scores
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def total_calls(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count

    @property
    def avg_quality(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_quality_score / self.success_count

    @property
    def cost_per_1k_tokens(self) -> float:
        total_tokens = self.total_input_tokens + self.total_output_tokens
        if total_tokens == 0:
            return 0.0
        return (self.total_cost_usd / total_tokens) * 1000

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "language_pair": self.language_pair,
            "document_type": self.document_type,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_quality": round(self.avg_quality, 4),
            "cost_per_1k_tokens": round(self.cost_per_1k_tokens, 6),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_calls": self.total_calls,
        }


@dataclass
class CallRecord:
    """One completed LLM call for recording."""

    provider: str
    language_pair: str  # "en→vi"
    document_type: str  # "academic", "general", "technical"
    success: bool
    latency_ms: float
    quality_score: float = 0.0  # EQS score if available
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


# ---------------------------------------------------------------------------
# Stats Tracker
# ---------------------------------------------------------------------------

class ProviderStatsTracker:
    """Thread-safe in-memory stats with optional JSON persistence.

    Usage::

        tracker = ProviderStatsTracker(persist_path="data/provider_stats.json")

        # After each LLM call
        tracker.record(CallRecord(
            provider="openai",
            language_pair="en→vi",
            document_type="academic",
            success=True,
            latency_ms=1200,
            quality_score=0.85,
            cost_usd=0.003,
            input_tokens=500,
            output_tokens=800,
        ))

        # Query stats
        metrics = tracker.get_metrics("openai", "en→vi", "academic")
        all_stats = tracker.get_all_metrics()
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._metrics: Dict[Tuple[str, str, str], ProviderMetrics] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        self._dirty = False

        if self._persist_path:
            self._load()

    def record(self, call: CallRecord) -> None:
        """Record a completed LLM call."""
        key = (call.provider, call.language_pair, call.document_type)

        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = ProviderMetrics(
                    provider=call.provider,
                    language_pair=call.language_pair,
                    document_type=call.document_type,
                )

            m = self._metrics[key]
            if call.success:
                m.success_count += 1
                m.total_latency_ms += call.latency_ms
                m.total_quality_score += call.quality_score
                m.total_cost_usd += call.cost_usd
                m.total_input_tokens += call.input_tokens
                m.total_output_tokens += call.output_tokens
            else:
                m.failure_count += 1

            self._dirty = True

        # Persist outside lock to avoid holding it during IO
        if self._persist_path and self._dirty:
            self._save()

    def get_metrics(
        self,
        provider: str,
        language_pair: str = "*",
        document_type: str = "*",
    ) -> Optional[ProviderMetrics]:
        """Get metrics for a specific (provider, lang_pair, doc_type) combo."""
        key = (provider, language_pair, document_type)
        with self._lock:
            return self._metrics.get(key)

    def get_provider_summary(self, provider: str) -> ProviderMetrics:
        """Aggregate all metrics for a provider across all lang/doc combos."""
        with self._lock:
            agg = ProviderMetrics(
                provider=provider,
                language_pair="*",
                document_type="*",
            )
            for (p, _, _), m in self._metrics.items():
                if p == provider:
                    agg.success_count += m.success_count
                    agg.failure_count += m.failure_count
                    agg.total_latency_ms += m.total_latency_ms
                    agg.total_quality_score += m.total_quality_score
                    agg.total_cost_usd += m.total_cost_usd
                    agg.total_input_tokens += m.total_input_tokens
                    agg.total_output_tokens += m.total_output_tokens
            return agg

    def get_all_metrics(self) -> List[ProviderMetrics]:
        """Return all tracked metrics."""
        with self._lock:
            return list(self._metrics.values())

    def get_providers_for(
        self,
        language_pair: str = "*",
        document_type: str = "*",
    ) -> List[ProviderMetrics]:
        """Get metrics for all providers matching a lang_pair/doc_type."""
        with self._lock:
            results = []
            for (_, lp, dt), m in self._metrics.items():
                if (lp == language_pair or language_pair == "*") and \
                   (dt == document_type or document_type == "*"):
                    results.append(m)
            return results

    def clear(self) -> None:
        """Clear all metrics (for testing)."""
        with self._lock:
            self._metrics.clear()
            self._dirty = True
        if self._persist_path:
            self._save()

    def to_dict(self) -> dict:
        """Export all metrics as a dict."""
        with self._lock:
            return {
                "metrics": [m.to_dict() for m in self._metrics.values()],
                "total_providers": len(
                    {m.provider for m in self._metrics.values()}
                ),
                "total_records": sum(
                    m.total_calls for m in self._metrics.values()
                ),
            }

    # --- Persistence ---

    def _save(self) -> None:
        """Persist metrics to JSON file."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            with self._lock:
                for m in self._metrics.values():
                    data.append({
                        "provider": m.provider,
                        "language_pair": m.language_pair,
                        "document_type": m.document_type,
                        "success_count": m.success_count,
                        "failure_count": m.failure_count,
                        "total_latency_ms": m.total_latency_ms,
                        "total_quality_score": m.total_quality_score,
                        "total_cost_usd": m.total_cost_usd,
                        "total_input_tokens": m.total_input_tokens,
                        "total_output_tokens": m.total_output_tokens,
                    })
                self._dirty = False

            self._persist_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Failed to save provider stats: %s", exc)

    def _load(self) -> None:
        """Load metrics from JSON file."""
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
            with self._lock:
                for item in raw:
                    key = (
                        item["provider"],
                        item["language_pair"],
                        item["document_type"],
                    )
                    self._metrics[key] = ProviderMetrics(
                        provider=item["provider"],
                        language_pair=item["language_pair"],
                        document_type=item["document_type"],
                        success_count=item.get("success_count", 0),
                        failure_count=item.get("failure_count", 0),
                        total_latency_ms=item.get("total_latency_ms", 0.0),
                        total_quality_score=item.get("total_quality_score", 0.0),
                        total_cost_usd=item.get("total_cost_usd", 0.0),
                        total_input_tokens=item.get("total_input_tokens", 0),
                        total_output_tokens=item.get("total_output_tokens", 0),
                    )
            logger.info(
                "Loaded %d provider stats entries from %s",
                len(self._metrics), self._persist_path,
            )
        except Exception as exc:
            logger.warning("Failed to load provider stats: %s", exc)
