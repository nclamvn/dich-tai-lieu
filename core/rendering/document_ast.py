"""
Document AST (Abstract Syntax Tree) for Rendering

A rendering-oriented intermediate representation that sits between:
- Semantic model (DocNode) - WHAT the content means
- Output formats (DOCX, PDF) - HOW to render it

Design goals:
1. Decouple semantic meaning from presentation
2. Support multiple output formats (DOCX, PDF, HTML)
3. Capture typography and styling information
4. Handle both BOOK and STEM modes
5. Make it easy to add new export formats

Architecture:
    Semantic (DocNode)
         ↓
    AST Builder (converts)
         ↓
    Document AST (this layer)
         ↓
    Renderers (DOCX, PDF, HTML...)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


# ============================================================================
# Enums for AST Node Types
# ============================================================================

class BlockType(Enum):
    """Types of block-level elements in the document."""
    # Headings
    HEADING = "heading"

    # Content blocks
    PARAGRAPH = "paragraph"
    BLOCKQUOTE = "blockquote"
    EPIGRAPH = "epigraph"

    # Mathematical/academic blocks
    THEOREM_BOX = "theorem_box"  # Theorem, lemma, definition, etc.
    PROOF_BOX = "proof_box"
    EQUATION = "equation"

    # Book-specific
    SCENE_BREAK = "scene_break"
    FRONT_MATTER = "front_matter"
    BACK_MATTER = "back_matter"

    # References
    REFERENCE_ENTRY = "reference_entry"


class HeadingLevel(Enum):
    """Heading hierarchy levels."""
    H1 = 1  # Chapter
    H2 = 2  # Section
    H3 = 3  # Subsection


class ParagraphRole(Enum):
    """Semantic roles for paragraphs (affects styling)."""
    BODY = "body"  # Regular body text
    BLOCKQUOTE = "blockquote"  # Quoted text
    EPIGRAPH = "epigraph"  # Chapter epigraph
    DIALOGUE = "dialogue"  # Dialogue (for future use)
    FIRST_PARAGRAPH = "first_paragraph"  # First paragraph after heading (no indent)


class EquationMode(Enum):
    """How equations should be rendered."""
    INLINE = "inline"  # Inline: $x^2$
    DISPLAY = "display"  # Display: $$\int f(x) dx$$


class TheoremType(Enum):
    """Types of theorem-like environments."""
    THEOREM = "theorem"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    COROLLARY = "corollary"
    DEFINITION = "definition"
    EXAMPLE = "example"
    REMARK = "remark"


# ============================================================================
# Typography and Style Classes
# ============================================================================

@dataclass
class FontStyle:
    """Typography settings for text."""
    family: str = "Georgia"  # Font family
    size_pt: float = 11.0  # Font size in points
    bold: bool = False
    italic: bool = False
    color: str = "000000"  # Hex color (without #)


@dataclass
class SpacingStyle:
    """Spacing and indentation settings."""
    line_spacing: float = 1.3  # Line spacing multiplier
    space_before_pt: float = 0.0  # Space before paragraph (points)
    space_after_pt: float = 0.0  # Space after paragraph (points)
    first_line_indent_pt: float = 0.0  # First line indent (points)
    left_indent_pt: float = 0.0  # Left margin indent
    right_indent_pt: float = 0.0  # Right margin indent


@dataclass
class ParagraphStyle:
    """Complete paragraph styling."""
    font: FontStyle = field(default_factory=FontStyle)
    spacing: SpacingStyle = field(default_factory=SpacingStyle)
    alignment: str = "justify"  # left, right, center, justify
    keep_with_next: bool = False  # Keep with next paragraph
    keep_together: bool = False  # Keep lines together (no page break)
    page_break_before: bool = False  # Force page break before


# ============================================================================
# AST Block Classes
# ============================================================================

@dataclass
class Block:
    """Base class for all block-level AST nodes."""
    # block_type is set by subclasses in __post_init__, not passed as parameter
    block_type: BlockType = field(init=False, default=BlockType.PARAGRAPH)
    # Use kw_only for optional fields so subclasses can add required fields
    style: Optional[ParagraphStyle] = field(default=None, kw_only=True)
    metadata: Dict[str, Any] = field(default_factory=dict, kw_only=True)


@dataclass
class Heading(Block):
    """Heading block (chapter, section, subsection)."""
    level: HeadingLevel
    text: str
    number: Optional[str] = None  # e.g., "1.2.3"

    def __post_init__(self):
        self.block_type = BlockType.HEADING


@dataclass
class Paragraph(Block):
    """Paragraph of text."""
    text: str
    role: ParagraphRole = ParagraphRole.BODY

    def __post_init__(self):
        self.block_type = BlockType.PARAGRAPH


@dataclass
class Equation(Block):
    """Mathematical equation."""
    latex: str  # LaTeX source
    mode: EquationMode = EquationMode.DISPLAY
    number: Optional[str] = None  # Equation number (e.g., "3.5")
    omml_xml: Optional[str] = None  # Pre-rendered OMML (optional)

    def __post_init__(self):
        self.block_type = BlockType.EQUATION


@dataclass
class TheoremBox(Block):
    """Theorem, lemma, definition, etc."""
    theorem_type: TheoremType
    title: str  # e.g., "Theorem 2.3"
    content: str  # The theorem statement
    number: Optional[str] = None  # e.g., "2.3"

    def __post_init__(self):
        self.block_type = BlockType.THEOREM_BOX


@dataclass
class ProofBox(Block):
    """Proof environment."""
    content: str
    qed_symbol: str = "□"  # End-of-proof symbol

    def __post_init__(self):
        self.block_type = BlockType.PROOF_BOX


@dataclass
class Blockquote(Block):
    """Quoted text block."""
    text: str
    attribution: Optional[str] = None  # Author attribution

    def __post_init__(self):
        self.block_type = BlockType.BLOCKQUOTE


@dataclass
class Epigraph(Block):
    """Chapter epigraph (quote at start of chapter)."""
    text: str
    attribution: Optional[str] = None

    def __post_init__(self):
        self.block_type = BlockType.EPIGRAPH


@dataclass
class SceneBreak(Block):
    """Scene separator in books."""
    symbol: str = "* * *"  # Separator symbol

    def __post_init__(self):
        self.block_type = BlockType.SCENE_BREAK


@dataclass
class ReferenceEntry(Block):
    """Bibliography/reference entry."""
    citation: str  # Full citation text
    key: Optional[str] = None  # Citation key (e.g., "Smith2020")

    def __post_init__(self):
        self.block_type = BlockType.REFERENCE_ENTRY


# ============================================================================
# Document-level Classes
# ============================================================================

@dataclass
class DocumentMetadata:
    """Metadata for the entire document."""
    title: Optional[str] = None
    author: Optional[str] = None
    language: str = "vi"  # Target language
    source_language: str = "en"
    domain: str = "book"  # book, stem, general
    layout_mode: str = "book"  # book, academic, simple

    # Typography presets
    body_font: str = "Georgia"
    body_size_pt: float = 11.0
    heading_font: str = "Georgia"

    # Page settings (for PDF export)
    page_width_mm: float = 210.0  # A4
    page_height_mm: float = 297.0
    margin_top_mm: float = 25.0
    margin_bottom_mm: float = 25.0
    margin_left_mm: float = 25.0
    margin_right_mm: float = 25.0


@dataclass
class StyleSheet:
    """Collection of named styles for the document."""
    heading_1: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=16.0, bold=True),
        spacing=SpacingStyle(space_before_pt=18.0, space_after_pt=12.0),
        page_break_before=True,
        keep_with_next=True
    ))

    heading_2: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=14.0, bold=True),
        spacing=SpacingStyle(space_before_pt=14.0, space_after_pt=8.0),
        keep_with_next=True
    ))

    heading_3: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=12.0, bold=True),
        spacing=SpacingStyle(space_before_pt=12.0, space_after_pt=6.0),
        keep_with_next=True
    ))

    body: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=11.0),
        spacing=SpacingStyle(line_spacing=1.3, first_line_indent_pt=18.0),
        alignment="justify"
    ))

    blockquote: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=10.5, italic=True),
        spacing=SpacingStyle(
            line_spacing=1.2,
            left_indent_pt=36.0,
            right_indent_pt=36.0,
            space_before_pt=6.0,
            space_after_pt=6.0
        ),
        alignment="justify"
    ))

    epigraph: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=10.0, italic=True),
        spacing=SpacingStyle(
            left_indent_pt=144.0,  # Align to right
            space_after_pt=12.0
        ),
        alignment="right"
    ))

    scene_break: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Georgia", size_pt=12.0),
        spacing=SpacingStyle(space_before_pt=12.0, space_after_pt=12.0),
        alignment="center"
    ))

    # Academic/STEM styles
    theorem_box: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Cambria", size_pt=11.0, italic=True),
        spacing=SpacingStyle(
            left_indent_pt=18.0,
            right_indent_pt=18.0,
            space_before_pt=6.0,
            space_after_pt=6.0
        ),
        keep_together=True
    ))

    proof_box: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(
        font=FontStyle(family="Cambria", size_pt=11.0),
        spacing=SpacingStyle(
            left_indent_pt=18.0,
            space_before_pt=3.0,
            space_after_pt=6.0
        )
    ))


@dataclass
class DocumentAST:
    """
    Top-level Document AST.

    This is the complete intermediate representation that can be rendered
    to DOCX, PDF, HTML, or other formats.

    Structure:
        metadata: Document-level settings
        styles: Typography and formatting presets
        blocks: Sequential list of content blocks

    Usage:
        # Build AST from semantic nodes
        ast = ASTBuilder().build(doc_nodes, metadata)

        # Render to DOCX
        docx = DOCXRenderer().render(ast)

        # Render to PDF
        pdf = PDFRenderer().render(ast)
    """
    metadata: DocumentMetadata
    styles: StyleSheet
    blocks: List[Block] = field(default_factory=list)

    def add_block(self, block: Block) -> None:
        """Add a block to the document."""
        self.blocks.append(block)

    def get_headings(self) -> List[Heading]:
        """Get all heading blocks (for TOC generation)."""
        return [b for b in self.blocks if isinstance(b, Heading)]

    def get_equations(self) -> List[Equation]:
        """Get all equation blocks."""
        return [b for b in self.blocks if isinstance(b, Equation)]

    def get_theorems(self) -> List[TheoremBox]:
        """Get all theorem boxes."""
        return [b for b in self.blocks if isinstance(b, TheoremBox)]

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about blocks in the document.

        Returns:
            Dict with counts of each block type
        """
        from collections import Counter
        stats = {
            'headings': len([b for b in self.blocks if isinstance(b, Heading)]),
            'paragraphs': len([b for b in self.blocks if isinstance(b, Paragraph)]),
            'equations': len([b for b in self.blocks if isinstance(b, Equation)]),
            'blockquotes': len([b for b in self.blocks if isinstance(b, Blockquote)]),
            'epigraphs': len([b for b in self.blocks if isinstance(b, Epigraph)]),
            'scene_breaks': len([b for b in self.blocks if isinstance(b, SceneBreak)]),
            'theorems': len([b for b in self.blocks if isinstance(b, TheoremBox)]),
            'proofs': len([b for b in self.blocks if isinstance(b, ProofBox)]),
            'references': len([b for b in self.blocks if isinstance(b, ReferenceEntry)]),
        }
        return stats

    def __len__(self) -> int:
        """Number of blocks in document."""
        return len(self.blocks)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (f"DocumentAST(domain={self.metadata.domain}, "
                f"blocks={len(self.blocks)}, "
                f"headings={len(self.get_headings())}, "
                f"equations={len(self.get_equations())})")


