#!/usr/bin/env python3
"""
Phase 2.0.1 Semantic Document Model - Test Suite

Tests for DocNodeType enum and DocNode dataclass.

Usage:
    python3 tests/test_phase20_semantic_model.py
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.structure.semantic_model import (
    DocNodeType,
    DocNode,
    DocNodeList
)


class TestDocNodeType(unittest.TestCase):
    """Test DocNodeType enum"""

    def test_all_node_types_exist(self):
        """Verify all expected node types are defined"""
        expected_types = [
            'CHAPTER', 'SECTION', 'SUBSECTION',
            'THEOREM', 'LEMMA', 'PROPOSITION', 'COROLLARY', 'DEFINITION', 'REMARK',
            'PROOF',
            'EQUATION_BLOCK',
            'PARAGRAPH',
            'REFERENCES_SECTION', 'REFERENCE_ENTRY',
            'UNKNOWN'
        ]
        for type_name in expected_types:
            self.assertTrue(hasattr(DocNodeType, type_name))

    def test_enum_values(self):
        """Test enum values are lowercase strings"""
        self.assertEqual(DocNodeType.CHAPTER.value, "chapter")
        self.assertEqual(DocNodeType.THEOREM.value, "theorem")
        self.assertEqual(DocNodeType.PROOF.value, "proof")
        self.assertEqual(DocNodeType.PARAGRAPH.value, "paragraph")


class TestDocNode(unittest.TestCase):
    """Test DocNode dataclass"""

    def test_basic_node_creation(self):
        """Test creating a simple DocNode"""
        node = DocNode(
            node_type=DocNodeType.PARAGRAPH,
            text="This is a paragraph."
        )
        self.assertEqual(node.node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(node.text, "This is a paragraph.")
        self.assertIsNone(node.title)
        self.assertIsNone(node.level)
        self.assertEqual(node.children, [])
        self.assertEqual(node.metadata, {})

    def test_heading_node(self):
        """Test creating a heading node with title and level"""
        node = DocNode(
            node_type=DocNodeType.CHAPTER,
            text="Introduction to Measure Theory",
            title="Chapter 1",
            level=1
        )
        self.assertEqual(node.node_type, DocNodeType.CHAPTER)
        self.assertEqual(node.title, "Chapter 1")
        self.assertEqual(node.level, 1)

    def test_theorem_node_with_metadata(self):
        """Test creating a theorem node with metadata"""
        node = DocNode(
            node_type=DocNodeType.THEOREM,
            text="Every compact subset of a Hausdorff space is closed.",
            title="Theorem 2.3",
            metadata={"number": "2.3", "page": 42}
        )
        self.assertEqual(node.node_type, DocNodeType.THEOREM)
        self.assertEqual(node.title, "Theorem 2.3")
        self.assertEqual(node.metadata["number"], "2.3")
        self.assertEqual(node.metadata["page"], 42)

    def test_is_heading_method(self):
        """Test is_heading() method"""
        chapter = DocNode(DocNodeType.CHAPTER, "Intro")
        section = DocNode(DocNodeType.SECTION, "Background")
        subsection = DocNode(DocNodeType.SUBSECTION, "Details")
        paragraph = DocNode(DocNodeType.PARAGRAPH, "Text")

        self.assertTrue(chapter.is_heading())
        self.assertTrue(section.is_heading())
        self.assertTrue(subsection.is_heading())
        self.assertFalse(paragraph.is_heading())

    def test_is_theorem_like_method(self):
        """Test is_theorem_like() method"""
        theorem = DocNode(DocNodeType.THEOREM, "Theorem text")
        lemma = DocNode(DocNodeType.LEMMA, "Lemma text")
        definition = DocNode(DocNodeType.DEFINITION, "Definition text")
        paragraph = DocNode(DocNodeType.PARAGRAPH, "Text")
        proof = DocNode(DocNodeType.PROOF, "Proof text")

        self.assertTrue(theorem.is_theorem_like())
        self.assertTrue(lemma.is_theorem_like())
        self.assertTrue(definition.is_theorem_like())
        self.assertFalse(paragraph.is_theorem_like())
        self.assertFalse(proof.is_theorem_like())

    def test_is_proof_method(self):
        """Test is_proof() method"""
        proof = DocNode(DocNodeType.PROOF, "Proof text")
        theorem = DocNode(DocNodeType.THEOREM, "Theorem text")

        self.assertTrue(proof.is_proof())
        self.assertFalse(theorem.is_proof())

    def test_is_equation_method(self):
        """Test is_equation() method"""
        equation = DocNode(DocNodeType.EQUATION_BLOCK, "$$E = mc^2$$")
        paragraph = DocNode(DocNodeType.PARAGRAPH, "Text")

        self.assertTrue(equation.is_equation())
        self.assertFalse(paragraph.is_equation())

    def test_node_with_children(self):
        """Test hierarchical structure with children"""
        child1 = DocNode(DocNodeType.PARAGRAPH, "First paragraph")
        child2 = DocNode(DocNodeType.PARAGRAPH, "Second paragraph")
        
        parent = DocNode(
            node_type=DocNodeType.SECTION,
            text="Introduction",
            title="Section 1",
            children=[child1, child2]
        )

        self.assertEqual(len(parent.children), 2)
        self.assertEqual(parent.children[0].text, "First paragraph")
        self.assertEqual(parent.children[1].text, "Second paragraph")

    def test_repr_method(self):
        """Test __repr__ output is informative"""
        node = DocNode(
            node_type=DocNodeType.THEOREM,
            text="This is a very long theorem statement that should be truncated in the repr output" * 5,
            title="Theorem 1.1",
            level=2
        )
        repr_output = repr(node)

        self.assertIn("theorem", repr_output)
        self.assertIn("Theorem 1.1", repr_output)
        self.assertIn("L2", repr_output)
        self.assertIn("...", repr_output)  # Truncation indicator


class TestDocNodeList(unittest.TestCase):
    """Test DocNodeList type alias"""

    def test_docnodelist_is_list(self):
        """Test that DocNodeList works as a list"""
        nodes: DocNodeList = [
            DocNode(DocNodeType.CHAPTER, "Chapter 1"),
            DocNode(DocNodeType.PARAGRAPH, "Some text"),
            DocNode(DocNodeType.THEOREM, "Theorem statement")
        ]

        self.assertEqual(len(nodes), 3)
        self.assertIsInstance(nodes, list)
        self.assertEqual(nodes[0].node_type, DocNodeType.CHAPTER)
        self.assertEqual(nodes[1].node_type, DocNodeType.PARAGRAPH)
        self.assertEqual(nodes[2].node_type, DocNodeType.THEOREM)


if __name__ == '__main__':
    unittest.main()
