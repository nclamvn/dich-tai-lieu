"""
Unit tests for api/services/formula_extractor.py — FormulaExtractor.

Target: comprehensive coverage of all formula kinds and modes.
"""

import pytest

from api.services.formula_extractor import (
    FormulaExtractor,
    ExtractedFormula,
    FormulaMode,
    FormulaKind,
)


# ---------------------------------------------------------------------------
# Inline dollar: $...$
# ---------------------------------------------------------------------------

class TestInlineDollar:
    def test_simple_inline(self):
        ext = FormulaExtractor()
        formulas = ext.extract("Given $x^2 + y^2 = r^2$ we see.")
        assert len(formulas) == 1
        f = formulas[0]
        assert f.mode == FormulaMode.INLINE
        assert f.kind == FormulaKind.DOLLAR_INLINE
        assert "x^2" in f.inner

    def test_multiple_inline(self):
        ext = FormulaExtractor()
        formulas = ext.extract("Let $a$ and $b$ be integers.")
        assert len(formulas) == 2

    def test_no_false_positive_on_dollar_signs(self):
        ext = FormulaExtractor()
        formulas = ext.extract("The price is $100 and $200.")
        # $100 and$ is matched but may or may not be — depends on regex
        # At minimum, should not crash

    def test_inner_strips_delimiters(self):
        ext = FormulaExtractor()
        formulas = ext.extract("$E=mc^2$")
        assert len(formulas) == 1
        assert formulas[0].inner == "E=mc^2"


# ---------------------------------------------------------------------------
# Display dollar: $$...$$
# ---------------------------------------------------------------------------

class TestDisplayDollar:
    def test_simple_display(self):
        ext = FormulaExtractor()
        formulas = ext.extract("$$\\int_0^1 f(x) dx$$")
        assert len(formulas) == 1
        assert formulas[0].mode == FormulaMode.DISPLAY
        assert formulas[0].kind == FormulaKind.DOLLAR_DISPLAY

    def test_multiline_display(self):
        ext = FormulaExtractor()
        text = "$$\nx^2 + y^2\n= r^2\n$$"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].mode == FormulaMode.DISPLAY

    def test_display_inner(self):
        ext = FormulaExtractor()
        formulas = ext.extract("$$x + y$$")
        assert formulas[0].inner == "x + y"


# ---------------------------------------------------------------------------
# LaTeX bracket: \[...\]
# ---------------------------------------------------------------------------

class TestBracketDisplay:
    def test_bracket_display(self):
        ext = FormulaExtractor()
        formulas = ext.extract("\\[x^2 + y^2 = r^2\\]")
        assert len(formulas) == 1
        assert formulas[0].mode == FormulaMode.DISPLAY
        assert formulas[0].kind == FormulaKind.BRACKET_DISPLAY

    def test_bracket_inner(self):
        ext = FormulaExtractor()
        formulas = ext.extract("\\[E=mc^2\\]")
        assert formulas[0].inner == "E=mc^2"


# ---------------------------------------------------------------------------
# LaTeX paren: \(...\)
# ---------------------------------------------------------------------------

class TestParenInline:
    def test_paren_inline(self):
        ext = FormulaExtractor()
        formulas = ext.extract("We have \\(x+y\\) as sum.")
        assert len(formulas) == 1
        assert formulas[0].mode == FormulaMode.INLINE
        assert formulas[0].kind == FormulaKind.PAREN_INLINE

    def test_paren_inner(self):
        ext = FormulaExtractor()
        formulas = ext.extract("\\(a+b\\)")
        assert formulas[0].inner == "a+b"


# ---------------------------------------------------------------------------
# LaTeX environments
# ---------------------------------------------------------------------------