# ============================================================================
# Helper Functions
# ============================================================================

def create_book_stylesheet() -> StyleSheet:
    """
    Create a stylesheet optimized for commercial book translation.

    Typography follows professional ebook standards:
    - Georgia font family (elegant serif for body text)
    - 11pt body with 1.15 line spacing
    - 0.32" (~23pt) first-line indent for paragraphs
    - Proper heading hierarchy (H1=16pt, H2=14pt, H3=12pt)
    - Page breaks before chapter headings
    """
    return StyleSheet(
        # Chapter heading (H1) - Maps to "Heading 1" in Word
        heading_1=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=16.0, bold=True),
            spacing=SpacingStyle(
                space_before_pt=18.0,
                space_after_pt=12.0
            ),
            alignment="left",
            page_break_before=True,  # New chapter = new page
            keep_with_next=True
        ),

        # Section heading (H2) - Maps to "Heading 2" in Word
        heading_2=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=14.0, bold=True),
            spacing=SpacingStyle(
                space_before_pt=14.0,
                space_after_pt=8.0
            ),
            alignment="left",
            keep_with_next=True
        ),

        # Subsection heading (H3) - Maps to "Heading 3" in Word
        heading_3=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=12.0, bold=True),
            spacing=SpacingStyle(
                space_before_pt=12.0,
                space_after_pt=6.0
            ),
            alignment="left",
            keep_with_next=True
        ),

        # Body paragraph - Commercial ebook standard
        body=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=11.0),
            spacing=SpacingStyle(
                line_spacing=1.15,          # Professional line spacing (not too loose)
                first_line_indent_pt=23.0,  # ~0.32" indent (commercial standard)
                space_after_pt=6.0          # Small gap between paragraphs
            ),
            alignment="justify"  # Full justification for professional look
        ),

        # Blockquote - Indented on both sides
        blockquote=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=10.5, italic=True),
            spacing=SpacingStyle(
                line_spacing=1.2,
                left_indent_pt=36.0,    # ~0.5" left indent
                right_indent_pt=36.0,   # ~0.5" right indent
                space_before_pt=9.0,    # Visual separation before
                space_after_pt=9.0      # Visual separation after
            ),
            alignment="justify"
        ),

        # Epigraph - Opening quote (right-aligned, italic)
        epigraph=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=10.0, italic=True),
            spacing=SpacingStyle(
                left_indent_pt=144.0,   # Right-align effect
                space_before_pt=12.0,   # Space before chapter content
                space_after_pt=12.0     # Space after epigraph
            ),
            alignment="right"
        ),

        # Scene break - Centered symbol with generous spacing
        scene_break=ParagraphStyle(
            font=FontStyle(family="Georgia", size_pt=12.0),
            spacing=SpacingStyle(
                space_before_pt=15.0,   # Generous space before scene break
                space_after_pt=15.0     # Generous space after scene break
            ),
            alignment="center"
        )
    )


