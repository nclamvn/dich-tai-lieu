"""
Unit Tests for Document AST

Tests the core Document AST data structures to ensure they work correctly
before using them in the rendering pipeline.
"""

import pytest
from core.rendering.document_ast import (
    # Enums
    BlockType,
    HeadingLevel,
    ParagraphRole,
    EquationMode,
    TheoremType,

    # Styles
    FontStyle,
    SpacingStyle,
    ParagraphStyle,

    # Blocks
    Heading,
    Paragraph,
    Equation,
    TheoremBox,
    ProofBox,
    Blockquote,
    Epigraph,
    SceneBreak,
    ReferenceEntry,

    # Document
    DocumentMetadata,
    StyleSheet,
    DocumentAST,

    # Helpers
    create_book_stylesheet,
    create_academic_stylesheet,
)


class TestFontStyle:
    """Test FontStyle data structure."""

    def test_default_values(self):
        """Test default font style values."""
        font = FontStyle()
        assert font.family == "Georgia"
        assert font.size_pt == 11.0
        assert font.bold is False
        assert font.italic is False
        assert font.color == "000000"

    def test_custom_values(self):
        """Test custom font style."""
        font = FontStyle(
            family="Cambria",
            size_pt=14.0,
            bold=True,
            italic=True,
            color="FF0000"
        )
        assert font.family == "Cambria"
        assert font.size_pt == 14.0
        assert font.bold is True
        assert font.italic is True
        assert font.color == "FF0000"


class TestSpacingStyle:
    """Test SpacingStyle data structure."""

    def test_default_values(self):
        """Test default spacing values."""
        spacing = SpacingStyle()
        assert spacing.line_spacing == 1.3
        assert spacing.space_before_pt == 0.0
        assert spacing.space_after_pt == 0.0
        assert spacing.first_line_indent_pt == 0.0
        assert spacing.left_indent_pt == 0.0
        assert spacing.right_indent_pt == 0.0

    def test_custom_values(self):
        """Test custom spacing."""
        spacing = SpacingStyle(
            line_spacing=1.5,
            space_before_pt=12.0,
            space_after_pt=6.0,
            first_line_indent_pt=18.0,
            left_indent_pt=36.0,
            right_indent_pt=36.0
        )
        assert spacing.line_spacing == 1.5
        assert spacing.space_before_pt == 12.0
        assert spacing.space_after_pt == 6.0
        assert spacing.first_line_indent_pt == 18.0
        assert spacing.left_indent_pt == 36.0
        assert spacing.right_indent_pt == 36.0


class TestParagraphStyle:
    """Test ParagraphStyle data structure."""

    def test_default_values(self):
        """Test default paragraph style."""
        style = ParagraphStyle()
        assert isinstance(style.font, FontStyle)
        assert isinstance(style.spacing, SpacingStyle)
        assert style.alignment == "justify"
        assert style.keep_with_next is False
        assert style.keep_together is False
        assert style.page_break_before is False


class TestHeading:
    """Test Heading block."""

    def test_create_heading_h1(self):
        """Test creating H1 heading."""
        heading = Heading(
            level=HeadingLevel.H1,
            text="Chapter 1: Introduction",
            number="1"
        )
        assert heading.block_type == BlockType.HEADING
        assert heading.level == HeadingLevel.H1
        assert heading.text == "Chapter 1: Introduction"
        assert heading.number == "1"

    def test_create_heading_h2(self):
        """Test creating H2 heading."""
        heading = Heading(
            level=HeadingLevel.H2,
            text="Section 1.1",
            number="1.1"
        )
        assert heading.level == HeadingLevel.H2
        assert heading.text == "Section 1.1"

    def test_create_heading_h3(self):
        """Test creating H3 heading."""
        heading = Heading(
            level=HeadingLevel.H3,
            text="Subsection 1.1.1"
        )
        assert heading.level == HeadingLevel.H3


class TestParagraph:
    """Test Paragraph block."""

    def test_create_body_paragraph(self):
        """Test creating body paragraph."""
        para = Paragraph(
            text="This is a body paragraph.",
            role=ParagraphRole.BODY
        )
        assert para.block_type == BlockType.PARAGRAPH
        assert para.text == "This is a body paragraph."
        assert para.role == ParagraphRole.BODY

    def test_create_first_paragraph(self):
        """Test creating first paragraph (no indent)."""
        para = Paragraph(
            text="This is the first paragraph after a heading.",
            role=ParagraphRole.FIRST_PARAGRAPH
        )
        assert para.role == ParagraphRole.FIRST_PARAGRAPH

    def test_create_dialogue_paragraph(self):
        """Test creating dialogue paragraph."""
        para = Paragraph(
            text='"Hello, world!" she said.',
            role=ParagraphRole.DIALOGUE
        )
        assert para.role == ParagraphRole.DIALOGUE