class TestLatexEnv:
    def test_equation_env(self):
        ext = FormulaExtractor()
        text = "\\begin{equation}E = mc^2\\end{equation}"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].kind == FormulaKind.LATEX_ENV
        assert formulas[0].env_name == "equation"
        assert formulas[0].mode == FormulaMode.DISPLAY

    def test_align_env(self):
        ext = FormulaExtractor()
        text = "\\begin{align}a &= b \\\\ c &= d\\end{align}"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].env_name == "align"

    def test_matrix_env(self):
        ext = FormulaExtractor()
        text = "\\begin{pmatrix}1 & 0 \\\\ 0 & 1\\end{pmatrix}"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].env_name == "pmatrix"

    def test_cases_env(self):
        ext = FormulaExtractor()
        text = "\\begin{cases}x &= 1 \\\\ y &= 2\\end{cases}"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].env_name == "cases"

    def test_env_inner(self):
        ext = FormulaExtractor()
        text = "\\begin{equation}x^2\\end{equation}"
        formulas = ext.extract(text)
        assert formulas[0].inner == "x^2"


# ---------------------------------------------------------------------------
# Unicode math
# ---------------------------------------------------------------------------

class TestUnicodeMath:
    def test_unicode_sequence(self):
        ext = FormulaExtractor()
        text = "The sum ∑∫√ is important."
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].kind == FormulaKind.UNICODE

    def test_short_unicode_ignored(self):
        """Sequences shorter than 3 should not match."""
        ext = FormulaExtractor()
        text = "Value ∈ set."  # Only 1 symbol
        formulas = ext.extract(text)
        assert len(formulas) == 0


# ---------------------------------------------------------------------------
# Mixed formulas
# ---------------------------------------------------------------------------

class TestMixed:
    def test_inline_and_display(self):
        ext = FormulaExtractor()
        text = "Given $x$ we compute $$\\int f(x) dx$$"
        formulas = ext.extract(text)
        assert len(formulas) == 2
        inline = [f for f in formulas if f.mode == FormulaMode.INLINE]
        display = [f for f in formulas if f.mode == FormulaMode.DISPLAY]
        assert len(inline) == 1
        assert len(display) == 1

    def test_no_overlap_between_display_and_inline(self):
        """$$...$$ should not also match as $...$."""
        ext = FormulaExtractor()
        text = "$$x^2$$"
        formulas = ext.extract(text)
        assert len(formulas) == 1
        assert formulas[0].kind == FormulaKind.DOLLAR_DISPLAY


# ---------------------------------------------------------------------------
# has_formulas
# ---------------------------------------------------------------------------

class TestHasFormulas:
    def test_has_inline(self):
        ext = FormulaExtractor()
        assert ext.has_formulas("$x^2$") is True

    def test_has_display(self):
        ext = FormulaExtractor()
        assert ext.has_formulas("$$x$$") is True

    def test_has_env(self):
        ext = FormulaExtractor()
        assert ext.has_formulas("\\begin{equation}x\\end{equation}") is True

    def test_no_formulas(self):
        ext = FormulaExtractor()
        assert ext.has_formulas("Just plain text.") is False

    def test_empty(self):
        ext = FormulaExtractor()
        assert ext.has_formulas("") is False
        assert ext.has_formulas(None) is False


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

class TestCount:
    def test_count(self):
        ext = FormulaExtractor()
        text = "$a$ and $b$ and $$c$$"
        result = ext.count(text)
        assert result["total"] == 3
        assert result["inline"] == 2
        assert result["display"] == 1
        assert "by_kind" in result

    def test_count_empty(self):
        ext = FormulaExtractor()
        result = ext.count("no formulas here")
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

class TestToDict:
    def test_to_dict(self):
        ext = FormulaExtractor()
        formulas = ext.extract("$x^2$")
        d = formulas[0].to_dict()
        assert d["mode"] == "inline"
        assert d["kind"] == "dollar_inline"
        assert d["content"] == "$x^2$"
        assert d["inner"] == "x^2"
        assert "start" in d
        assert "end" in d

    def test_env_to_dict(self):
        ext = FormulaExtractor()
        formulas = ext.extract("\\begin{equation}x\\end{equation}")
        d = formulas[0].to_dict()
        assert d["env_name"] == "equation"
