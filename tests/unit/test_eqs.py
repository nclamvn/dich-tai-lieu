"""
Unit tests for api/services/eqs.py — Extraction Quality Scorer.

Target: 90%+ coverage of ExtractionQualityScorer and EQSReport.
"""
import pytest
from api.services.eqs import (
    ExtractionQualityScorer,
    EQSReport,
    SignalScore,
    DEFAULT_WEIGHTS,
)


# ---------------------------------------------------------------------------
# EQSReport dataclass
# ---------------------------------------------------------------------------

class TestEQSReport:
    def test_passed_above_threshold(self):
        report = EQSReport(overall_score=0.75, grade="B")
        assert report.passed is True

    def test_passed_at_threshold(self):
        report = EQSReport(overall_score=0.6, grade="C")
        assert report.passed is True

    def test_failed_below_threshold(self):
        report = EQSReport(overall_score=0.59, grade="D")
        assert report.passed is False

    def test_to_dict(self):
        sig = SignalScore(name="encoding", score=0.95, weight=0.2, details="ok")
        report = EQSReport(
            overall_score=0.85,
            grade="B",
            signals=[sig],
            recommendation="Good",
            metadata={"pages": 10},
        )
        d = report.to_dict()
        assert d["overall_score"] == 0.85
        assert d["grade"] == "B"
        assert d["passed"] is True
        assert len(d["signals"]) == 1
        assert d["signals"][0]["name"] == "encoding"
        assert d["recommendation"] == "Good"
        assert d["metadata"]["pages"] == 10

    def test_to_dict_empty_signals(self):
        report = EQSReport(overall_score=0.0, grade="F")
        d = report.to_dict()
        assert d["signals"] == []
        assert d["passed"] is False


# ---------------------------------------------------------------------------
# ExtractionQualityScorer — constructor
# ---------------------------------------------------------------------------

class TestScorerInit:
    def test_default_weights(self):
        scorer = ExtractionQualityScorer()
        assert scorer.weights == DEFAULT_WEIGHTS

    def test_custom_weights(self):
        w = {
            "text_density": 0.3,
            "structure": 0.1,
            "encoding": 0.2,
            "language": 0.2,
            "completeness": 0.1,
            "format_integrity": 0.1,
        }
        scorer = ExtractionQualityScorer(weights=w)
        assert scorer.weights["text_density"] == 0.3

    def test_bad_weights_raises(self):
        w = {
            "text_density": 0.5,
            "structure": 0.5,
            "encoding": 0.5,
            "language": 0.5,
            "completeness": 0.5,
            "format_integrity": 0.5,
        }
        with pytest.raises(ValueError, match="must sum to 1.0"):
            ExtractionQualityScorer(weights=w)


# ---------------------------------------------------------------------------
# ExtractionQualityScorer.score — integration-level
# ---------------------------------------------------------------------------

class TestScorerScore:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_empty_text(self):
        report = self.scorer.score("", total_pages=5)
        assert report.overall_score == 0.0
        assert report.grade == "F"
        assert "No text" in report.recommendation

    def test_whitespace_only(self):
        report = self.scorer.score("   \n\t  ", total_pages=1)
        assert report.overall_score == 0.0
        assert report.grade == "F"

    def test_good_english_text(self):
        text = (
            "# Introduction\n\n"
            "This is a well-structured document about machine learning.\n"
            "It contains multiple paragraphs with proper formatting.\n\n"
            "## Methods\n\n"
            "We used neural networks to classify images.\n"
            "- Convolutional layers\n"
            "- Batch normalisation\n"
            "- Dropout regularisation\n\n"
            "The results were statistically significant.\n"
        ) * 5  # repeat to get decent density
        report = self.scorer.score(text, total_pages=1, expected_language="en")
        assert report.overall_score >= 0.6
        assert report.grade in ("A", "B", "C")
        assert report.passed is True
        assert len(report.signals) == 6

    def test_garbage_text(self):
        text = "\ufffd" * 100 + "\x00" * 50
        report = self.scorer.score(text, total_pages=10)
        assert report.overall_score < 0.5
        assert report.passed is False

    def test_report_metadata(self):
        report = self.scorer.score("Hello world", total_pages=3, expected_language="en")
        assert report.metadata["total_pages"] == 3
        assert report.metadata["text_length"] == 11
        assert report.metadata["expected_language"] == "en"

    def test_signals_have_correct_names(self):
        report = self.scorer.score("Some text here", total_pages=1)
        signal_names = {s.name for s in report.signals}
        expected = {"text_density", "structure", "encoding", "language",
                    "completeness", "format_integrity"}
        assert signal_names == expected


