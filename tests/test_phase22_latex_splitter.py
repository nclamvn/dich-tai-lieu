"""
Phase 2.2.0 - LaTeX Equation Splitter Unit Tests

Tests the high-confidence LaTeX equation splitter that extracts
individual equations from compound LaTeX blocks.
"""

import pytest
from core.latex.eq_splitter import (
    split_latex_equations,
    SplitEquationResult,
    get_splitter_statistics,
)


class TestSingleCleanEquation:
    """Test Case 1: Single clean equation without delimiters or text"""

    def test_clean_equation_no_delimiters(self):
        """Single clean LaTeX equation should be extracted confidently"""
        latex = r"\sup_{n,d\in\mathbb{N}} \left\| \sum_{j=1}^n f(jd) \right\|_H"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert result.equation_segments[0] == latex.strip()
        assert result.reason is None

    def test_clean_fraction_equation(self):
        """Clean fraction equation should be extracted"""
        latex = r"\frac{d}{dx} \int_0^x f(t) dt = f(x)"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert latex.strip() in result.equation_segments[0]


class TestDisplayMathDelimiters:
    """Test Case 2: Equations with display math delimiters"""

    def test_double_dollar_delimiters(self):
        """Display math with $$ delimiters should extract inner content"""
        latex = r"$$ x^2 + y^2 = z^2 $$"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert "x^2 + y^2 = z^2" == result.equation_segments[0]
        assert "$$" not in result.equation_segments[0]  # Delimiters stripped

    def test_bracket_delimiters(self):
        """Display math with \\[...\\] delimiters should extract inner content"""
        latex = r"\[ E = mc^2 \]"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert "E = mc^2" == result.equation_segments[0]
        assert r"\[" not in result.equation_segments[0]
        assert r"\]" not in result.equation_segments[0]

    def test_display_with_whitespace(self):
        """Display math with extra whitespace should be trimmed"""
        latex = r"$$   \int_0^\infty e^{-x} dx = 1   $$"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        # Check trimmed content
        assert result.equation_segments[0].startswith(r"\int")
        assert not result.equation_segments[0].startswith(" ")


class TestEnvironmentBlocks:
    """Test Case 3: LaTeX environment blocks"""

    def test_equation_environment(self):
        """\\begin{equation} environment should be extracted as full block"""
        latex = r"\begin{equation} x^2 + y^2 = z^2 \end{equation}"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert latex == result.equation_segments[0]  # Full block preserved

    def test_align_environment(self):
        """\\begin{align} environment should be extracted"""
        latex = r"\begin{align} S_n &= \sum_{j=1}^n f(jd) \\ T_n &= \sum_{j=1}^n g(jd) \end{align}"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1
        assert r"\begin{align}" in result.equation_segments[0]

    def test_starred_environment(self):
        """Starred environment (equation*) should be extracted"""
        latex = r"\begin{equation*} \lim_{n \to \infty} \frac{1}{n} = 0 \end{equation*}"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1

    def test_gather_environment(self):
        """\\begin{gather} environment should be extracted"""
        latex = r"\begin{gather} a = b + c \\ d = e + f \end{gather}"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1


class TestMixedTextInlineMath:
    """Test Case 4: Mixed text with inline math (should NOT be confident)"""

    def test_text_with_single_inline_math(self):
        """Text with inline math should not be confident"""
        latex = r"Given a sequence $f\colon \mathbb{N} \to H$ taking values in $H$."

        result = split_latex_equations(latex)

        assert result.is_confident is False
        assert "inline math with surrounding text" in result.reason.lower() or \
               "inline" in result.reason.lower()

    def test_text_with_multiple_inline_math(self):
        """Multiple inline math with text should not be confident"""
        latex = r"For all $x \in X$ and $y \in Y$, we have $f(x) = g(y)$."

        result = split_latex_equations(latex)

        assert result.is_confident is False

    def test_inline_only_no_text(self):
        """Inline math without text should not be confident (low priority for OMML)"""
        latex = r"$\alpha + \beta = \gamma$"

        result = split_latex_equations(latex)

        # Phase 2.2.0: inline-only is not confident (low priority)
        assert result.is_confident is False


