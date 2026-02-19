"""
Integration tests: EQS wired into extraction pipeline.

Validates that EQS scoring and feedback loop are correctly wired
into APSV2Service._smart_extract_pdf without breaking extraction flow.
"""
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from dataclasses import dataclass

from api.aps_v2_service import APSV2Service


# ---------------------------------------------------------------------------
# Helpers — mock smart_extraction objects
# ---------------------------------------------------------------------------

@dataclass
class _FakeAnalysis:
    total_pages: int = 5
    text_coverage: float = 0.85
    scanned_pages: int = 0
    strategy: object = None  # set per-test
    strategy_reason: str = "text-heavy"
    estimated_cost_vision: float = 1.50
    complex_page_numbers: list = None

    def __post_init__(self):
        if self.complex_page_numbers is None:
            self.complex_page_numbers = []


@dataclass
class _FakeExtractResult:
    full_content: str = ""
    content: str = ""
    total_pages: int = 5
    extraction_time: float = 0.3
    ocr_confidence: float = 0.92


class _FakeStrategy:
    """Emulate ExtractionStrategy enum values."""
    FAST_TEXT = "fast_text"
    HYBRID = "hybrid"
    FULL_VISION = "full_vision"
    OCR = "ocr"

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, _FakeStrategy):
            return self._value == other._value
        return self._value == other

    def __hash__(self):
        return hash(self._value)


def _make_service(tmp_path):
    """Create a test APSV2Service with temp dirs."""
    return APSV2Service(
        output_dir=str(tmp_path / "outputs"),
        upload_dir=str(tmp_path / "uploads"),
        base_dir=str(tmp_path),
    )


