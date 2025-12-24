#!/usr/bin/env python3
"""
Phase 1.9 Vietnamese Academic Polisher - Test Suite

Tests for Vietnamese terminology normalization and academic phrasing improvements.

Critical requirements:
- 100% formula preservation (NEVER modify math content)
- Proper noun preservation (mathematician names, institutions)
- Theorem/Lemma numbering preservation
- Safe, conservative improvements only

Usage:
    python3 tests/test_phase19_vn_polisher.py
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.postprocess.vn_academic_polisher import (
    VietnameseAcademicPolisher,
    Phase19PolishingStats
)


class TestTerminologyNormalization(unittest.TestCase):
    """Test Vietnamese terminology normalization"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_estimation_terminology(self):
        """Test normalization of 'ước tính' → 'ước lượng'"""
        text = "Chúng ta cần ước tính giá trị này."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("ước lượng", result)
        self.assertNotIn("ước tính", result)

    def test_set_terminology(self):
        """Test normalization of 'tập' → 'tập hợp' (in set theory context)"""
        text = "Xét tập A và tập B."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("tập hợp", result)

    def test_phrase_normalization(self):
        """Test normalization of common phrases"""
        text = "Chúng ta thu được kết quả này."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Ta thu được", result)
        self.assertNotIn("Chúng ta thu được", result)


class TestPhraseImprovements(unittest.TestCase):
    """Test academic Vietnamese phrase improvements"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_academic_connector(self):
        """Test 'Chúng ta có thể thấy rằng' → 'Ta thấy rằng'"""
        text = "Chúng ta có thể thấy rằng giá trị này là dương."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Ta thấy rằng", result)
        self.assertNotIn("Chúng ta có thể thấy rằng", result)

    def test_academic_concision(self):
        """Test 'Chúng ta có' → 'Ta có'"""
        text = "Chúng ta có công thức sau."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Ta có", result)
        self.assertNotIn("Chúng ta có", result)

    def test_redundancy_removal(self):
        """Test 'một cách chính xác' → 'chính xác'"""
        text = "Kết quả này được xác định một cách chính xác."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("chính xác", result)
        self.assertNotIn("một cách chính xác", result)


class TestFormulaPreservation(unittest.TestCase):
    """Critical tests for 100% formula preservation"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_inline_math_preserved(self):
        """Test inline math $...$ is preserved"""
        text = "Giá trị $x$ phải thỏa mãn $x > 0$."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("$x$", result)
        self.assertIn("$x > 0$", result)

    def test_display_math_preserved(self):
        """Test display math $$...$$ is preserved"""
        text = "Ta có công thức $$E = mc^2$$."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("$$E = mc^2$$", result)

    def test_latex_brackets_preserved(self):
        """Test LaTeX brackets \\[...\\] are preserved"""
        text = "Phương trình \\[\\nabla^2 \\phi = 0\\] là phương trình Laplace."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("\\[\\nabla^2 \\phi = 0\\]", result)

    def test_latex_environment_preserved(self):
        """Test LaTeX environments are preserved"""
        text = "\\begin{equation}x^2 + y^2 = 1\\end{equation}"
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("\\begin{equation}x^2 + y^2 = 1\\end{equation}", result)

    def test_complex_formula_preserved(self):
        """Test complex formulas with subscripts, superscripts, fractions"""
        text = "Định lý 1.1: $$\\sum_{i=1}^{n} \\frac{1}{i^2} = \\frac{\\pi^2}{6}$$."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("$$\\sum_{i=1}^{n} \\frac{1}{i^2} = \\frac{\\pi^2}{6}$$", result)

    def test_formula_count_preserved(self):
        """Test that formula count is preserved (no formulas lost)"""
        text = """
        Ta có $a = b$ và $c = d$.
        Từ đó suy ra $$a + c = b + d$$.
        """
        polished, stats = self.polisher.polish_with_stats(text)

        # Count formulas in original
        import re
        original_count = len(re.findall(r'\$[^\$]+?\$', text))

        # Count formulas in polished
        polished_count = len(re.findall(r'\$[^\$]+?\$', polished))

        self.assertEqual(original_count, polished_count,
                        "Formula count must be preserved")
        self.assertEqual(stats.formulas_corrupted, 0,
                        "No formulas should be corrupted")

    def test_mixed_text_and_formulas(self):
        """Test polishing text while preserving formulas"""
        text = "Chúng ta có thể thấy rằng ước tính $\\hat{\\theta}$ là chính xác."
        result = self.polisher.polish(text, track_stats=False)

        # Check text improved
        self.assertIn("Ta thấy rằng", result)
        self.assertIn("ước lượng", result)

        # Check formula preserved
        self.assertIn("$\\hat{\\theta}$", result)