class TestBlockquote:
    """Test Blockquote block."""

    def test_create_blockquote_without_attribution(self):
        """Test blockquote without attribution."""
        quote = Blockquote(
            text="This is a quoted text."
        )
        assert quote.block_type == BlockType.BLOCKQUOTE
        assert quote.text == "This is a quoted text."
        assert quote.attribution is None

    def test_create_blockquote_with_attribution(self):
        """Test blockquote with attribution."""
        quote = Blockquote(
            text="To be or not to be, that is the question.",
            attribution="Shakespeare"
        )
        assert quote.text == "To be or not to be, that is the question."
        assert quote.attribution == "Shakespeare"


class TestEpigraph:
    """Test Epigraph block."""

    def test_create_epigraph(self):
        """Test creating epigraph."""
        epigraph = Epigraph(
            text="The beginning is the most important part of the work.",
            attribution="Plato"
        )
        assert epigraph.block_type == BlockType.EPIGRAPH
        assert epigraph.text == "The beginning is the most important part of the work."
        assert epigraph.attribution == "Plato"


class TestSceneBreak:
    """Test SceneBreak block."""

    def test_create_scene_break_default(self):
        """Test default scene break."""
        sb = SceneBreak()
        assert sb.block_type == BlockType.SCENE_BREAK
        assert sb.symbol == "* * *"

    def test_create_scene_break_custom(self):
        """Test custom scene break symbol."""
        sb = SceneBreak(symbol="◆ ◆ ◆")
        assert sb.symbol == "◆ ◆ ◆"


class TestEquation:
    """Test Equation block."""

    def test_create_display_equation(self):
        """Test display equation."""
        eq = Equation(
            latex=r"\int_a^b f(x) dx = F(b) - F(a)",
            mode=EquationMode.DISPLAY,
            number="3.5"
        )
        assert eq.block_type == BlockType.EQUATION
        assert eq.latex == r"\int_a^b f(x) dx = F(b) - F(a)"
        assert eq.mode == EquationMode.DISPLAY
        assert eq.number == "3.5"

    def test_create_inline_equation(self):
        """Test inline equation."""
        eq = Equation(
            latex="x^2 + y^2 = r^2",
            mode=EquationMode.INLINE
        )
        assert eq.mode == EquationMode.INLINE
        assert eq.number is None

    def test_equation_with_omml(self):
        """Test equation with OMML XML."""
        eq = Equation(
            latex="a^2 + b^2 = c^2",
            mode=EquationMode.DISPLAY,
            omml_xml="<m:oMathPara>...</m:oMathPara>"
        )
        assert eq.omml_xml == "<m:oMathPara>...</m:oMathPara>"


class TestTheoremBox:
    """Test TheoremBox block."""

    def test_create_theorem(self):
        """Test creating theorem."""
        thm = TheoremBox(
            theorem_type=TheoremType.THEOREM,
            title="Theorem 2.3",
            content="Every compact subset of a Hausdorff space is closed.",
            number="2.3"
        )
        assert thm.block_type == BlockType.THEOREM_BOX
        assert thm.theorem_type == TheoremType.THEOREM
        assert thm.title == "Theorem 2.3"
        assert thm.number == "2.3"

    def test_create_definition(self):
        """Test creating definition."""
        defn = TheoremBox(
            theorem_type=TheoremType.DEFINITION,
            title="Definition 1.1",
            content="A metric space is a set X with a distance function d: X × X → R."
        )
        assert defn.theorem_type == TheoremType.DEFINITION


class TestProofBox:
    """Test ProofBox block."""

    def test_create_proof(self):
        """Test creating proof."""
        proof = ProofBox(
            content="Let K be compact and x ∈ X \\ K. For each y ∈ K...",
            qed_symbol="□"
        )
        assert proof.block_type == BlockType.PROOF_BOX
        assert proof.content.startswith("Let K be compact")
        assert proof.qed_symbol == "□"

    def test_create_proof_custom_qed(self):
        """Test proof with custom QED symbol."""
        proof = ProofBox(
            content="The proof follows directly.",
            qed_symbol="∎"
        )
        assert proof.qed_symbol == "∎"