# ---------------------------------------------------------------------------
# Individual signal scorers
# ---------------------------------------------------------------------------

class TestTextDensity:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_very_low_density(self):
        # 10 chars across 10 pages = 1 char/page
        sig = self.scorer._score_text_density("a" * 10, 10)
        assert sig.score < 0.1

    def test_ideal_density(self):
        # ~1500 chars/page
        sig = self.scorer._score_text_density("a" * 1500, 1)
        assert sig.score >= 0.9

    def test_high_density(self):
        # 3000 chars/page — still within range
        sig = self.scorer._score_text_density("a" * 3000, 1)
        assert sig.score >= 0.9

    def test_extreme_density(self):
        # 20000 chars/page — overshoot
        sig = self.scorer._score_text_density("a" * 20000, 1)
        assert sig.score >= 0.5
        assert sig.score < 1.0

    def test_zero_pages_handled(self):
        sig = self.scorer._score_text_density("some text", 0)
        assert sig.score >= 0.0


class TestStructure:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_markdown_headings(self):
        text = "# Title\n## Section\nSome paragraph text that is long enough to be detected.\n"
        sig = self.scorer._score_structure(text)
        assert sig.score > 0.5

    def test_list_items(self):
        text = "- Item one\n- Item two\n- Item three\n1. Numbered\n2. Also numbered\n"
        sig = self.scorer._score_structure(text)
        assert sig.score > 0.3

    def test_uppercase_heading(self):
        text = "CHAPTER ONE\nSome body text that follows the chapter heading nicely.\n"
        sig = self.scorer._score_structure(text)
        assert sig.score > 0.3

    def test_no_structure(self):
        text = "a\nb\nc\nd\n"
        sig = self.scorer._score_structure(text)
        assert sig.score < 0.5

    def test_empty_text(self):
        sig = self.scorer._score_structure("")
        assert sig.score == 0.0


class TestEncoding:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_clean_text(self):
        sig = self.scorer._score_encoding("Hello, this is clean English text.")
        assert sig.score >= 0.9

    def test_mojibake(self):
        text = "Ã©Ã¨Ã" * 20 + "normal text"
        sig = self.scorer._score_encoding(text)
        assert sig.score < 0.8

    def test_replacement_chars(self):
        text = "Hello \ufffd\ufffd\ufffd world"
        sig = self.scorer._score_encoding(text)
        assert sig.score < 1.0

    def test_null_bytes(self):
        text = "text\x00with\x00nulls"
        sig = self.scorer._score_encoding(text)
        assert sig.score < 1.0

    def test_empty_text(self):
        sig = self.scorer._score_encoding("")
        assert sig.score == 1.0


class TestLanguage:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_good_english(self):
        text = "This is a perfectly normal English sentence with multiple words."
        sig = self.scorer._score_language(text, "en")
        assert sig.score >= 0.7

    def test_too_few_words(self):
        sig = self.scorer._score_language("hi yo", None)
        assert sig.score == 0.3

    def test_cjk_boost(self):
        # CJK text needs enough whitespace-separated "words" to pass the 5-word minimum
        text = "日本語の テスト文 です。 これは 正常な テキスト です。 品質を 確認 します。"
        sig = self.scorer._score_language(text, "ja")
        assert sig.score >= 0.5

    def test_chinese_boost(self):
        text = "这是 一个 测试 文本 用于 检查 中文 提取 质量 评估"
        sig = self.scorer._score_language(text, "zh")
        assert sig.score >= 0.5

    def test_nonsense_tokens(self):
        text = "!@#$ %^&* ()_+ {}|: <>? " * 10
        sig = self.scorer._score_language(text, "en")
        assert sig.score < 0.7


