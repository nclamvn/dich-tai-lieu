"""
Unit tests for api/services/extraction_feedback.py — feedback loop.

Target: 85%+ coverage of ExtractionFeedbackLoop, FeedbackResult, FeedbackLoopResult.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.extraction_feedback import (
    ExtractionFeedbackLoop,
    ExtractionStrategy,
    FeedbackAction,
    FeedbackResult,
    FeedbackLoopResult,
    DEFAULT_FALLBACK_CHAIN,
)
from api.services.eqs import EQSReport, ExtractionQualityScorer, SignalScore


# ---------------------------------------------------------------------------
# FeedbackResult
# ---------------------------------------------------------------------------

class TestFeedbackResult:
    def test_to_dict(self):
        report = EQSReport(overall_score=0.8, grade="B")
        fb = FeedbackResult(
            action=FeedbackAction.ACCEPT,
            strategy_used=ExtractionStrategy.TEXT,
            eqs_report=report,
            iteration=1,
            reason="Good",
        )
        d = fb.to_dict()
        assert d["action"] == "accept"
        assert d["strategy_used"] == "text"
        assert d["eqs_score"] == 0.8
        assert d["eqs_grade"] == "B"
        assert d["next_strategy"] is None
        assert d["iteration"] == 1

    def test_to_dict_with_next_strategy(self):
        report = EQSReport(overall_score=0.3, grade="F")
        fb = FeedbackResult(
            action=FeedbackAction.RETRY,
            strategy_used=ExtractionStrategy.TEXT,
            eqs_report=report,
            next_strategy=ExtractionStrategy.OCR,
            iteration=1,
            reason="Low score",
        )
        d = fb.to_dict()
        assert d["next_strategy"] == "ocr"
        assert d["action"] == "retry"


# ---------------------------------------------------------------------------
# FeedbackLoopResult
# ---------------------------------------------------------------------------

class TestFeedbackLoopResult:
    def test_empty_result(self):
        r = FeedbackLoopResult()
        assert r.total_iterations == 0
        assert r.best_result is None

    def test_best_result(self):
        low = FeedbackResult(
            action=FeedbackAction.RETRY,
            strategy_used=ExtractionStrategy.TEXT,
            eqs_report=EQSReport(overall_score=0.3, grade="F"),
        )
        high = FeedbackResult(
            action=FeedbackAction.ACCEPT,
            strategy_used=ExtractionStrategy.OCR,
            eqs_report=EQSReport(overall_score=0.8, grade="B"),
        )
        r = FeedbackLoopResult(iterations=[low, high])
        assert r.best_result == high
        assert r.total_iterations == 2

    def test_to_dict(self):
        fb = FeedbackResult(
            action=FeedbackAction.ACCEPT,
            strategy_used=ExtractionStrategy.TEXT,
            eqs_report=EQSReport(overall_score=0.9, grade="A"),
            iteration=1,
            reason="Good",
        )
        r = FeedbackLoopResult(
            iterations=[fb],
            final_action=FeedbackAction.ACCEPT,
            total_time=1.5,
        )
        d = r.to_dict()
        assert d["final_action"] == "accept"
        assert d["total_iterations"] == 1
        assert d["best_score"] == 0.9
        assert d["best_strategy"] == "text"
        assert len(d["iterations"]) == 1

    def test_to_dict_empty(self):
        r = FeedbackLoopResult()
        d = r.to_dict()
        assert d["best_score"] == 0.0
        assert d["best_strategy"] is None


# ---------------------------------------------------------------------------
# ExtractionFeedbackLoop.evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def setup_method(self):
        self.loop = ExtractionFeedbackLoop(min_score=0.6, max_retries=3)

    def test_accept_high_score(self):
        """Score above threshold → ACCEPT."""
        good_text = (
            "# Introduction\n\n"
            "This is a well-structured English document with proper content.\n"
            "It has multiple sentences and paragraphs for quality assessment.\n\n"
            "## Methods\n\n"
            "We applied machine learning to solve this problem effectively.\n"
            "- Step one: data collection\n"
            "- Step two: model training\n"
        ) * 10
        result = self.loop.evaluate(
            text=good_text,
            strategy=ExtractionStrategy.TEXT,
            total_pages=1,
            expected_language="en",
        )
        assert result.action == FeedbackAction.ACCEPT
        assert result.eqs_report.overall_score >= 0.6

    def test_retry_low_score(self):
        """Score below threshold → RETRY with next strategy."""
        result = self.loop.evaluate(
            text="x",
            strategy=ExtractionStrategy.TEXT,
            total_pages=100,
            iteration=1,
        )
        assert result.action == FeedbackAction.RETRY
        assert result.next_strategy == ExtractionStrategy.OCR

    def test_retry_from_ocr(self):
        """Low OCR score → RETRY with vision."""
        result = self.loop.evaluate(
            text="x",
            strategy=ExtractionStrategy.OCR,
            total_pages=50,
            iteration=2,
        )
        assert result.action == FeedbackAction.RETRY
        assert result.next_strategy == ExtractionStrategy.VISION

    def test_escalate_from_vision(self):
        """Low vision score → ESCALATE (manual_review is not automated)."""
        result = self.loop.evaluate(
            text="x",
            strategy=ExtractionStrategy.VISION,
            total_pages=50,
            iteration=2,
        )
        assert result.action == FeedbackAction.ESCALATE
        assert result.next_strategy == ExtractionStrategy.MANUAL_REVIEW

    def test_escalate_max_retries(self):
        """Max retries reached → ESCALATE."""
        result = self.loop.evaluate(
            text="x",
            strategy=ExtractionStrategy.TEXT,
            total_pages=100,
            iteration=3,  # equals max_retries
        )
        assert result.action == FeedbackAction.ESCALATE
        assert "Max retries" in result.reason

    def test_empty_text_low_score(self):
        """Empty text → low score → RETRY."""
        result = self.loop.evaluate(
            text="",
            strategy=ExtractionStrategy.TEXT,
            total_pages=5,
            iteration=1,
        )
        assert result.eqs_report.overall_score == 0.0
        assert result.action in (FeedbackAction.RETRY, FeedbackAction.ESCALATE)


# ---------------------------------------------------------------------------
# ExtractionFeedbackLoop._next_strategy
# ---------------------------------------------------------------------------

class TestNextStrategy:
    def setup_method(self):
        self.loop = ExtractionFeedbackLoop()

    def test_text_to_ocr(self):
        assert self.loop._next_strategy(ExtractionStrategy.TEXT) == ExtractionStrategy.OCR

    def test_ocr_to_vision(self):
        assert self.loop._next_strategy(ExtractionStrategy.OCR) == ExtractionStrategy.VISION

    def test_vision_to_manual(self):
        assert self.loop._next_strategy(ExtractionStrategy.VISION) == ExtractionStrategy.MANUAL_REVIEW

    def test_manual_stays_manual(self):
        # manual_review is last in chain
        result = self.loop._next_strategy(ExtractionStrategy.MANUAL_REVIEW)
        # No next strategy after manual_review in default chain
        # Since manual_review IS in the chain as last, idx+1 is out of bounds
        assert result == ExtractionStrategy.MANUAL_REVIEW

    def test_unknown_strategy(self):
        """Strategy not in chain → fallback to manual_review."""
        loop = ExtractionFeedbackLoop(fallback_chain=[ExtractionStrategy.TEXT])
        result = loop._next_strategy(ExtractionStrategy.OCR)
        assert result == ExtractionStrategy.MANUAL_REVIEW

    def test_custom_chain(self):
        loop = ExtractionFeedbackLoop(
            fallback_chain=[ExtractionStrategy.OCR, ExtractionStrategy.VISION]
        )
        assert loop._next_strategy(ExtractionStrategy.OCR) == ExtractionStrategy.VISION


# ---------------------------------------------------------------------------
# ExtractionFeedbackLoop.run_loop
# ---------------------------------------------------------------------------

class TestRunLoop:
    @pytest.mark.asyncio
    async def test_accept_first_try(self):
        """Good text → accept on first iteration."""
        good_text = (
            "# Document Title\n\n"
            "This is well-structured content with proper English language.\n"
            "Multiple sentences provide enough density for quality scoring.\n\n"
            "## Section One\n\n"
            "Detailed explanation of the methodology used in this research.\n"
            "- Point A: data preprocessing steps\n"
            "- Point B: model architecture design\n"
        ) * 15

        extract_fn = AsyncMock(return_value=good_text)
        loop = ExtractionFeedbackLoop(min_score=0.5)

        result = await loop.run_loop(
            extract_fn=extract_fn,
            initial_strategy=ExtractionStrategy.TEXT,
            total_pages=1,
            expected_language="en",
        )
        assert result.final_action == FeedbackAction.ACCEPT
        assert result.total_iterations == 1
        extract_fn.assert_called_once_with(ExtractionStrategy.TEXT)

    @pytest.mark.asyncio
    async def test_retry_then_accept(self):
        """First extraction bad, second good → accept on iteration 2."""
        good_text = (
            "# Well-formed Document\n\n"
            "This document has proper structure and content density.\n"
            "It contains detailed paragraphs with multiple sentences.\n\n"
            "## Analysis Section\n\n"
            "The analysis demonstrates significant findings in the data.\n"
            "- Finding one: improved accuracy\n"
            "- Finding two: reduced latency\n"
        ) * 15

        call_count = 0
        async def extract_fn(strategy):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "x"  # bad text
            return good_text

        loop = ExtractionFeedbackLoop(min_score=0.5, max_retries=3)
        result = await loop.run_loop(
            extract_fn=extract_fn,
            initial_strategy=ExtractionStrategy.TEXT,
            total_pages=1,
        )
        assert result.total_iterations == 2
        assert result.final_action == FeedbackAction.ACCEPT

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """All extractions bad → escalate."""
        extract_fn = AsyncMock(return_value="x")
        loop = ExtractionFeedbackLoop(min_score=0.9, max_retries=3)

        result = await loop.run_loop(
            extract_fn=extract_fn,
            total_pages=100,
        )
        assert result.final_action == FeedbackAction.ESCALATE
        assert result.total_iterations >= 2

    @pytest.mark.asyncio
    async def test_extraction_exception_handled(self):
        """Exception during extraction → treated as empty text."""
        call_count = 0
        async def extract_fn(strategy):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("extraction failed")
            return "x"  # still bad

        loop = ExtractionFeedbackLoop(min_score=0.9, max_retries=2)
        result = await loop.run_loop(
            extract_fn=extract_fn,
            total_pages=10,
        )
        # Should not crash, should have multiple iterations
        assert result.total_iterations >= 1

    @pytest.mark.asyncio
    async def test_loop_records_time(self):
        extract_fn = AsyncMock(return_value="Some adequate text " * 100)
        loop = ExtractionFeedbackLoop(min_score=0.1)

        result = await loop.run_loop(
            extract_fn=extract_fn,
            total_pages=1,
        )
        assert result.total_time >= 0.0


# ---------------------------------------------------------------------------
# Default fallback chain
# ---------------------------------------------------------------------------

class TestFallbackChain:
    def test_default_chain_order(self):
        assert DEFAULT_FALLBACK_CHAIN == [
            ExtractionStrategy.TEXT,
            ExtractionStrategy.OCR,
            ExtractionStrategy.VISION,
            ExtractionStrategy.MANUAL_REVIEW,
        ]

    def test_custom_chain(self):
        chain = [ExtractionStrategy.VISION, ExtractionStrategy.TEXT]
        loop = ExtractionFeedbackLoop(fallback_chain=chain)
        assert loop.fallback_chain == chain


# ---------------------------------------------------------------------------
# Strategy enum
# ---------------------------------------------------------------------------

class TestExtractionStrategy:
    def test_values(self):
        assert ExtractionStrategy.TEXT.value == "text"
        assert ExtractionStrategy.OCR.value == "ocr"
        assert ExtractionStrategy.VISION.value == "vision"
        assert ExtractionStrategy.MANUAL_REVIEW.value == "manual_review"

    def test_string_enum(self):
        # ExtractionStrategy inherits from str
        assert isinstance(ExtractionStrategy.TEXT, str)
        assert ExtractionStrategy.TEXT == "text"