class TestReferenceEntry:
    """Test ReferenceEntry block."""

    def test_create_reference(self):
        """Test creating reference entry."""
        ref = ReferenceEntry(
            citation="Smith, J. (2020). Introduction to Mathematics. Publisher.",
            key="Smith2020"
        )
        assert ref.block_type == BlockType.REFERENCE_ENTRY
        assert ref.citation.startswith("Smith, J.")
        assert ref.key == "Smith2020"


class TestDocumentMetadata:
    """Test DocumentMetadata."""

    def test_default_metadata(self):
        """Test default metadata values."""
        meta = DocumentMetadata()
        assert meta.title is None
        assert meta.author is None
        assert meta.language == "vi"
        assert meta.source_language == "en"
        assert meta.domain == "book"
        assert meta.layout_mode == "book"

    def test_custom_metadata(self):
        """Test custom metadata."""
        meta = DocumentMetadata(
            title="My Book",
            author="John Doe",
            language="en",
            domain="stem",
            layout_mode="academic"
        )
        assert meta.title == "My Book"
        assert meta.author == "John Doe"
        assert meta.domain == "stem"
        assert meta.layout_mode == "academic"


class TestStyleSheet:
    """Test StyleSheet."""

    def test_default_stylesheet(self):
        """Test default stylesheet."""
        styles = StyleSheet()

        # Check heading styles exist
        assert isinstance(styles.heading_1, ParagraphStyle)
        assert isinstance(styles.heading_2, ParagraphStyle)
        assert isinstance(styles.heading_3, ParagraphStyle)

        # Check body style
        assert isinstance(styles.body, ParagraphStyle)

        # Check book-specific styles
        assert isinstance(styles.blockquote, ParagraphStyle)
        assert isinstance(styles.epigraph, ParagraphStyle)

        # Check heading sizes
        assert styles.heading_1.font.size_pt == 16.0
        assert styles.heading_2.font.size_pt == 14.0
        assert styles.heading_3.font.size_pt == 12.0

    def test_book_stylesheet(self):
        """Test book-optimized stylesheet."""
        styles = create_book_stylesheet()

        # Georgia font for books
        assert styles.heading_1.font.family == "Georgia"
        assert styles.body.font.family == "Georgia"

        # Page break before H1
        assert styles.heading_1.page_break_before is True

    def test_academic_stylesheet(self):
        """Test academic-optimized stylesheet."""
        styles = create_academic_stylesheet()

        # Cambria font for academic
        assert styles.heading_1.font.family == "Cambria"
        assert styles.body.font.family == "Cambria"

        # Academic has theorem box style
        assert isinstance(styles.theorem_box, ParagraphStyle)


