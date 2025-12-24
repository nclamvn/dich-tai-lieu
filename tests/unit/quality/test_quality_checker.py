"""
Unit tests for Quality Checker

Tests quality validation for translations including:
- Length ratio checks
- Placeholder consistency validation
- STEM preservation verification
"""

import pytest
from core.quality.quality_checker import (
    QualityReport,
    check_length_ratio,
    check_placeholder_consistency,
    check_stem_preservation,
    build_quality_report
)


class TestLengthRatioCheck:
    """Test length ratio checking"""

    def test_good_ratio(self):
        """Test translation with good length ratio"""
        source = "Hello world"
        translated = "Bonjour le monde"

        result = check_length_ratio(source, translated)

        assert result['ok'] is True
        assert 0.5 <= result['ratio'] <= 3.0

    def test_ratio_too_short(self):
        """Test translation that's too short"""
        source = "This is a long sentence with many words."
        translated = "Short"

        result = check_length_ratio(source, translated)

        assert result['ok'] is False
        assert result['ratio'] < 0.5

    def test_ratio_too_long(self):
        """Test translation that's too long"""
        source = "Hi"
        translated = "This is an extremely long translation that far exceeds the reasonable length for such a short source text."

        result = check_length_ratio(source, translated)

        assert result['ok'] is False
        assert result['ratio'] > 3.0

    def test_custom_thresholds(self):
        """Test with custom min/max ratio thresholds"""
        source = "Hello world"
        translated = "Bonjour monde"

        # Reasonable thresholds (ratio ~1.18)
        result = check_length_ratio(source, translated, min_ratio=0.8, max_ratio=1.5)
        assert result['ok'] is True

        # Very loose thresholds
        result = check_length_ratio(source, translated, min_ratio=0.1, max_ratio=10.0)
        assert result['ok'] is True

    def test_empty_source(self):
        """Test with empty source text"""
        source = ""
        translated = ""

        result = check_length_ratio(source, translated)

        assert result['ok'] is True

    def test_empty_source_non_empty_translation(self):
        """Test with empty source but non-empty translation"""
        source = ""
        translated = "Something"

        result = check_length_ratio(source, translated)

        assert result['ok'] is False


class TestPlaceholderConsistency:
    """Test placeholder consistency checking"""

    def test_perfect_consistency(self):
        """Test with perfect placeholder consistency"""
        source = "The equation ⟪STEM_F0⟫ is important."
        translated = "L'équation ⟪STEM_F0⟫ est importante."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is True
        assert len(result['missing']) == 0
        assert len(result['extra']) == 0

    def test_multiple_placeholders_consistent(self):
        """Test multiple placeholders all preserved"""
        source = "Both ⟪STEM_F0⟫ and ⟪STEM_F1⟫ and ⟪STEM_C0⟫ are important."
        translated = "Both ⟪STEM_F0⟫ and ⟪STEM_F1⟫ and ⟪STEM_C0⟫ are important."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is True
        assert len(result['missing']) == 0
        assert len(result['extra']) == 0

    def test_missing_placeholder(self):
        """Test with missing placeholder in translation"""
        source = "Equations ⟪STEM_F0⟫ and ⟪STEM_F1⟫ are key."
        translated = "Equations ⟪STEM_F0⟫ are key."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is False
        assert '⟪STEM_F1⟫' in result['missing']
        assert len(result['extra']) == 0

    def test_extra_placeholder(self):
        """Test with extra placeholder in translation"""
        source = "The equation ⟪STEM_F0⟫ is important."
        translated = "The equations ⟪STEM_F0⟫ and ⟪STEM_F1⟫ are important."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is False
        assert '⟪STEM_F1⟫' in result['extra']
        assert len(result['missing']) == 0

    def test_no_placeholders(self):
        """Test with no placeholders"""
        source = "This is plain text."
        translated = "Ceci est du texte brut."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is True
        assert len(result['missing']) == 0
        assert len(result['extra']) == 0

    def test_code_placeholders(self):
        """Test with code placeholders"""
        source = "Use ⟪STEM_C0⟫ function."
        translated = "Utiliser ⟪STEM_C0⟫ fonction."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is True

    def test_table_placeholders(self):
        """Test with table placeholders"""
        source = "See ⟪STEM_T0⟫ for data."
        translated = "Voir ⟪STEM_T0⟫ pour les données."

        result = check_placeholder_consistency(source, translated)

        assert result['ok'] is True