def create_academic_stylesheet() -> StyleSheet:
    """Create a stylesheet optimized for academic/STEM documents (Cambria)."""
    return StyleSheet(
        heading_1=ParagraphStyle(
            font=FontStyle(family="Cambria", size_pt=16.0, bold=True),
            spacing=SpacingStyle(space_before_pt=18.0, space_after_pt=12.0),
            page_break_before=True,
            keep_with_next=True
        ),
        heading_2=ParagraphStyle(
            font=FontStyle(family="Cambria", size_pt=14.0, bold=True),
            spacing=SpacingStyle(space_before_pt=14.0, space_after_pt=8.0),
            keep_with_next=True
        ),
        body=ParagraphStyle(
            font=FontStyle(family="Cambria", size_pt=11.0),
            spacing=SpacingStyle(line_spacing=1.15, first_line_indent_pt=0.0),
            alignment="left"
        ),
        theorem_box=ParagraphStyle(
            font=FontStyle(family="Cambria", size_pt=11.0, italic=True),
            spacing=SpacingStyle(
                left_indent_pt=18.0,
                right_indent_pt=18.0,
                space_before_pt=6.0,
                space_after_pt=6.0
            ),
            keep_together=True
        )
    )


# ============================================================================
# Type Aliases
# ============================================================================

BlockList = List[Block]
"""List of AST blocks"""