class TestDocumentAST:
    """Test DocumentAST."""

    def test_create_empty_document(self):
        """Test creating empty document."""
        meta = DocumentMetadata()
        styles = StyleSheet()
        ast = DocumentAST(metadata=meta, styles=styles, blocks=[])

        assert ast.metadata == meta
        assert ast.styles == styles
        assert len(ast) == 0
        assert len(ast.blocks) == 0

    def test_add_blocks(self):
        """Test adding blocks to document."""
        meta = DocumentMetadata()
        styles = StyleSheet()
        ast = DocumentAST(metadata=meta, styles=styles)

        # Add heading
        ast.add_block(Heading(
            level=HeadingLevel.H1,
            text="Chapter 1"
        ))

        # Add paragraphs
        ast.add_block(Paragraph(
            text="First paragraph.",
            role=ParagraphRole.BODY
        ))

        ast.add_block(Paragraph(
            text="Second paragraph.",
            role=ParagraphRole.BODY
        ))

        assert len(ast) == 3
        assert len(ast.blocks) == 3

    def test_get_headings(self):
        """Test getting all headings from document."""
        ast = DocumentAST(
            metadata=DocumentMetadata(),
            styles=StyleSheet()
        )

        ast.add_block(Heading(level=HeadingLevel.H1, text="Chapter 1"))
        ast.add_block(Paragraph(text="Text"))
        ast.add_block(Heading(level=HeadingLevel.H2, text="Section 1.1"))
        ast.add_block(Paragraph(text="More text"))

        headings = ast.get_headings()
        assert len(headings) == 2
        assert headings[0].level == HeadingLevel.H1
        assert headings[1].level == HeadingLevel.H2

    def test_get_equations(self):
        """Test getting all equations from document."""
        ast = DocumentAST(
            metadata=DocumentMetadata(),
            styles=StyleSheet()
        )

        ast.add_block(Paragraph(text="Text before equation"))
        ast.add_block(Equation(latex="x^2", mode=EquationMode.DISPLAY))
        ast.add_block(Paragraph(text="Text after equation"))
        ast.add_block(Equation(latex="y = mx + b", mode=EquationMode.DISPLAY))

        equations = ast.get_equations()
        assert len(equations) == 2
        assert equations[0].latex == "x^2"
        assert equations[1].latex == "y = mx + b"

    def test_get_theorems(self):
        """Test getting all theorems from document."""
        ast = DocumentAST(
            metadata=DocumentMetadata(),
            styles=StyleSheet()
        )

        ast.add_block(TheoremBox(
            theorem_type=TheoremType.THEOREM,
            title="Theorem 1",
            content="Statement 1"
        ))

        ast.add_block(Paragraph(text="Some text"))

        ast.add_block(TheoremBox(
            theorem_type=TheoremType.LEMMA,
            title="Lemma 1",
            content="Statement 2"
        ))

        theorems = ast.get_theorems()
        assert len(theorems) == 2
        assert theorems[0].theorem_type == TheoremType.THEOREM
        assert theorems[1].theorem_type == TheoremType.LEMMA

    def test_document_repr(self):
        """Test document __repr__."""
        meta = DocumentMetadata(domain="book")
        ast = DocumentAST(metadata=meta, styles=StyleSheet())

        ast.add_block(Heading(level=HeadingLevel.H1, text="Chapter"))
        ast.add_block(Paragraph(text="Text"))
        ast.add_block(Equation(latex="E=mc^2", mode=EquationMode.DISPLAY))

        repr_str = repr(ast)
        assert "domain=book" in repr_str
        assert "blocks=3" in repr_str
        assert "headings=1" in repr_str
        assert "equations=1" in repr_str


class TestCompleteDocument:
    """Test creating complete documents."""

    def test_create_book_chapter(self):
        """Test creating a complete book chapter."""
        meta = DocumentMetadata(
            title="My Novel",
            domain="book",
            layout_mode="book"
        )
        styles = create_book_stylesheet()
        ast = DocumentAST(metadata=meta, styles=styles)

        # Chapter heading
        ast.add_block(Heading(
            level=HeadingLevel.H1,
            text="Chapter 1: The Beginning",
            number="1"
        ))

        # Epigraph
        ast.add_block(Epigraph(
            text="All beginnings are hard.",
            attribution="Chaim Potok"
        ))

        # Body paragraphs
        ast.add_block(Paragraph(
            text="It was a dark and stormy night.",
            role=ParagraphRole.FIRST_PARAGRAPH
        ))

        ast.add_block(Paragraph(
            text="The rain poured down in torrents.",
            role=ParagraphRole.BODY
        ))

        # Scene break
        ast.add_block(SceneBreak(symbol="* * *"))

        # More text
        ast.add_block(Paragraph(
            text="Later that evening...",
            role=ParagraphRole.BODY
        ))

        # Verify structure
        assert len(ast) == 6
        assert len(ast.get_headings()) == 1
        assert ast.metadata.domain == "book"
        assert ast.styles.body.font.family == "Georgia"

    def test_create_academic_document(self):
        """Test creating academic document with theorems."""
        meta = DocumentMetadata(
            domain="stem",
            layout_mode="academic"
        )
        styles = create_academic_stylesheet()
        ast = DocumentAST(metadata=meta, styles=styles)

        # Section heading
        ast.add_block(Heading(
            level=HeadingLevel.H2,
            text="Main Results",
            number="2"
        ))

        # Theorem
        ast.add_block(TheoremBox(
            theorem_type=TheoremType.THEOREM,
            title="Theorem 2.1",
            content="For all x in X, there exists y in Y such that f(x) = y.",
            number="2.1"
        ))

        # Proof
        ast.add_block(ProofBox(
            content="The proof follows by construction.",
            qed_symbol="□"
        ))

        # Equation
        ast.add_block(Equation(
            latex=r"\sum_{i=1}^{n} x_i = 0",
            mode=EquationMode.DISPLAY,
            number="2.1"
        ))

        # Verify structure
        assert len(ast) == 4
        assert len(ast.get_theorems()) == 1
        assert len(ast.get_equations()) == 1
        assert ast.styles.body.font.family == "Cambria"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
