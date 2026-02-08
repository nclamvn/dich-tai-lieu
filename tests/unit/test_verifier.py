"""Tests for core_v2/verifier.py — QualityVerifier, VerificationResult, quick_verify."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from core_v2.verifier import (
    QualityLevel,
    QualityVerifier,
    VerificationResult,
    quick_verify,
)


# ==================== QualityLevel Enum ====================


class TestQualityLevel:
    """QualityLevel enum values."""

    def test_all_levels(self):
        expected = {"excellent", "good", "acceptable", "needs_revision", "poor"}
        actual = {ql.value for ql in QualityLevel}
        assert expected == actual


# ==================== VerificationResult ====================


class TestVerificationResult:
    """VerificationResult dataclass and to_dict."""

    def test_defaults(self):
        vr = VerificationResult(overall_quality=QualityLevel.GOOD, score=0.8)
        assert vr.accuracy == 0.0
        assert vr.fluency == 0.0
        assert vr.issues == []
        assert vr.suggestions == []

    def test_to_dict(self):
        vr = VerificationResult(
            overall_quality=QualityLevel.EXCELLENT,
            score=0.95,
            accuracy=0.9,
            fluency=0.95,
            issues=["minor issue"],
            suggestions=["improve something"],
        )
        d = vr.to_dict()
        assert d["overall_quality"] == "excellent"
        assert d["score"] == 0.95
        assert d["dimensions"]["accuracy"] == 0.9
        assert "minor issue" in d["issues"]

    def test_to_dict_dimensions(self):
        vr = VerificationResult(
            overall_quality=QualityLevel.GOOD, score=0.8,
            accuracy=0.85, fluency=0.9, style_match=0.7,
            terminology=0.8, formatting=0.75,
        )
        dims = vr.to_dict()["dimensions"]
        assert set(dims.keys()) == {"accuracy", "fluency", "style_match", "terminology", "formatting"}


# ==================== quick_verify ====================


class TestQuickVerify:
    """quick_verify() sanity checks."""

    def test_valid_translation(self):
        assert quick_verify("Hello world", "Xin chào thế giới") is True

    def test_empty_translation_fails(self):
        assert quick_verify("Hello", "") is False

    def test_whitespace_only_fails(self):
        assert quick_verify("Hello", "   ") is False

    def test_identical_long_text_fails(self):
        text = "This is a long enough text that should not be identical. " * 5
        assert quick_verify(text, text) is False

    def test_identical_short_text_passes(self):
        # Short identical text is OK (e.g., numbers, proper nouns)
        assert quick_verify("OK", "OK") is True

    def test_very_short_translation_fails(self):
        source = "This is a reasonably long paragraph with many words."
        translation = "X"
        assert quick_verify(source, translation) is False

    def test_very_long_translation_fails(self):
        source = "Short."
        translation = "Extremely long " * 100
        assert quick_verify(source, translation) is False

    def test_reasonable_ratio_passes(self):
        source = "Hello world, this is a test sentence."
        translation = "Xin chào thế giới, đây là một câu thử nghiệm."
        assert quick_verify(source, translation) is True

    def test_empty_source_with_translation(self):
        # ratio = len(translated) / max(0, 1) → could be high
        assert quick_verify("", "Some translation") is False

    def test_both_empty(self):
        assert quick_verify("", "") is False


# ==================== QualityVerifier._select_sample_indices ====================


class TestSelectSampleIndices:
    """Sample index selection logic."""

    def _make_verifier(self):
        return QualityVerifier(llm_client=AsyncMock())

    def test_small_total_returns_all(self):
        v = self._make_verifier()
        indices = v._select_sample_indices(total=3, sample_size=5)
        assert indices == [0, 1, 2]

    def test_includes_first_and_last(self):
        v = self._make_verifier()
        indices = v._select_sample_indices(total=20, sample_size=4)
        assert 0 in indices
        assert 19 in indices

    def test_sample_size_respected(self):
        v = self._make_verifier()
        indices = v._select_sample_indices(total=100, sample_size=5)
        assert len(indices) <= 5

    def test_single_element(self):
        v = self._make_verifier()
        indices = v._select_sample_indices(total=1, sample_size=1)
        assert indices == [0]


# ==================== QualityVerifier._aggregate_results ====================


class TestAggregateResults:
    """Result aggregation logic."""

    def _make_verifier(self):
        return QualityVerifier(llm_client=AsyncMock())

    def test_empty_results(self):
        v = self._make_verifier()
        result = v._aggregate_results([], 0, 10)
        assert result.overall_quality == QualityLevel.ACCEPTABLE
        assert result.score == 0.5

    def test_excellent_scores(self):
        v = self._make_verifier()
        results = [{
            "accuracy": 0.95, "fluency": 0.95, "style_match": 0.95,
            "terminology": 0.95, "formatting": 0.95,
            "issues": [], "suggestions": [],
        }]
        result = v._aggregate_results(results, 1, 1)
        assert result.overall_quality == QualityLevel.EXCELLENT
        assert result.score >= 0.9

    def test_poor_scores(self):
        v = self._make_verifier()
        results = [{
            "accuracy": 0.1, "fluency": 0.1, "style_match": 0.1,
            "terminology": 0.1, "formatting": 0.1,
            "issues": ["bad"], "suggestions": ["fix"],
        }]
        result = v._aggregate_results(results, 1, 1)
        assert result.overall_quality == QualityLevel.POOR
        assert result.score < 0.4

    def test_issues_collected(self):
        v = self._make_verifier()
        results = [
            {"accuracy": 0.7, "fluency": 0.7, "style_match": 0.7,
             "terminology": 0.7, "formatting": 0.7,
             "issues": ["issue A"], "suggestions": ["fix A"]},
            {"accuracy": 0.7, "fluency": 0.7, "style_match": 0.7,
             "terminology": 0.7, "formatting": 0.7,
             "issues": ["issue B"], "suggestions": ["fix B"]},
        ]
        result = v._aggregate_results(results, 2, 5)
        assert "issue A" in result.issues
        assert "issue B" in result.issues
        assert result.verified_chunks == 2
        assert result.total_chunks == 5

    def test_quality_levels_thresholds(self):
        v = self._make_verifier()

        def make_result(score):
            return [{
                "accuracy": score, "fluency": score, "style_match": score,
                "terminology": score, "formatting": score,
                "issues": [], "suggestions": [],
            }]

        assert v._aggregate_results(make_result(0.95), 1, 1).overall_quality == QualityLevel.EXCELLENT
        assert v._aggregate_results(make_result(0.80), 1, 1).overall_quality == QualityLevel.GOOD
        assert v._aggregate_results(make_result(0.65), 1, 1).overall_quality == QualityLevel.ACCEPTABLE
        assert v._aggregate_results(make_result(0.45), 1, 1).overall_quality == QualityLevel.NEEDS_REVISION
        assert v._aggregate_results(make_result(0.20), 1, 1).overall_quality == QualityLevel.POOR


# ==================== QualityVerifier.verify (async) ====================


class TestVerifyAsync:
    """Full verify flow with mocked LLM."""

    @pytest.mark.asyncio
    async def test_chunk_mismatch(self):
        mock_client = AsyncMock()
        v = QualityVerifier(llm_client=mock_client)
        result = await v.verify(
            source_chunks=["a", "b"],
            translated_chunks=["x"],
            source_lang="en",
            target_lang="vi",
        )
        assert result.overall_quality == QualityLevel.POOR
        assert result.score == 0.0
        assert "mismatch" in result.issues[0].lower()

    @pytest.mark.asyncio
    async def test_successful_verification(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "accuracy": 0.9, "fluency": 0.85, "style_match": 0.8,
            "terminology": 0.9, "formatting": 0.85,
            "issues": [], "suggestions": [],
        })
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        v = QualityVerifier(llm_client=mock_client, sample_rate=1.0)
        result = await v.verify(
            source_chunks=["Hello world"],
            translated_chunks=["Xin chào thế giới"],
            source_lang="en",
            target_lang="vi",
        )
        assert result.score > 0.8
        assert result.overall_quality in (QualityLevel.EXCELLENT, QualityLevel.GOOD)

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self):
        mock_client = AsyncMock()
        mock_client.chat.side_effect = RuntimeError("LLM error")

        v = QualityVerifier(llm_client=mock_client, sample_rate=1.0)
        result = await v.verify(
            source_chunks=["test"],
            translated_chunks=["thử"],
            source_lang="en",
            target_lang="vi",
        )
        # Should still return a result, not raise
        assert isinstance(result, VerificationResult)
        assert result.score > 0
