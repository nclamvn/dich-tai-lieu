"""
Phase 2.0.1 - Semantic Document Model
Phase 3.0 - Extended for Commercial Book Translation

Pure semantic representation of document structure.
No dependencies on DOCX or rendering - just data structures.

This is the single source of truth for document structure modeling.
Supports both academic/STEM documents and commercial book translation.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class DocNodeType(Enum):
    """
    Semantic types for document nodes.

    Covers both academic/STEM documents and commercial book translation.
    """
    # Document structure
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"

    # Mathematical/academic blocks
    THEOREM = "theorem"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    COROLLARY = "corollary"
    DEFINITION = "definition"
    EXAMPLE = "example"  # Phase 2.0.8: Added for academic documents
    REMARK = "remark"

    # Proof blocks
    PROOF = "proof"

    # Equations
    EQUATION_BLOCK = "equation_block"

    # Content
    PARAGRAPH = "paragraph"

    # Phase 3.0: Book-specific types
    BLOCKQUOTE = "blockquote"  # Quoted text in books
    EPIGRAPH = "epigraph"  # Chapter epigraphs (quotes at start of chapter)
    SCENE_BREAK = "scene_break"  # Scene separators (*, ---, etc.)
    FRONT_MATTER = "front_matter"  # Title page, copyright, dedication, TOC
    BACK_MATTER = "back_matter"  # Appendices, acknowledgments, author bio
    DIALOGUE = "dialogue"  # Dialogue paragraphs (for advanced formatting)

    # References
    REFERENCES_SECTION = "references_section"
    REFERENCE_ENTRY = "reference_entry"

    # Fallback
    UNKNOWN = "unknown"


@dataclass
class DocNode:
    """
    A node in the semantic document tree/list.

    Represents a single semantic unit: chapter, theorem, proof, paragraph, etc.

    Attributes:
        node_type: The semantic type of this node
        text: The actual text content (may include LaTeX formulas)
        title: Optional title/label (e.g., "Theorem 1.1", "Chapter 3")
        level: Optional hierarchy level (1=chapter, 2=section, 3=subsection)
        children: Optional child nodes (for hierarchical structure)
        metadata: Arbitrary additional data (page numbers, styles, etc.)

    Examples:
        # Chapter heading
        DocNode(
            node_type=DocNodeType.CHAPTER,
            text="Introduction to Measure Theory",
            title="Chapter 1",
            level=1
        )

        # Theorem with proof
        DocNode(
            node_type=DocNodeType.THEOREM,
            text="Every compact subset of a Hausdorff space is closed.",
            title="Theorem 2.3",
            metadata={"number": "2.3"}
        )

        # Proof block
        DocNode(
            node_type=DocNodeType.PROOF,
            text="Let K be compact and x ∈ X \\ K. For each y ∈ K...",
        )

        # Display equation
        DocNode(
            node_type=DocNodeType.EQUATION_BLOCK,
            text="$$\\int_a^b f(x) dx = F(b) - F(a)$$",
            metadata={"equation_number": "3.5"}
        )
    """
    node_type: DocNodeType
    text: str
    title: Optional[str] = None
    level: Optional[int] = None
    children: List["DocNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_heading(self) -> bool:
        """Check if this node is a heading (chapter/section/subsection)"""
        return self.node_type in {
            DocNodeType.CHAPTER,
            DocNodeType.SECTION,
            DocNodeType.SUBSECTION
        }

    def is_theorem_like(self) -> bool:
        """Check if this node is a theorem-like block"""
        return self.node_type in {
            DocNodeType.THEOREM,
            DocNodeType.LEMMA,
            DocNodeType.PROPOSITION,
            DocNodeType.COROLLARY,
            DocNodeType.DEFINITION,
            DocNodeType.EXAMPLE,  # Phase 2.0.8
            DocNodeType.REMARK
        }

    def is_proof(self) -> bool:
        """Check if this node is a proof block"""
        return self.node_type == DocNodeType.PROOF

    def is_equation(self) -> bool:
        """Check if this node is an equation block"""
        return self.node_type == DocNodeType.EQUATION_BLOCK

    # Phase 3.0: Book-specific helper methods
    def is_blockquote(self) -> bool:
        """Check if this node is a blockquote"""
        return self.node_type == DocNodeType.BLOCKQUOTE

    def is_epigraph(self) -> bool:
        """Check if this node is an epigraph"""
        return self.node_type == DocNodeType.EPIGRAPH

    def is_scene_break(self) -> bool:
        """Check if this node is a scene break"""
        return self.node_type == DocNodeType.SCENE_BREAK

    def is_book_element(self) -> bool:
        """Check if this node is a book-specific element"""
        return self.node_type in {
            DocNodeType.BLOCKQUOTE,
            DocNodeType.EPIGRAPH,
            DocNodeType.SCENE_BREAK,
            DocNodeType.FRONT_MATTER,
            DocNodeType.BACK_MATTER,
            DocNodeType.DIALOGUE
        }

    def __repr__(self) -> str:
        """Human-readable representation for debugging"""
        title_part = f" '{self.title}'" if self.title else ""
        level_part = f" L{self.level}" if self.level is not None else ""
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"DocNode({self.node_type.value}{title_part}{level_part}: {text_preview!r})"


# Convenience type alias
DocNodeList = List[DocNode]