class TestMixedTextDisplayMath:
    """Test Case 5 (Optional): Mixed text with clean display math"""

    def test_text_display_text_pattern(self):
        """Text before/after display math - conservative approach"""
        latex = r"Consider the equation $$ x^2 = 1 $$ which has two solutions."

        result = split_latex_equations(latex)

        # Phase 2.2.0 conservative: may or may not extract
        # If extracted, should be confident about the display part
        if result.is_confident:
            assert len(result.equation_segments) > 0
            # The display equation should be extracted
            assert any("x^2 = 1" in seg for seg in result.equation_segments)


class TestInvalidEmptyInput:
    """Test Case 6: Invalid or empty input"""

    def test_empty_string(self):
        """Empty string should not be confident"""
        result = split_latex_equations("")

        assert result.is_confident is False
        assert "empty" in result.reason.lower()

    def test_whitespace_only(self):
        """Whitespace-only should not be confident"""
        result = split_latex_equations("   \n\t  ")

        assert result.is_confident is False

    def test_plain_text_no_math(self):
        """Plain text without LaTeX should not be confident"""
        latex = "This is just plain text with no equations."

        result = split_latex_equations(latex)

        assert result.is_confident is False

    def test_none_input_handled(self):
        """None input should not crash (defensive)"""
        # This tests that the function doesn't crash on unexpected input
        # Though the type hints say str, defensive programming is good
        try:
            result = split_latex_equations(None)
            # Should either handle gracefully or raise TypeError
            assert not result.is_confident
        except (TypeError, AttributeError):
            # Expected behavior - type error on None
            pass


class TestComplexRealWorldCases:
    """Real-world complex cases from arXiv papers"""

    def test_complex_display_equation(self):
        """Complex display equation from real arXiv paper"""
        latex = r"$$ \sup_{n,d \in \mathbb{N}} \left\| \sum_{j=1}^n f(jd) \right\|_H < \infty $$"

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1

    def test_multiline_align_star(self):
        """Multi-line align* environment"""
        latex = r"""\begin{align*}
        \mathbb{E}[X_n] &= \int_0^1 x^n dx \\
        &= \frac{1}{n+1}
        \end{align*}"""

        result = split_latex_equations(latex)

        assert result.is_confident is True
        assert len(result.equation_segments) == 1


class TestSplitterStatistics:
    """Test the statistics utility function"""

    def test_statistics_empty_list(self):
        """Statistics on empty list should return zeros"""
        stats = get_splitter_statistics([])

        assert stats['total'] == 0
        assert stats['confident'] == 0
        assert stats['confident_rate'] == 0.0

    def test_statistics_mixed_results(self):
        """Statistics on mixed confident/not confident results"""
        results = [
            split_latex_equations(r"$$ x = 1 $$"),  # Confident
            split_latex_equations(r"Given $x = 1$ in text"),  # Not confident
            split_latex_equations(r"\begin{equation} y = 2 \end{equation}"),  # Confident
        ]

        stats = get_splitter_statistics(results)

        assert stats['total'] == 3
        assert stats['confident'] == 2
        assert stats['confident_rate'] == pytest.approx(66.67, rel=0.1)


class TestEdgeCases:
    """Edge cases and defensive tests"""

    def test_nested_delimiters_rejected(self):
        """Nested $$ delimiters should not be confident"""
        latex = r"$$ x = $$ y $$"

        result = split_latex_equations(latex)

        # Should detect invalid nested structure
        assert result.is_confident is False

    def test_mismatched_environment(self):
        """Mismatched \\begin{} and \\end{} should not be confident"""
        latex = r"\begin{equation} x = 1 \end{align}"

        result = split_latex_equations(latex)

        # Should not match due to mismatch
        assert result.is_confident is False

    def test_escaped_dollar_signs(self):
        """Escaped \\$ should not be treated as delimiters"""
        latex = r"Price is \$10 and \$20"

        result = split_latex_equations(latex)

        # Should not detect math equations
        assert result.is_confident is False


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
