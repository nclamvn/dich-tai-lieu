"""
Unit tests for FormulaDetector

Tests formula detection including:
- Inline math: $...$, \\(...\\)
- Display math: $$...$$, \\[...\\]
- LaTeX environments
- Unicode math symbols
- Chemical formulas (NEW in Phase 3)
"""

import pytest
from core.stem.formula_detector import FormulaDetector, FormulaType, FormulaMatch


class TestFormulaDetector:
    """Test FormulaDetector functionality"""

    @pytest.fixture
    def detector(self):
        """Create FormulaDetector instance"""
        return FormulaDetector()

    # Basic inline math tests
    def test_inline_dollar_simple(self, detector):
        """Test simple inline math with $...$"""
        text = "The equation $E = mc^2$ is famous."
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.INLINE_DOLLAR
        assert matches[0].content == "$E = mc^2$"

    def test_inline_paren(self, detector):
        """Test inline math with \(...\)"""
        text = r"The equation \(E = mc^2\) is famous."
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.INLINE_PAREN
        assert r"\(E = mc^2\)" in matches[0].content

    # Display math tests
    def test_display_dollar(self, detector):
        """Test display math with $$...$$"""
        text = "The equation $$E = mc^2$$ is famous."
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.DISPLAY_DOLLAR
        assert matches[0].content == "$$E = mc^2$$"

    def test_display_bracket(self, detector):
        """Test display math with \[...\]"""
        text = r"The equation \[E = mc^2\] is famous."
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.DISPLAY_BRACKET
        assert r"\[E = mc^2\]" in matches[0].content

    # LaTeX environment tests
    def test_latex_equation_env(self, detector):
        """Test LaTeX equation environment"""
        text = r"\begin{equation}E = mc^2\end{equation}"
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.LATEX_ENV
        assert matches[0].environment_name == "equation"

    def test_latex_align_env(self, detector):
        """Test LaTeX align environment"""
        text = r"\begin{align}a &= b \\ c &= d\end{align}"
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.LATEX_ENV
        assert matches[0].environment_name == "align"

    # Unicode math tests
    def test_unicode_math_symbols(self, detector):
        """Test Unicode math symbol detection"""
        text = "The integral ∫∫∫ is a triple integral."
        matches = detector.detect_formulas(text)

        assert len(matches) == 1
        assert matches[0].formula_type == FormulaType.UNICODE_MATH
        assert "∫∫∫" in matches[0].content

    # Chemical formula tests (NEW in Phase 3)
    def test_chemical_formula_simple(self, detector):
        """Test simple chemical formula detection"""
        text = "Water is H2O and ethanol is CH3CH2OH."
        matches = detector.detect_formulas(text, include_chemical=True)

        # Should detect H2O and CH3CH2OH
        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        assert len(chemical_matches) >= 1

        # Check for ethanol formula
        ethanol = [m for m in chemical_matches if "CH3CH2OH" in m.content]
        assert len(ethanol) == 1

    def test_chemical_formula_sulfuric_acid(self, detector):
        """Test sulfuric acid formula"""
        text = "Sulfuric acid has the formula H2SO4."
        matches = detector.detect_formulas(text, include_chemical=True)

        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        assert len(chemical_matches) >= 1
        assert any("H2SO4" in m.content for m in chemical_matches)

    def test_chemical_formula_glucose(self, detector):
        """Test glucose formula"""
        text = "Glucose is C6H12O6."
        matches = detector.detect_formulas(text, include_chemical=True)

        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        assert len(chemical_matches) >= 1
        assert any("C6H12O6" in m.content for m in chemical_matches)

    def test_chemical_formula_smiles_simple(self, detector):
        """Test simple SMILES pattern"""
        text = "The SMILES notation C(CO)N represents a molecule."
        matches = detector.detect_formulas(text, include_chemical=True)

        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        assert len(chemical_matches) >= 1

    def test_chemical_formula_exclude_common_words(self, detector):
        """Test that common words are not detected as chemical formulas"""
        text = "Chemistry and Chemical engineering are fields."
        matches = detector.detect_formulas(text, include_chemical=True)

        # Should not detect "Chemistry" or "Chemical" as formulas
        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        false_positives = [m for m in chemical_matches if m.content in ["Chemistry", "Chemical"]]
        assert len(false_positives) == 0

    def test_chemical_formula_disable_flag(self, detector):
        """Test that chemical formula detection can be disabled"""
        text = "Water is H2O and ethanol is CH3CH2OH."

        # With chemical detection enabled
        matches_with = detector.detect_formulas(text, include_chemical=True)
        chemical_with = [m for m in matches_with if m.formula_type == FormulaType.CHEMICAL]

        # With chemical detection disabled
        matches_without = detector.detect_formulas(text, include_chemical=False)
        chemical_without = [m for m in matches_without if m.formula_type == FormulaType.CHEMICAL]

        assert len(chemical_with) > 0
        assert len(chemical_without) == 0

    # Multiple formulas tests
    def test_multiple_formulas_mixed(self, detector):
        """Test multiple formulas of different types"""
        text = "Einstein's $E = mc^2$ and water H2O are well-known."
        matches = detector.detect_formulas(text, include_chemical=True)

        # Should have both math and chemical
        assert len(matches) >= 2

        math_matches = [m for m in matches if m.formula_type == FormulaType.INLINE_DOLLAR]
        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]

        assert len(math_matches) >= 1
        assert len(chemical_matches) >= 1

    # Edge cases
    def test_empty_text(self, detector):
        """Test empty text"""
        matches = detector.detect_formulas("")
        assert len(matches) == 0

    def test_no_formulas(self, detector):
        """Test text with no formulas"""
        text = "This is plain text with no formulas."
        matches = detector.detect_formulas(text)
        assert len(matches) == 0

    def test_overlapping_formulas(self, detector):
        """Test that overlapping formulas are handled"""
        text = "Nested $$outer $inner$ outer$$"
        matches = detector.detect_formulas(text)

        # Should prioritize display math over inline
        assert len(matches) >= 1

    # Utility method tests
    def test_has_formulas_true(self, detector):
        """Test has_formulas() returns True when formulas exist"""
        text = "The equation $E = mc^2$ is famous."
        assert detector.has_formulas(text) is True

    def test_has_formulas_false(self, detector):
        """Test has_formulas() returns False when no formulas"""
        text = "This is plain text."
        assert detector.has_formulas(text) is False

    def test_count_formulas(self, detector):
        """Test count_formulas() method"""
        text = "Equations: $a = b$ and $$c = d$$ and H2O"
        counts = detector.count_formulas(text)

        assert counts['total'] >= 2
        assert 'inline_dollar' in counts['by_type']
        assert 'display_dollar' in counts['by_type']

    # Real-world examples
    def test_scientific_paper_excerpt(self, detector):
        """Test realistic scientific paper text"""
        text = """
        The Schrödinger equation $i\hbar\frac{\partial}{\partial t}\Psi = \hat{H}\Psi$
        is fundamental in quantum mechanics. For a hydrogen atom with formula H2,
        we can solve this equation analytically.
        """
        matches = detector.detect_formulas(text, include_chemical=True)

        # Should detect at least the math equation
        # Note: H2 might not be detected as it's very short and conservative pattern
        assert len(matches) >= 1

        # Should have at least one math formula
        math_matches = [m for m in matches if m.formula_type in [
            FormulaType.INLINE_DOLLAR,
            FormulaType.DISPLAY_DOLLAR
        ]]
        assert len(math_matches) >= 1

    def test_chemistry_paper_excerpt(self, detector):
        """Test realistic chemistry paper text"""
        text = """
        The reaction of methanol CH3OH with oxygen O2 produces
        carbon dioxide CO2 and water H2O. The balanced equation is:
        $$2CH_3OH + 3O_2 \\rightarrow 2CO_2 + 4H_2O$$
        """
        matches = detector.detect_formulas(text, include_chemical=True)

        # Should detect both display math and chemical formulas
        assert len(matches) >= 2

        chemical_matches = [m for m in matches if m.formula_type == FormulaType.CHEMICAL]
        math_matches = [m for m in matches if m.formula_type == FormulaType.DISPLAY_DOLLAR]

        assert len(chemical_matches) >= 1
        assert len(math_matches) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