class TestSTEMPreservation:
    """Test STEM preservation checking"""

    def test_no_stem_content(self):
        """Test text with no STEM content"""
        original = "This is plain text."
        translated = "Ceci est du texte brut."

        result = check_stem_preservation(original, translated)

        assert result['ok'] is True
        assert len(result['warnings']) == 0

    def test_formula_properly_protected(self):
        """Test formula that was properly protected"""
        original = "The equation $E = mc^2$ is famous."
        translated = "L'équation ⟪STEM_F0⟫ est célèbre."

        result = check_stem_preservation(original, translated)

        assert result['ok'] is True
        assert len(result['warnings']) == 0

    def test_unprotected_formula_warning(self):
        """Test unprotected formula in translation"""
        original = "The equation $E = mc^2$ is famous."
        translated = "L'équation $E = mc^2$ est célèbre."

        result = check_stem_preservation(original, translated)

        assert result['ok'] is False
        assert len(result['warnings']) > 0
        assert any("Unprotected formula" in w for w in result['warnings'])

    def test_code_properly_protected(self):
        """Test code that was properly protected"""
        original = "```python\nprint('hello')\n```"
        translated = "⟪STEM_C0⟫"

        result = check_stem_preservation(original, translated)

        assert result['ok'] is True

    def test_unprotected_code_warning(self):
        """Test unprotected code in translation"""
        original = "```python\nprint('hello')\n```"
        translated = "```python\nprint('hello')\n```"

        result = check_stem_preservation(original, translated)

        # Should warn about unprotected code
        assert result['ok'] is False
        assert len(result['warnings']) > 0


class TestBuildQualityReport:
    """Test building comprehensive quality reports"""

    def test_perfect_translation(self):
        """Test perfect translation with all checks passing"""
        source = "The equation ⟪STEM_F0⟫ is important."
        translated = "L'équation ⟪STEM_F0⟫ est importante."

        report = build_quality_report(source, translated)

        assert report.overall_pass is True
        assert report.length_ratio_ok is True
        assert report.placeholder_consistency_ok is True
        assert report.stem_preservation_ok is True
        assert len(report.warnings) == 0

    def test_length_ratio_failure(self):
        """Test translation with bad length ratio"""
        source = "Hello"
        translated = "This is an extremely long translation that's clearly wrong"

        report = build_quality_report(source, translated)

        assert report.overall_pass is False
        assert report.length_ratio_ok is False
        assert len(report.warnings) > 0
        assert any("Length ratio" in w for w in report.warnings)

    def test_missing_placeholder_failure(self):
        """Test translation with missing placeholder"""
        source = "Equations ⟪STEM_F0⟫ and ⟪STEM_F1⟫."
        translated = "Equations ⟪STEM_F0⟫."

        report = build_quality_report(source, translated)

        assert report.overall_pass is False
        assert report.placeholder_consistency_ok is False
        assert len(report.missing_placeholders) > 0
        assert '⟪STEM_F1⟫' in report.missing_placeholders

    def test_extra_placeholder_failure(self):
        """Test translation with extra placeholder"""
        source = "Equation ⟪STEM_F0⟫."
        translated = "Equations ⟪STEM_F0⟫ and ⟪STEM_F1⟫."

        report = build_quality_report(source, translated)

        assert report.overall_pass is False
        assert report.placeholder_consistency_ok is False
        assert len(report.extra_placeholders) > 0
        assert '⟪STEM_F1⟫' in report.extra_placeholders

    def test_stem_preservation_with_original(self):
        """Test STEM preservation check with original source"""
        original = "The equation $E = mc^2$ is famous."
        source_with_placeholder = "The equation ⟪STEM_F0⟫ is famous."
        translated_good = "L'équation ⟪STEM_F0⟫ est célèbre."
        translated_bad = "L'équation $E = mc^2$ est célèbre."

        # Good translation
        report_good = build_quality_report(
            source_with_placeholder,
            translated_good,
            original_source=original
        )
        assert report_good.stem_preservation_ok is True

        # Bad translation (unprotected formula)
        report_bad = build_quality_report(
            source_with_placeholder,
            translated_bad,
            original_source=original
        )
        assert report_bad.stem_preservation_ok is False

    def test_multiple_failures(self):
        """Test translation with multiple issues"""
        source = "Equation ⟪STEM_F0⟫."
        translated = "This is way too long and also missing ⟪STEM_F1⟫ placeholder oops."

        report = build_quality_report(source, translated)

        assert report.overall_pass is False
        assert len(report.warnings) >= 2

    def test_custom_thresholds(self):
        """Test with custom length ratio thresholds"""
        source = "Hello world"
        translated = "Bonjour monde"

        # Reasonable thresholds (ratio ~1.18)
        report = build_quality_report(source, translated, min_ratio=0.8, max_ratio=1.5)
        assert report.length_ratio_ok is True

        # Very strict thresholds (will fail)
        report = build_quality_report(source, translated, min_ratio=0.99, max_ratio=1.01)
        assert report.length_ratio_ok is False


