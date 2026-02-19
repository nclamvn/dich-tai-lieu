"""
Extraction Feedback Loop — auto-retry with quality-driven fallback.

Given an extraction result and its EQS report, decides whether to:
  1. Accept   — quality is good enough
  2. Retry    — try the next fallback strategy
  3. Escalate — flag for manual review

Strategy chain:  text → ocr → vision → manual_review

This module is **standalone** — it does not import extraction modules.
It returns *recommendations*; the caller decides whether to act on them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from api.services.eqs import EQSReport, ExtractionQualityScorer
from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class ExtractionStrategy(str, Enum):
    """Extraction method identifiers (mirrors core names)."""
    TEXT = "text"
    OCR = "ocr"
    VISION = "vision"
    MANUAL_REVIEW = "manual_review"


class FeedbackAction(str, Enum):
    ACCEPT = "accept"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass
class FeedbackResult:
    """Outcome of one feedback-loop iteration."""
    action: FeedbackAction
    strategy_used: ExtractionStrategy
    eqs_report: EQSReport
    next_strategy: Optional[ExtractionStrategy] = None
    iteration: int = 1
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "strategy_used": self.strategy_used.value,
            "eqs_score": round(self.eqs_report.overall_score, 4),
            "eqs_grade": self.eqs_report.grade,
            "next_strategy": self.next_strategy.value if self.next_strategy else None,
            "iteration": self.iteration,
            "reason": self.reason,
        }


@dataclass
class FeedbackLoopResult:
    """Aggregate result across all feedback-loop iterations."""
    iterations: List[FeedbackResult] = field(default_factory=list)
    final_action: FeedbackAction = FeedbackAction.ACCEPT
    total_time: float = 0.0

    @property
    def best_result(self) -> Optional[FeedbackResult]:
        """Return the iteration with the highest EQS score."""
        if not self.iterations:
            return None
        return max(self.iterations, key=lambda r: r.eqs_report.overall_score)

    @property
    def total_iterations(self) -> int:
        return len(self.iterations)

    def to_dict(self) -> dict:
        best = self.best_result
        return {
            "final_action": self.final_action.value,
            "total_iterations": self.total_iterations,
            "total_time": round(self.total_time, 3),
            "best_score": round(best.eqs_report.overall_score, 4) if best else 0.0,
            "best_strategy": best.strategy_used.value if best else None,
            "iterations": [it.to_dict() for it in self.iterations],
        }


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

# Default strategy order — each strategy escalates to the next
DEFAULT_FALLBACK_CHAIN: List[ExtractionStrategy] = [
    ExtractionStrategy.TEXT,
    ExtractionStrategy.OCR,
    ExtractionStrategy.VISION,
    ExtractionStrategy.MANUAL_REVIEW,
]


# ---------------------------------------------------------------------------
# Feedback Loop
# ---------------------------------------------------------------------------

class ExtractionFeedbackLoop:
    """Quality-driven extraction feedback loop.

    Usage::

        loop = ExtractionFeedbackLoop(min_score=0.6)

        # Evaluate first extraction attempt
        result = loop.evaluate(
            text="...",
            strategy=ExtractionStrategy.TEXT,
            total_pages=10,
        )

        if result.action == FeedbackAction.RETRY:
            # Caller re-extracts with result.next_strategy
            ...

    For automatic multi-step loops, use ``run_loop()`` with an
    extraction callback.
    """

    def __init__(
        self,
        min_score: float = 0.6,
        max_retries: int = 3,
        scorer: Optional[ExtractionQualityScorer] = None,
        fallback_chain: Optional[List[ExtractionStrategy]] = None,
    ):
        self.min_score = min_score
        self.max_retries = max_retries
        self.scorer = scorer or ExtractionQualityScorer()
        self.fallback_chain = fallback_chain or list(DEFAULT_FALLBACK_CHAIN)

    def evaluate(
        self,
        text: str,
        strategy: ExtractionStrategy,
        total_pages: int = 1,
        expected_language: Optional[str] = None,
        iteration: int = 1,
    ) -> FeedbackResult:
        """Evaluate extraction quality and recommend next action.

        Args:
            text: Extracted text content.
            strategy: Strategy that produced this text.
            total_pages: Total pages in source document.
            expected_language: Expected language code.
            iteration: Current iteration number (1-based).

        Returns:
            FeedbackResult with action and optional next_strategy.
        """
        report = self.scorer.score(
            text=text,
            total_pages=total_pages,
            expected_language=expected_language,
        )

        # Determine action
        if report.overall_score >= self.min_score:
            return FeedbackResult(
                action=FeedbackAction.ACCEPT,
                strategy_used=strategy,
                eqs_report=report,
                iteration=iteration,
                reason=f"Score {report.overall_score:.3f} >= threshold {self.min_score}",
            )

        # Check if we've exhausted retries
        if iteration >= self.max_retries:
            return FeedbackResult(
                action=FeedbackAction.ESCALATE,
                strategy_used=strategy,
                eqs_report=report,
                iteration=iteration,
                reason=f"Max retries ({self.max_retries}) reached. Score {report.overall_score:.3f}",
            )

        # Find next strategy in fallback chain
        next_strategy = self._next_strategy(strategy)

        if next_strategy == ExtractionStrategy.MANUAL_REVIEW:
            return FeedbackResult(
                action=FeedbackAction.ESCALATE,
                strategy_used=strategy,
                eqs_report=report,
                next_strategy=next_strategy,
                iteration=iteration,
                reason=f"No more automated strategies. Score {report.overall_score:.3f}",
            )

        return FeedbackResult(
            action=FeedbackAction.RETRY,
            strategy_used=strategy,
            eqs_report=report,
            next_strategy=next_strategy,
            iteration=iteration,
            reason=(
                f"Score {report.overall_score:.3f} < threshold {self.min_score}. "
                f"Retry with {next_strategy.value}"
            ),
        )

    async def run_loop(
        self,
        extract_fn: Callable,
        initial_strategy: ExtractionStrategy = ExtractionStrategy.TEXT,
        total_pages: int = 1,
        expected_language: Optional[str] = None,
    ) -> FeedbackLoopResult:
        """Run the full feedback loop with automatic retries.

        Args:
            extract_fn: Async callable ``(strategy) -> str`` that performs
                extraction and returns the text.
            initial_strategy: Starting strategy.
            total_pages: Total pages in source document.
            expected_language: Expected language code.

        Returns:
            FeedbackLoopResult with all iteration details.
        """
        loop_result = FeedbackLoopResult()
        start_time = time.time()
        strategy = initial_strategy
        iteration = 0

        while iteration < self.max_retries:
            iteration += 1

            try:
                text = await extract_fn(strategy)
            except Exception as exc:
                logger.warning(
                    "Extraction failed with strategy=%s: %s",
                    strategy.value, exc,
                )
                text = ""

            fb = self.evaluate(
                text=text,
                strategy=strategy,
                total_pages=total_pages,
                expected_language=expected_language,
                iteration=iteration,
            )
            loop_result.iterations.append(fb)

            logger.info(
                "Feedback loop iter=%d strategy=%s score=%.3f action=%s",
                iteration, strategy.value,
                fb.eqs_report.overall_score, fb.action.value,
            )

            if fb.action == FeedbackAction.ACCEPT:
                loop_result.final_action = FeedbackAction.ACCEPT
                break

            if fb.action == FeedbackAction.ESCALATE:
                loop_result.final_action = FeedbackAction.ESCALATE
                break

            # Retry with next strategy
            if fb.next_strategy is None:
                loop_result.final_action = FeedbackAction.ESCALATE
                break
            strategy = fb.next_strategy

        loop_result.total_time = time.time() - start_time
        return loop_result

    def _next_strategy(
        self, current: ExtractionStrategy
    ) -> Optional[ExtractionStrategy]:
        """Return the next strategy in the fallback chain."""
        try:
            idx = self.fallback_chain.index(current)
            if idx + 1 < len(self.fallback_chain):
                return self.fallback_chain[idx + 1]
        except ValueError:
            pass
        return ExtractionStrategy.MANUAL_REVIEW