class TestCompleteness:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_full_extraction(self):
        # 1000 chars for 5 pages (200 chars/page, well above 50 minimum)
        sig = self.scorer._score_completeness("x" * 1000, 5)
        assert sig.score == 1.0

    def test_partial_extraction(self):
        # 100 chars for 10 pages (10 chars/page, below 50 minimum)
        sig = self.scorer._score_completeness("x" * 100, 10)
        assert sig.score < 1.0
        assert sig.score > 0.0

    def test_empty_extraction(self):
        sig = self.scorer._score_completeness("", 5)
        assert sig.score == 0.0

    def test_zero_pages(self):
        # 0 pages is treated as 1, so need ≥50 chars for full score
        sig = self.scorer._score_completeness("x" * 60, 0)
        assert sig.score == 1.0


class TestFormatIntegrity:
    def setup_method(self):
        self.scorer = ExtractionQualityScorer()

    def test_no_markers_neutral(self):
        sig = self.scorer._score_format_integrity("Plain text without markers")
        assert sig.score == 0.7

    def test_valid_latex(self):
        text = "The formula is $E = mc^2$ and also $$\\int_0^1 f(x) dx$$"
        sig = self.scorer._score_format_integrity(text)
        assert sig.score >= 0.7

    def test_valid_markdown(self):
        text = "# Heading\n**Bold text** and [a link](http://example.com)"
        sig = self.scorer._score_format_integrity(text)
        assert sig.score >= 0.7

    def test_broken_dollar_signs(self):
        text = "$ broken $ more $ unmatched $$ also broken"
        sig = self.scorer._score_format_integrity(text)
        # Some broken markers
        assert sig.name == "format_integrity"


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

class TestGrading:
    def test_grade_a(self):
        assert ExtractionQualityScorer._grade(0.95) == "A"
        assert ExtractionQualityScorer._grade(0.90) == "A"

    def test_grade_b(self):
        assert ExtractionQualityScorer._grade(0.80) == "B"
        assert ExtractionQualityScorer._grade(0.75) == "B"

    def test_grade_c(self):
        assert ExtractionQualityScorer._grade(0.65) == "C"
        assert ExtractionQualityScorer._grade(0.60) == "C"

    def test_grade_d(self):
        assert ExtractionQualityScorer._grade(0.50) == "D"
        assert ExtractionQualityScorer._grade(0.40) == "D"

    def test_grade_f(self):
        assert ExtractionQualityScorer._grade(0.30) == "F"
        assert ExtractionQualityScorer._grade(0.0) == "F"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class TestRecommendation:
    def test_good_grade(self):
        rec = ExtractionQualityScorer._recommend("A", [])
        assert "good" in rec.lower()

    def test_bad_encoding_signal(self):
        signals = [
            SignalScore(name="encoding", score=0.1, weight=0.2),
            SignalScore(name="language", score=0.8, weight=0.2),
        ]
        rec = ExtractionQualityScorer._recommend("D", signals)
        assert "encoding" in rec.lower()

    def test_bad_density_signal(self):
        signals = [
            SignalScore(name="text_density", score=0.1, weight=0.25),
            SignalScore(name="encoding", score=0.9, weight=0.2),
        ]
        rec = ExtractionQualityScorer._recommend("D", signals)
        assert "density" in rec.lower()

    def test_no_signals(self):
        rec = ExtractionQualityScorer._recommend("F", [])
        assert "unable" in rec.lower()