class TestProperNounPreservation(unittest.TestCase):
    """Test that proper nouns are not modified"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_mathematician_names_preserved(self):
        """Test mathematician names are not translated"""
        text = "Theo Cauchy-Schwarz và Hardy-Littlewood, ta có ước tính sau."
        result = self.polisher.polish(text, track_stats=False)

        # Names preserved
        self.assertIn("Cauchy-Schwarz", result)
        self.assertIn("Hardy-Littlewood", result)

        # Text improved
        self.assertIn("ước lượng", result)

    def test_institution_names_preserved(self):
        """Test institution names are not modified"""
        text = "Nghiên cứu tại Heidelberg và Cambridge."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Heidelberg", result)
        self.assertIn("Cambridge", result)

    def test_grant_ids_preserved(self):
        """Test grant IDs and licenses are not modified"""
        text = "Được hỗ trợ bởi DMS-0649473 theo CC-BY."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("DMS-0649473", result)
        self.assertIn("CC-BY", result)


class TestTheoremNumberingPreservation(unittest.TestCase):
    """Test that theorem/lemma numbering is preserved"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_theorem_numbering(self):
        """Test 'Định lý X.Y' format is preserved"""
        text = "Theo Định lý 1.1 và Định lý 2.3, chúng ta có kết quả."
        result = self.polisher.polish(text, track_stats=False)

        # Numbering preserved
        self.assertIn("Định lý 1.1", result)
        self.assertIn("Định lý 2.3", result)

        # Text improved
        self.assertIn("ta có", result)

    def test_lemma_numbering(self):
        """Test 'Bổ đề X.Y' format is preserved"""
        text = "Bổ đề 3.2 chứng tỏ rằng tập này là compact."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Bổ đề 3.2", result)
        self.assertIn("tập hợp", result)

    def test_definition_numbering(self):
        """Test 'Định nghĩa X.Y' format is preserved"""
        text = "Định nghĩa 1.5 cho biết tập con này."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("Định nghĩa 1.5", result)


class TestStatisticsTracking(unittest.TestCase):
    """Test polishing statistics tracking"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_stats_returned(self):
        """Test that statistics are returned"""
        text = "Chúng ta có ước tính $x = 1$."
        polished, stats = self.polisher.polish_with_stats(text)

        self.assertIsInstance(stats, Phase19PolishingStats)
        self.assertGreater(stats.total_changes, 0)

    def test_term_changes_tracked(self):
        """Test term normalization changes are tracked"""
        text = "Ước tính này và ước tính kia."
        polished, stats = self.polisher.polish_with_stats(text)

        self.assertGreater(stats.terms_normalized, 0)
        self.assertIn("ước lượng", polished)

    def test_formula_protection_tracked(self):
        """Test formula protection is tracked"""
        text = "Ta có $a = b$ và $$c = d$$."
        polished, stats = self.polisher.polish_with_stats(text)

        self.assertGreater(stats.formulas_protected, 0)
        self.assertEqual(stats.formulas_corrupted, 0)

    def test_stats_to_dict(self):
        """Test statistics can be serialized to dict"""
        text = "Chúng ta có ước tính này."
        polished, stats = self.polisher.polish_with_stats(text)

        stats_dict = stats.to_dict()
        self.assertIsInstance(stats_dict, dict)
        self.assertIn('terms_normalized', stats_dict)
        self.assertIn('formulas_protected', stats_dict)
        self.assertIn('total_changes', stats_dict)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_empty_text(self):
        """Test polishing empty text"""
        result = self.polisher.polish("", track_stats=False)
        self.assertEqual(result, "")

    def test_only_formulas(self):
        """Test text with only formulas (no prose)"""
        text = "$x = 1$ $$y = 2$$"
        result = self.polisher.polish(text, track_stats=False)
        self.assertEqual(text.replace(" ", ""), result.replace(" ", ""))

    def test_nested_delimiters(self):
        """Test nested or malformed delimiters don't break"""
        text = "Ta có $x$ và $$y = \\{z : z > 0\\}$$."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("$x$", result)
        self.assertIn("$$", result)

    def test_unicode_vietnamese(self):
        """Test Unicode Vietnamese characters are preserved"""
        text = "Định lý về hàm điều hòa: $$\\Delta u = 0$$."
        result = self.polisher.polish(text, track_stats=False)
        self.assertIn("điều hòa", result)
        self.assertIn("$$\\Delta u = 0$$", result)

    def test_punctuation_fixes(self):
        """Test punctuation spacing fixes"""
        text = "Ta có  kết quả  sau :  $x = 1$  ."
        result = self.polisher.polish(text, track_stats=False)
        # Should fix double spaces and spacing around punctuation
        self.assertNotIn("  ", result)
        self.assertNotIn(" :", result)
        self.assertNotIn(" .", result)


class TestRegressionPrevention(unittest.TestCase):
    """Tests to prevent regressions from Phase 1.6/1.7"""

    def setUp(self):
        self.polisher = VietnameseAcademicPolisher()

    def test_no_paragraph_collapse(self):
        """Test that polishing doesn't collapse paragraphs"""
        text = "Đoạn 1.\n\nĐoạn 2.\n\nĐoạn 3."
        result = self.polisher.polish(text, track_stats=False)
        # Should preserve newlines
        self.assertIn("\n", result)

    def test_no_delimiter_corruption(self):
        """Test that polishing doesn't corrupt delimiters (Phase 1.6.3 issue)"""
        text = "Trong đó $h$ là hằng số Planck."
        result = self.polisher.polish(text, track_stats=False)
        # Should NOT become $$h$ or $h$$ or other malformed variants
        self.assertIn("$h$", result)
        self.assertNotIn("$$h$", result)
        self.assertNotIn("$h$$", result)


def run_tests(verbosity=2):
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTerminologyNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestPhraseImprovements))
    suite.addTests(loader.loadTestsFromTestCase(TestFormulaPreservation))
    suite.addTests(loader.loadTestsFromTestCase(TestProperNounPreservation))
    suite.addTests(loader.loadTestsFromTestCase(TestTheoremNumberingPreservation))
    suite.addTests(loader.loadTestsFromTestCase(TestStatisticsTracking))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestRegressionPrevention))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("Phase 1.9 Vietnamese Academic Polisher - Test Suite")
    print("=" * 70)
    print()

    success = run_tests(verbosity=2)

    print()
    print("=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        sys.exit(1)
