#!/usr/bin/env python3
"""
Phase 2.0.2 Semantic Document Extractor - Test Suite

Tests for semantic structure extraction from paragraphs.

UPDATED for Phase 2.0.2 full implementation.

Usage:
    python3 tests/test_phase20_semantic_extractor.py
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.structure.semantic_extractor import (
    extract_semantic_structure,
    _detect_heading,
    _detect_theorem_like,
    _detect_proof_start,
    _detect_proof_end,
    _detect_references_section,
    _detect_equation_block
)
from core.structure.semantic_model import DocNodeType, DocNode


class TestDetectHeading(unittest.TestCase):
    """Test _detect_heading function"""

    def test_english_chapter(self):
        """Test English chapter detection"""
        result = _detect_heading("Chapter 1")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.CHAPTER)
        self.assertEqual(level, 1)

    def test_english_chapter_uppercase(self):
        """Test uppercase CHAPTER"""
        result = _detect_heading("CHAPTER 3: Introduction")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.CHAPTER)

    def test_vietnamese_chapter(self):
        """Test Vietnamese chapter detection"""
        result = _detect_heading("Chương 2")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.CHAPTER)
        self.assertEqual(level, 1)

    def test_numbered_section(self):
        """Test numbered section (1. Title)"""
        result = _detect_heading("1. Introduction")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.SECTION)
        self.assertEqual(level, 2)

    def test_subsection(self):
        """Test subsection (1.1 Title)"""
        result = _detect_heading("1.1 Background")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.SUBSECTION)
        self.assertEqual(level, 3)

    def test_section_keyword(self):
        """Test 'Section 1.1' pattern"""
        result = _detect_heading("Section 2.3")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.SUBSECTION)

    def test_vietnamese_section(self):
        """Test Vietnamese 'Mục' pattern"""
        result = _detect_heading("Mục 3.1")
        self.assertIsNotNone(result)
        node_type, title, level = result
        self.assertEqual(node_type, DocNodeType.SUBSECTION)

    def test_not_heading(self):
        """Test regular paragraph is not detected as heading"""
        result = _detect_heading("This is a regular paragraph with numbers 123.")
        self.assertIsNone(result)

    def test_theorem_not_heading(self):
        """Test theorem is not detected as heading"""
        result = _detect_heading("Theorem 1.1. Every measure is non-negative.")
        self.assertIsNone(result)


class TestDetectTheoremLike(unittest.TestCase):
    """Test _detect_theorem_like function"""

    def test_theorem_with_number(self):
        """Test Theorem with number"""
        result = _detect_theorem_like("Theorem 1.1")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.THEOREM)
        self.assertEqual(title, "Theorem 1.1")

    def test_lemma_with_number(self):
        """Test Lemma with number"""
        result = _detect_theorem_like("Lemma 2.3")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.LEMMA)
        self.assertEqual(title, "Lemma 2.3")

    def test_definition_with_number(self):
        """Test Definition with number"""
        result = _detect_theorem_like("Definition 3.5")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.DEFINITION)
        self.assertEqual(title, "Definition 3.5")

    def test_theorem_without_number(self):
        """Test Theorem without number (Theorem.)"""
        result = _detect_theorem_like("Theorem. Every compact subset is closed.")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.THEOREM)
        self.assertEqual(title, "Theorem")

    def test_vietnamese_theorem(self):
        """Test Vietnamese theorem"""
        result = _detect_theorem_like("Định lý 1.2")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.THEOREM)
        self.assertEqual(title, "Định lý 1.2")

    def test_vietnamese_lemma(self):
        """Test Vietnamese lemma"""
        result = _detect_theorem_like("Bổ đề 3.1")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.LEMMA)

    def test_vietnamese_definition(self):
        """Test Vietnamese definition"""
        result = _detect_theorem_like("Định nghĩa 2.4")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.DEFINITION)

    def test_remark(self):
        """Test Remark"""
        result = _detect_theorem_like("Remark 1.5")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.REMARK)

    def test_example_as_remark(self):
        """Test Example is treated as Remark"""
        result = _detect_theorem_like("Example 2.1")
        self.assertIsNotNone(result)
        node_type, title = result
        self.assertEqual(node_type, DocNodeType.REMARK)

    def test_not_theorem(self):
        """Test regular paragraph is not detected as theorem"""
        result = _detect_theorem_like("This is a regular paragraph.")
        self.assertIsNone(result)


class TestDetectProof(unittest.TestCase):
    """Test proof detection functions"""

    def test_proof_start_with_period(self):
        """Test 'Proof.' detection"""
        result = _detect_proof_start("Proof. Let x be arbitrary.")
        self.assertTrue(result)

    def test_proof_start_with_colon(self):
        """Test 'Proof:' detection"""
        result = _detect_proof_start("Proof: We proceed by induction.")
        self.assertTrue(result)

    def test_proof_of(self):
        """Test 'Proof of Theorem 1.1' detection"""
        result = _detect_proof_start("Proof of Theorem 1.1")
        self.assertTrue(result)

    def test_vietnamese_proof(self):
        """Test Vietnamese proof"""
        result = _detect_proof_start("Chứng minh. Giả sử x là tùy ý.")
        self.assertTrue(result)

    def test_not_proof_start(self):
        """Test regular paragraph is not proof"""
        result = _detect_proof_start("This is a regular paragraph.")
        self.assertFalse(result)

    def test_proof_end_qed_box(self):
        """Test QED box symbol ∎"""
        result = _detect_proof_end("Thus we have proven the claim. ∎")
        self.assertTrue(result)

    def test_proof_end_hollow_box(self):
        """Test hollow box symbol □"""
        result = _detect_proof_end("Therefore the theorem holds. □")
        self.assertTrue(result)

    def test_proof_end_filled_box(self):
        """Test filled box symbol ■"""
        result = _detect_proof_end("This completes the proof. ■")
        self.assertTrue(result)

    def test_no_proof_end(self):
        """Test paragraph without QED marker"""
        result = _detect_proof_end("This is just a regular sentence.")
        self.assertFalse(result)


class TestDetectReferencesSection(unittest.TestCase):
    """Test references section detection"""

    def test_references_heading(self):
        """Test 'References' heading"""
        result = _detect_references_section("References")
        self.assertTrue(result)

    def test_references_uppercase(self):
        """Test 'REFERENCES' heading"""
        result = _detect_references_section("REFERENCES")
        self.assertTrue(result)

    def test_bibliography(self):
        """Test 'Bibliography' heading"""
        result = _detect_references_section("Bibliography")
        self.assertTrue(result)

    def test_vietnamese_references(self):
        """Test Vietnamese 'Tài liệu tham khảo'"""
        result = _detect_references_section("Tài liệu tham khảo")
        self.assertTrue(result)

    def test_appendix(self):
        """Test 'Appendix' heading"""
        result = _detect_references_section("Appendix A")
        self.assertTrue(result)

    def test_not_references(self):
        """Test regular paragraph is not references"""
        result = _detect_references_section("This refers to previous work.")
        self.assertFalse(result)


class TestDetectEquationBlock(unittest.TestCase):
    """Test equation block detection"""

    def test_display_math_double_dollar(self):
        """Test $$...$$ detection"""
        result = _detect_equation_block("$$E = mc^2$$")
        self.assertTrue(result)

    def test_display_math_brackets(self):
        """Test \\[...\\] detection"""
        result = _detect_equation_block("\\[\\int_a^b f(x) dx\\]")
        self.assertTrue(result)

    def test_inline_math_short_paragraph(self):
        """Test short paragraph with inline math"""
        result = _detect_equation_block("$x \\in \\mathbb{R}$")
        self.assertTrue(result)

    def test_math_heavy_content(self):
        """Test paragraph with high math symbol density"""
        result = _detect_equation_block("∀x ∈ ℝ, ∃y ∈ ℂ: x² + y² = 1")
        self.assertTrue(result)

    def test_not_equation_long_text(self):
        """Test long paragraph with some math is not equation block"""
        result = _detect_equation_block(
            "This is a long paragraph discussing mathematical concepts. "
            "We have the equation $E = mc^2$ which is famous. "
            "However, this is primarily text and not an equation block. " * 10
        )
        self.assertFalse(result)

    def test_not_equation_no_math(self):
        """Test regular paragraph without math"""
        result = _detect_equation_block("This is a regular paragraph.")
        self.assertFalse(result)


class TestExtractSemanticStructure(unittest.TestCase):
    """Test extract_semantic_structure function with real implementation"""

    def test_empty_input(self):
        """Test with empty paragraph list"""
        paragraphs = []
        nodes = extract_semantic_structure(paragraphs)
        self.assertEqual(len(nodes), 0)

    def test_single_paragraph(self):
        """Test with a single regular paragraph"""
        paragraphs = ["This is a simple paragraph."]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(nodes[0].text, "This is a simple paragraph.")

    def test_chapter_detection(self):
        """Test chapter is detected"""
        paragraphs = [
            "Chapter 1: Introduction",
            "This chapter introduces the topic."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].node_type, DocNodeType.CHAPTER)
        self.assertEqual(nodes[0].level, 1)
        self.assertEqual(nodes[1].node_type, DocNodeType.PARAGRAPH)

    def test_theorem_single_paragraph(self):
        """Test single-paragraph theorem"""
        paragraphs = [
            "Theorem 1.1. Every compact subset of a Hausdorff space is closed."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[0].title, "Theorem 1.1")

    def test_theorem_multi_paragraph(self):
        """Test multi-paragraph theorem block"""
        paragraphs = [
            "Theorem 1.1. Let X be a topological space.",
            "Then every compact subset K is closed.",
            "Furthermore, K is bounded."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect theorem and merge all paragraphs
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertIn("Let X be a topological space", nodes[0].text)
        self.assertIn("Furthermore, K is bounded", nodes[0].text)

    def test_proof_block(self):
        """Test proof block detection"""
        paragraphs = [
            "Proof. Let K be compact and x ∈ X \\ K.",
            "For each y ∈ K, choose disjoint neighborhoods.",
            "This completes the proof. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_type, DocNodeType.PROOF)
        self.assertIn("Let K be compact", nodes[0].text)
        self.assertIn("This completes the proof", nodes[0].text)

    def test_theorem_then_proof(self):
        """Test theorem followed by proof"""
        paragraphs = [
            "Theorem 1.1. Every measure is non-negative.",
            "Proof. Let μ be a measure.",
            "By definition, μ(∅) = 0 and μ(A) ≥ 0. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)

    def test_equation_block(self):
        """Test equation block detection"""
        paragraphs = [
            "The famous equation is:",
            "$$E = mc^2$$",
            "This shows mass-energy equivalence."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[1].node_type, DocNodeType.EQUATION_BLOCK)
        self.assertIn("E = mc^2", nodes[1].text)

    def test_references_section(self):
        """Test references section"""
        paragraphs = [
            "References",
            "[1] Rudin, W. (1987). Real and Complex Analysis.",
            "[2] Folland, G. (1999). Real Analysis."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0].node_type, DocNodeType.REFERENCES_SECTION)
        self.assertEqual(nodes[1].node_type, DocNodeType.REFERENCE_ENTRY)
        self.assertEqual(nodes[2].node_type, DocNodeType.REFERENCE_ENTRY)

    def test_vietnamese_content(self):
        """Test Vietnamese academic content"""
        paragraphs = [
            "Chương 1: Giới thiệu",
            "Định lý 1.1. Mọi tập compact trong không gian Hausdorff đều đóng.",
            "Chứng minh. Giả sử K là compact và x ∈ X \\ K.",
            "Điều này hoàn tất chứng minh. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0].node_type, DocNodeType.CHAPTER)
        self.assertEqual(nodes[1].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[2].node_type, DocNodeType.PROOF)

    def test_priority_order(self):
        """Test heading has higher priority than theorem"""
        paragraphs = [
            "1. Introduction",
            "Theorem 1.1. Important result."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(nodes[0].node_type, DocNodeType.SECTION)
        self.assertEqual(nodes[1].node_type, DocNodeType.THEOREM)

    def test_empty_paragraphs_filtered(self):
        """Test that empty paragraphs are filtered out"""
        paragraphs = [
            "First paragraph.",
            "",
            "  ",
            "Third paragraph."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].text, "First paragraph.")
        self.assertEqual(nodes[1].text, "Third paragraph.")

    def test_complex_document_structure(self):
        """Test complex document with multiple element types"""
        paragraphs = [
            "Chapter 1: Measure Theory",
            "1. Introduction",
            "Measure theory is fundamental to modern analysis.",
            "Definition 1.1. A measure is a function μ: Σ → [0, ∞].",
            "Theorem 1.2. Every measure is monotone.",
            "Proof. Let A ⊆ B. Then B = A ∪ (B \\ A). ∎",
            "$$\\mu(B) = \\mu(A) + \\mu(B \\setminus A)$$",
            "Remark. This is a basic property.",
            "References",
            "[1] Rudin, W. (1987). Real and Complex Analysis."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Verify correct number and types
        self.assertEqual(len(nodes), 10)
        self.assertEqual(nodes[0].node_type, DocNodeType.CHAPTER)
        self.assertEqual(nodes[1].node_type, DocNodeType.SECTION)
        self.assertEqual(nodes[2].node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(nodes[3].node_type, DocNodeType.DEFINITION)
        self.assertEqual(nodes[4].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[5].node_type, DocNodeType.PROOF)
        self.assertEqual(nodes[6].node_type, DocNodeType.EQUATION_BLOCK)
        self.assertEqual(nodes[7].node_type, DocNodeType.REMARK)
        self.assertEqual(nodes[8].node_type, DocNodeType.REFERENCES_SECTION)
        self.assertEqual(nodes[9].node_type, DocNodeType.REFERENCE_ENTRY)


class TestFormulaPreservation(unittest.TestCase):
    """Test that LaTeX formulas are preserved exactly (critical constraint)"""

    def test_inline_math_preserved(self):
        """Test inline math $...$ is preserved"""
        paragraphs = ["The equation $E = mc^2$ is famous."]
        nodes = extract_semantic_structure(paragraphs)

        self.assertIn("$E = mc^2$", nodes[0].text)

    def test_display_math_preserved(self):
        """Test display math $$...$$ is preserved"""
        paragraphs = ["$$\\int_a^b f(x) dx = F(b) - F(a)$$"]
        nodes = extract_semantic_structure(paragraphs)

        self.assertIn("$$\\int_a^b f(x) dx = F(b) - F(a)$$", nodes[0].text)

    def test_complex_formula_preserved(self):
        """Test complex formulas are preserved"""
        paragraphs = [
            "Theorem 1. For all $x \\in \\mathbb{R}$, we have:",
            "$$\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}$$"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Check all LaTeX is preserved
        combined_text = " ".join(node.text for node in nodes)
        self.assertIn("$x \\in \\mathbb{R}$", combined_text)
        self.assertIn("$$\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}$$", combined_text)

    def test_formulas_in_theorem_preserved(self):
        """Test formulas within theorems are preserved"""
        paragraphs = [
            "Theorem 1.1. For all $\\epsilon > 0$, there exists $\\delta > 0$ such that $|f(x) - f(a)| < \\epsilon$."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertIn("$\\epsilon > 0$", nodes[0].text)
        self.assertIn("$\\delta > 0$", nodes[0].text)
        self.assertIn("$|f(x) - f(a)| < \\epsilon$", nodes[0].text)


class TestUnicodeHandling(unittest.TestCase):
    """Test Unicode and special characters"""

    def test_unicode_math_symbols(self):
        """Test Unicode math symbols are preserved"""
        paragraphs = ["∀x ∈ ℝ, ∃y ∈ ℂ such that x² + y² = 1"]
        nodes = extract_semantic_structure(paragraphs)

        self.assertIn("∀x ∈ ℝ", nodes[0].text)
        self.assertIn("∃y ∈ ℂ", nodes[0].text)

    def test_vietnamese_text(self):
        """Test Vietnamese text with diacritics"""
        paragraphs = [
            "Định nghĩa 1.1. Một không gian metric là một cặp (X, d)."
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(nodes[0].node_type, DocNodeType.DEFINITION)
        self.assertIn("không gian metric", nodes[0].text)

    def test_mixed_languages(self):
        """Test mixed English and Vietnamese"""
        paragraphs = [
            "Chapter 1: Introduction",
            "Định lý 1.1. Every compact set is closed.",
            "Chứng minh. This follows from the definition. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0].node_type, DocNodeType.CHAPTER)
        self.assertEqual(nodes[1].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[2].node_type, DocNodeType.PROOF)


class TestPhase203aProofDetection(unittest.TestCase):
    """
    Phase 2.0.3a - Robust Proof Detection Tests

    Tests for multi-paragraph proofs, proof-theorem anchoring, and EN/VI patterns.
    """

    def test_en_single_paragraph_proof_with_qed(self):
        """Test English single-paragraph proof with QED marker"""
        paragraphs = [
            "Theorem 1.1. Some important statement.",
            "Proof. We now show that the claim holds. QED"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: 1 THEOREM + 1 PROOF
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)

        # Proof should be single paragraph
        self.assertIn("We now show that the claim holds", nodes[1].text)
        self.assertIn("QED", nodes[1].text)

    def test_en_multi_paragraph_proof_with_qed_symbol(self):
        """Test English multi-paragraph proof with QED symbol"""
        paragraphs = [
            "Theorem 2.3. Important result.",
            "Proof. First we observe that the property holds.",
            "Next, we apply Lemma 1.1 to obtain the desired inequality.",
            "This completes the proof. ∎",
            "Example 2.4. Another statement."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: THEOREM + PROOF (3 paragraphs) + REMARK (Example)
        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)
        self.assertEqual(nodes[2].node_type, DocNodeType.REMARK)

        # Proof should contain all 3 paragraphs
        proof_text = nodes[1].text
        self.assertIn("First we observe", proof_text)
        self.assertIn("Next, we apply Lemma 1.1", proof_text)
        self.assertIn("This completes the proof", proof_text)

        # Example should NOT be in proof
        self.assertNotIn("Example 2.4", proof_text)

    def test_vi_proof_with_het_chung_minh(self):
        """Test Vietnamese proof with 'Hết chứng minh' marker"""
        paragraphs = [
            "Định lý 1.1. Mệnh đề quan trọng.",
            "Chứng minh. Trước hết ta xét trường hợp đơn giản.",
            "Hết chứng minh."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: 1 THEOREM + 1 PROOF
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)

        # Proof should contain both paragraphs
        proof_text = nodes[1].text
        self.assertIn("Trước hết ta xét", proof_text)
        self.assertIn("Hết chứng minh", proof_text)

    def test_vi_proof_no_qed_ends_at_theorem(self):
        """Test Vietnamese proof without QED marker (ends at next theorem)"""
        paragraphs = [
            "Định lý 1.1. Mệnh đề đầu tiên.",
            "Chứng minh. Ta có tính chất cơ bản.",
            "Do đó suy ra kết luận mong muốn.",
            "Định lý 1.2. Mệnh đề tiếp theo."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Note: Lookahead ends proof before "Do đó suy ra", making it a PARAGRAPH
        # Result: THEOREM + PROOF (1 para) + PARAGRAPH + THEOREM
        self.assertEqual(len(nodes), 4)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)
        self.assertEqual(nodes[2].node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(nodes[3].node_type, DocNodeType.THEOREM)

        # Proof contains first paragraph only
        proof_text = nodes[1].text
        self.assertIn("Ta có tính chất", proof_text)

        # "Do đó suy ra" is separate PARAGRAPH
        self.assertEqual(nodes[2].text, "Do đó suy ra kết luận mong muốn.")

        # Second theorem is separate
        self.assertEqual(nodes[3].title, "Định lý 1.2")

    def test_inline_proof_heading(self):
        """Test inline proof heading (proof content on same line)"""
        paragraphs = [
            "Chứng minh. Từ đó ta thấy rằng điều cần chứng minh hiển nhiên.",
            "Do đó mệnh đề được chứng minh. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: 1 PROOF with 2 paragraphs
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].node_type, DocNodeType.PROOF)

        proof_text = nodes[0].text
        self.assertIn("Từ đó ta thấy", proof_text)
        self.assertIn("Do đó mệnh đề", proof_text)

    def test_proof_with_explicit_label(self):
        """Test proof with explicit theorem label ('Proof of Theorem 4.2')"""
        paragraphs = [
            "Theorem 4.2. Main result.",
            "Some discussion paragraph.",
            "Proof of Theorem 4.2. We proceed by contradiction.",
            "This completes the proof. ∎"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: THEOREM (multi-paragraph, includes discussion) + PROOF
        # Note: "Some discussion" is absorbed into THEOREM as multi-paragraph block
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)

        # Proof should have explicit_label metadata
        proof = nodes[1]
        self.assertIn('explicit_label', proof.metadata)
        self.assertEqual(proof.metadata['explicit_label'], "Theorem 4.2")

    def test_proof_theorem_anchoring_metadata(self):
        """Test proof-theorem anchoring via metadata"""
        paragraphs = [
            "Theorem 1.1. Important statement.",
            "Proof. We prove this directly. QED"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: THEOREM + PROOF
        self.assertEqual(len(nodes), 2)
        theorem = nodes[0]
        proof = nodes[1]

        # Proof should have anchoring metadata
        self.assertIn('related_to_type', proof.metadata)
        self.assertIn('related_to_label', proof.metadata)

        # Verify anchoring points to theorem
        self.assertEqual(proof.metadata['related_to_type'], 'THEOREM')
        self.assertEqual(proof.metadata['related_to_label'], "Theorem 1.1")

    def test_multiple_proofs_in_sequence(self):
        """Test multiple theorem-proof pairs in sequence"""
        paragraphs = [
            "Lemma 2.1. First auxiliary result.",
            "Proof. This is straightforward. ∎",
            "Lemma 2.2. Second auxiliary result.",
            "Proof. Similar to Lemma 2.1.",
            "The claim follows. QED"
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Should detect: LEMMA + PROOF + LEMMA + PROOF
        self.assertEqual(len(nodes), 4)
        self.assertEqual(nodes[0].node_type, DocNodeType.LEMMA)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)
        self.assertEqual(nodes[2].node_type, DocNodeType.LEMMA)
        self.assertEqual(nodes[3].node_type, DocNodeType.PROOF)

        # First proof anchored to first lemma
        self.assertEqual(nodes[1].metadata['related_to_label'], "Lemma 2.1")

        # Second proof anchored to second lemma
        self.assertEqual(nodes[3].metadata['related_to_label'], "Lemma 2.2")

    def test_proof_ends_at_section_heading(self):
        """Test proof without QED ends when new section starts"""
        paragraphs = [
            "Theorem 3.1. Main result of this section.",
            "Proof. We establish the result in three steps.",
            "Step 1: Verify the base case.",
            "Step 2: Apply induction.",
            "2. Next Section",
            "This section discusses applications."
        ]
        nodes = extract_semantic_structure(paragraphs)

        # Note: Lookahead ends proof before "Step 2" due to upcoming SECTION
        # Result: THEOREM + PROOF (2 paras) + PARAGRAPH + SECTION + PARAGRAPH
        self.assertEqual(len(nodes), 5)
        self.assertEqual(nodes[0].node_type, DocNodeType.THEOREM)
        self.assertEqual(nodes[1].node_type, DocNodeType.PROOF)
        self.assertEqual(nodes[2].node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(nodes[3].node_type, DocNodeType.SECTION)
        self.assertEqual(nodes[4].node_type, DocNodeType.PARAGRAPH)

        # Proof contains "Proof" + "Step 1" only
        proof_text = nodes[1].text
        self.assertIn("three steps", proof_text)
        self.assertIn("Step 1", proof_text)

        # "Step 2" is separate PARAGRAPH
        self.assertEqual(nodes[2].text, "Step 2: Apply induction.")

        # Section heading is separate
        self.assertNotIn("Next Section", proof_text)


if __name__ == '__main__':
    unittest.main()