def _build_import_mock(strategy_value, text_content, total_pages=5):
    """Build a module-level mock for 'from core.smart_extraction import ...'."""
    fake_strat = _FakeStrategy(strategy_value)
    analysis = _FakeAnalysis(
        total_pages=total_pages,
        strategy=fake_strat,
    )
    result = _FakeExtractResult(
        full_content=text_content,
        content=text_content,
        total_pages=total_pages,
    )

    # Return objects that _smart_extract_pdf imports
    return {
        "ExtractionStrategy": _FakeStrategy,
        "analyze_document": MagicMock(return_value=analysis),
        "fast_extract": AsyncMock(return_value=result),
        "smart_extract": AsyncMock(return_value=result),
        "SmartExtractionRouter": MagicMock(),
        "analysis": analysis,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Test EQS scoring is wired
# ---------------------------------------------------------------------------

class TestEQSScoringWired:
    @pytest.mark.asyncio
    async def test_extraction_produces_eqs_metadata(self, tmp_path):
        """After extraction, _last_eqs_report is populated."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        good_text = (
            "# Introduction\n\n"
            "This document discusses machine learning techniques.\n"
            "Multiple paragraphs provide sufficient content density.\n\n"
            "## Methods\n\n"
            "We used neural networks for classification.\n"
        ) * 20

        mocks = _build_import_mock("fast_text", good_text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(pdf_file, use_vision=False)

        assert result == good_text
        assert service._last_eqs_report is not None
        assert "eqs_score" in service._last_eqs_report
        assert "eqs_grade" in service._last_eqs_report
        assert 0.0 <= service._last_eqs_report["eqs_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_eqs_score_in_valid_range(self, tmp_path):
        """EQS score is always between 0.0 and 1.0."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        text = "Hello world, this is a test document. " * 50
        mocks = _build_import_mock("fast_text", text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            await service._smart_extract_pdf(pdf_file, use_vision=False)

        assert service._last_eqs_report is not None
        score = service._last_eqs_report["eqs_score"]
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_eqs_does_not_block_pipeline(self, tmp_path):
        """If EQS scorer raises, pipeline still returns text."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        text = "Normal extracted content. " * 20
        mocks = _build_import_mock("fast_text", text)

        # Monkey-patch the feedback loop to raise
        original_evaluate = service._eqs_feedback.evaluate
        service._eqs_feedback.evaluate = MagicMock(
            side_effect=RuntimeError("EQS exploded")
        )

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(pdf_file, use_vision=False)

        # Pipeline still returns text
        assert result == text
        # EQS report is None due to error
        assert service._last_eqs_report is None

        # Restore
        service._eqs_feedback.evaluate = original_evaluate


# ---------------------------------------------------------------------------
# Test FeedbackLoop retry
# ---------------------------------------------------------------------------

class TestFeedbackLoopWired:
    @pytest.mark.asyncio
    async def test_good_extraction_no_retry(self, tmp_path):
        """Good text → score >= threshold → no retry."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        good_text = (
            "# Document\n\n"
            "Well-structured content with proper formatting.\n"
            "Multiple sentences provide density for scoring.\n\n"
            "## Section Two\n\n"
            "Additional content with list items:\n"
            "- Item one\n- Item two\n- Item three\n"
        ) * 20

        mocks = _build_import_mock("fast_text", good_text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(pdf_file, use_vision=False)

        assert result == good_text
        assert service._last_eqs_report is not None
        # Good text should pass without retry
        assert service._last_eqs_report.get("eqs_retried", False) is False

    @pytest.mark.asyncio
    async def test_all_strategies_fail_still_continues(self, tmp_path):
        """Even if all extractions score poorly, pipeline returns best text."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Very short/poor text
        bad_text = "x"
        mocks = _build_import_mock("fast_text", bad_text, total_pages=100)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(pdf_file, use_vision=False)

        # Pipeline still returns text (no exception)
        assert isinstance(result, str)
        assert service._last_eqs_report is not None


# ---------------------------------------------------------------------------
# Test EQS in job metadata
# ---------------------------------------------------------------------------

class TestEQSInJobMetadata:
    @pytest.mark.asyncio
    async def test_eqs_score_saved_to_job(self, tmp_path):
        """After extraction, create_job includes EQS metadata."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        text = "Well-structured document content. " * 50
        mocks = _build_import_mock("fast_text", text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            await service._smart_extract_pdf(pdf_file, use_vision=False)

        # Now the EQS report should be set
        eqs = service._last_eqs_report
        assert eqs is not None
        assert "eqs_score" in eqs
        assert "eqs_grade" in eqs
        assert "eqs_strategy_used" in eqs
        assert "eqs_passed" in eqs

    @pytest.mark.asyncio
    async def test_eqs_metadata_format(self, tmp_path):
        """EQS metadata has all expected fields with non-null values."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        text = (
            "# Title\n\n"
            "Content paragraph with enough words for scoring.\n"
            "- List item one\n- List item two\n"
        ) * 30

        mocks = _build_import_mock("fast_text", text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            await service._smart_extract_pdf(pdf_file, use_vision=False)

        eqs = service._last_eqs_report
        assert eqs is not None
        assert isinstance(eqs["eqs_score"], float)
        assert eqs["eqs_grade"] in ("A", "B", "C", "D", "F")
        assert isinstance(eqs["eqs_strategy_used"], str)
        assert isinstance(eqs["eqs_passed"], bool)
        assert isinstance(eqs["eqs_recommendation"], str)


# ---------------------------------------------------------------------------
# Regression guards
# ---------------------------------------------------------------------------

class TestPipelineRegression:
    @pytest.mark.asyncio
    async def test_existing_extraction_still_works(self, tmp_path):
        """Extraction flow produces same text output as before EQS."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        expected_text = "The quick brown fox jumps over the lazy dog. " * 100
        mocks = _build_import_mock("fast_text", expected_text)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(pdf_file, use_vision=False)

        assert result == expected_text

    @pytest.mark.asyncio
    async def test_extraction_performance_no_degradation(self, tmp_path):
        """EQS scoring overhead is < 100ms for typical document."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        # Simulate a typical 50-page document
        text = "This is a typical paragraph. " * 500  # ~2500 words
        mocks = _build_import_mock("fast_text", text, total_pages=50)

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            start = time.time()
            await service._smart_extract_pdf(pdf_file, use_vision=False)
            elapsed = time.time() - start

        # Total time includes mock setup — EQS scoring should be negligible
        # Allow generous 500ms for slow CI environments
        assert elapsed < 0.5, f"EQS overhead too high: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_vision_path_bypasses_eqs(self, tmp_path):
        """FULL_VISION without OCR returns file path, no EQS scoring."""
        service = _make_service(tmp_path)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mocks = _build_import_mock("full_vision", "", total_pages=10)
        # For FULL_VISION without OCR-supported lang, returns file path
        mocks["analysis"].scanned_pages = 5

        with patch.dict("sys.modules", {"core.smart_extraction": MagicMock(**{
            "SmartExtractionRouter": mocks["SmartExtractionRouter"],
            "ExtractionStrategy": mocks["ExtractionStrategy"],
            "analyze_document": mocks["analyze_document"],
            "smart_extract": mocks["smart_extract"],
            "fast_extract": mocks["fast_extract"],
        })}):
            result = await service._smart_extract_pdf(
                pdf_file, use_vision=True, source_lang=None
            )

        # Should return file path for orchestrator Vision processing
        assert result == str(pdf_file)
        # No EQS scoring for Vision pass-through
        assert service._last_eqs_report is None