class TestQualityReport:
    """Test QualityReport dataclass"""

    def test_report_repr(self):
        """Test QualityReport __repr__"""
        report = QualityReport(
            length_ratio=1.0,
            length_ratio_ok=True,
            overall_pass=True
        )

        repr_str = repr(report)
        assert "PASS" in repr_str
        assert "1.00" in repr_str

    def test_report_summary(self):
        """Test QualityReport summary method"""
        report = QualityReport(
            length_ratio=1.5,
            length_ratio_ok=True,
            placeholder_consistency_ok=True,
            stem_preservation_ok=True,
            overall_pass=True
        )

        summary = report.summary()
        assert "PASS" in summary
        assert "1.50" in summary

    def test_report_summary_with_warnings(self):
        """Test summary with warnings"""
        report = QualityReport(
            length_ratio=5.0,
            length_ratio_ok=False,
            missing_placeholders=['⟪STEM_F0⟫'],
            placeholder_consistency_ok=False,
            warnings=["Length ratio out of bounds", "Missing placeholder"],
            overall_pass=False
        )

        summary = report.summary()
        assert "FAIL" in summary
        assert "5.00" in summary
        assert "Missing" in summary


# Integration tests
class TestQualityCheckerIntegration:
    """Integration tests for quality checker"""

    def test_realistic_good_translation(self):
        """Test realistic good scientific translation"""
        source = """
        Einstein's equation ⟪STEM_F0⟫ relates energy to mass.
        The code ⟪STEM_C0⟫ demonstrates this principle.
        """

        translated = """
        L'équation d'Einstein ⟪STEM_F0⟫ relie l'énergie à la masse.
        Le code ⟪STEM_C0⟫ démontre ce principe.
        """

        report = build_quality_report(source, translated)

        assert report.overall_pass is True

    def test_realistic_bad_translation(self):
        """Test realistic bad translation with issues"""
        source = """
        The formula ⟪STEM_F0⟫ and ⟪STEM_F1⟫ are fundamental.
        """

        translated = """
        Wrong!
        """

        report = build_quality_report(source, translated)

        assert report.overall_pass is False
        # Should fail on both length ratio and missing placeholders
        assert not report.length_ratio_ok or not report.placeholder_consistency_ok


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
