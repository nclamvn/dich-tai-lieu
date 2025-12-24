"""
AST Builder - Converts Semantic Model to Document AST

Transforms semantic DocNode lists into rendering-oriented DocumentAST.

Flow:
    DocNode list (semantic) → ASTBuilder → DocumentAST → Renderer (DOCX/PDF)

Responsibilities:
- Map semantic node types to AST block types
- Apply typography and styling based on layout mode
- Preserve equation information for both LaTeX and OMML rendering
- Handle both BOOK and STEM modes correctly
"""

from typing import List, Optional, Dict, Any
import logging

from core.structure.semantic_model import DocNode, DocNodeType, DocNodeList
from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    StyleSheet,
    Block,
    Heading,
    HeadingLevel,
    Paragraph,
    ParagraphRole,
    Equation,
    EquationMode,
    TheoremBox,
    TheoremType,
    ProofBox,
    Blockquote,
    Epigraph,
    SceneBreak,
    ReferenceEntry,
    create_book_stylesheet,
    create_academic_stylesheet,
)

logger = logging.getLogger(__name__)


class ASTBuilder:
    """
    Builds Document AST from semantic DocNode list.

    Usage:
        builder = ASTBuilder()
        ast = builder.build(doc_nodes, metadata)

        # Render to DOCX
        docx = DOCXRenderer().render(ast)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._last_block_breaks_paragraph_flow = True  # Start of document counts as break

    def build(
        self,
        doc_nodes: DocNodeList,
        metadata: Optional[DocumentMetadata] = None,
        preserve_omml: bool = False
    ) -> DocumentAST:
        """
        Build DocumentAST from semantic node list.

        Args:
            doc_nodes: List of semantic DocNode objects
            metadata: Document metadata (optional, will use defaults)
            preserve_omml: If True, preserve OMML XML in equation metadata

        Returns:
            DocumentAST ready for rendering
        """
        # Use defaults if metadata not provided
        if metadata is None:
            metadata = DocumentMetadata()

        # Select stylesheet based on layout mode
        if metadata.layout_mode == "academic":
            styles = create_academic_stylesheet()
        elif metadata.layout_mode == "book":
            styles = create_book_stylesheet()
        else:
            styles = StyleSheet()  # Default

        # Create AST
        ast = DocumentAST(
            metadata=metadata,
            styles=styles,
            blocks=[]
        )

        # Convert each semantic node to AST block
        for node in doc_nodes:
            block = self._convert_node(node, metadata, preserve_omml)
            if block:
                ast.add_block(block)

        self.logger.info(f"Built DocumentAST: {len(ast)} blocks, "
                        f"{len(ast.get_headings())} headings, "
                        f"{len(ast.get_equations())} equations")

        return ast

    def _convert_node(
        self,
        node: DocNode,
        metadata: DocumentMetadata,
        preserve_omml: bool
    ) -> Optional[Block]:
        """
        Convert a single semantic node to an AST block.

        Args:
            node: Semantic DocNode
            metadata: Document metadata
            preserve_omml: Whether to preserve OMML in equations

        Returns:
            AST Block or None if node should be skipped
        """
        # Dispatch based on node type
        if node.is_heading():
            return self._convert_heading(node)

        elif node.node_type == DocNodeType.PARAGRAPH:
            return self._convert_paragraph(node)

        elif node.is_blockquote():
            return self._convert_blockquote(node)

        elif node.is_epigraph():
            return self._convert_epigraph(node)

        elif node.is_scene_break():
            return self._convert_scene_break(node)

        elif node.is_theorem_like():
            return self._convert_theorem(node)

        elif node.is_proof():
            return self._convert_proof(node)

        elif node.is_equation():
            return self._convert_equation(node, preserve_omml)

        elif node.node_type == DocNodeType.REFERENCE_ENTRY:
            return self._convert_reference(node)

        else:
            # Unknown or unsupported node type
            self.logger.warning(f"Skipping unsupported node type: {node.node_type}")
            return None

    # ========================================================================
    # Conversion Methods for Each Node Type
    # ========================================================================

    def _convert_heading(self, node: DocNode) -> Heading:
        """Convert heading node to Heading block."""
        # Headings break paragraph flow (next paragraph should have no indent)
        self._last_block_breaks_paragraph_flow = True

        # Map level (1-3)
        if node.level == 1:
            level = HeadingLevel.H1
        elif node.level == 2:
            level = HeadingLevel.H2
        else:
            level = HeadingLevel.H3

        # Extract number if present
        number = node.metadata.get('number')

        return Heading(
            level=level,
            text=node.text,
            number=number,
            metadata=node.metadata
        )

    def _convert_paragraph(self, node: DocNode) -> Paragraph:
        """Convert paragraph node to Paragraph block."""
        # Determine paragraph role based on context
        role = ParagraphRole.BODY

        # Check metadata for explicit role hints (takes precedence)
        if node.metadata.get('is_first_paragraph'):
            role = ParagraphRole.FIRST_PARAGRAPH
        elif node.metadata.get('role') == 'dialogue':
            role = ParagraphRole.DIALOGUE
        elif self._last_block_breaks_paragraph_flow:
            # Auto-detect first paragraph after heading/break (commercial convention)
            role = ParagraphRole.FIRST_PARAGRAPH

        # Reset flow-break flag after consuming it
        self._last_block_breaks_paragraph_flow = False

        return Paragraph(
            text=node.text,
            role=role,
            metadata=node.metadata
        )

    def _convert_blockquote(self, node: DocNode) -> Blockquote:
        """Convert blockquote node to Blockquote block."""
        attribution = node.metadata.get('attribution')

        return Blockquote(
            text=node.text,
            attribution=attribution,
            metadata=node.metadata
        )

    def _convert_epigraph(self, node: DocNode) -> Epigraph:
        """Convert epigraph node to Epigraph block."""
        attribution = node.metadata.get('attribution')

        return Epigraph(
            text=node.text,
            attribution=attribution,
            metadata=node.metadata
        )

    def _convert_scene_break(self, node: DocNode) -> SceneBreak:
        """Convert scene break node to SceneBreak block."""
        # Scene breaks also break paragraph flow (next paragraph should have no indent)
        self._last_block_breaks_paragraph_flow = True

        # Default symbol is "* * *"
        symbol = node.text if node.text.strip() else "* * *"

        return SceneBreak(
            symbol=symbol,
            metadata=node.metadata
        )

    def _convert_theorem(self, node: DocNode) -> TheoremBox:
        """Convert theorem-like node to TheoremBox block."""
        # Map semantic type to theorem type
        theorem_type_map = {
            DocNodeType.THEOREM: TheoremType.THEOREM,
            DocNodeType.LEMMA: TheoremType.LEMMA,
            DocNodeType.PROPOSITION: TheoremType.PROPOSITION,
            DocNodeType.COROLLARY: TheoremType.COROLLARY,
            DocNodeType.DEFINITION: TheoremType.DEFINITION,
            DocNodeType.EXAMPLE: TheoremType.EXAMPLE,
            DocNodeType.REMARK: TheoremType.REMARK,
        }

        theorem_type = theorem_type_map.get(node.node_type, TheoremType.THEOREM)

        # Title is from node.title or auto-generate
        title = node.title if node.title else theorem_type.value.title()

        # Number from metadata
        number = node.metadata.get('number')

        return TheoremBox(
            theorem_type=theorem_type,
            title=title,
            content=node.text,
            number=number,
            metadata=node.metadata
        )

    def _convert_proof(self, node: DocNode) -> ProofBox:
        """Convert proof node to ProofBox block."""
        qed_symbol = node.metadata.get('qed_symbol', '□')

        return ProofBox(
            content=node.text,
            qed_symbol=qed_symbol,
            metadata=node.metadata
        )

    def _convert_equation(self, node: DocNode, preserve_omml: bool) -> Equation:
        """Convert equation node to Equation block."""
        # Determine mode (inline vs display)
        # Check if text starts with $$ (display) or $ (inline)
        latex = node.text.strip()

        if latex.startswith('$$') and latex.endswith('$$'):
            mode = EquationMode.DISPLAY
            latex = latex[2:-2].strip()  # Remove $$ delimiters
        elif latex.startswith('$') and latex.endswith('$'):
            mode = EquationMode.INLINE
            latex = latex[1:-1].strip()  # Remove $ delimiters
        else:
            # No delimiters - assume display by default
            mode = EquationMode.DISPLAY

        # Extract equation number
        eq_number = node.metadata.get('equation_number')

        # Preserve OMML if requested
        omml_xml = None
        if preserve_omml and 'omml_xml' in node.metadata:
            omml_xml = node.metadata['omml_xml']

        return Equation(
            latex=latex,
            mode=mode,
            number=eq_number,
            omml_xml=omml_xml,
            metadata=node.metadata
        )

    def _convert_reference(self, node: DocNode) -> ReferenceEntry:
        """Convert reference entry node to ReferenceEntry block."""
        citation_key = node.metadata.get('citation_key')

        return ReferenceEntry(
            citation=node.text,
            key=citation_key,
            metadata=node.metadata
        )


# ============================================================================
# Convenience Functions
# ============================================================================

def build_ast_from_semantic(
    doc_nodes: DocNodeList,
    domain: str = "book",
    layout_mode: str = "book",
    language: str = "vi",
    source_language: str = "en",
    preserve_omml: bool = False
) -> DocumentAST:
    """
    Convenience function to build DocumentAST from semantic nodes.

    Args:
        doc_nodes: List of semantic DocNode objects
        domain: Document domain ("book", "stem", "general")
        layout_mode: Layout mode ("book", "academic", "simple")
        language: Target language
        source_language: Source language
        preserve_omml: Whether to preserve OMML in equations

    Returns:
        DocumentAST ready for rendering

    Example:
        >>> from core.structure.semantic_model import DocNode, DocNodeType
        >>> nodes = [
        ...     DocNode(node_type=DocNodeType.CHAPTER, text="Introduction", level=1),
        ...     DocNode(node_type=DocNodeType.PARAGRAPH, text="This is the first paragraph.")
        ... ]
        >>> ast = build_ast_from_semantic(nodes, domain="book", layout_mode="book")
        >>> print(ast)
        DocumentAST(domain=book, blocks=2, headings=1, equations=0)
    """
    metadata = DocumentMetadata(
        domain=domain,
        layout_mode=layout_mode,
        language=language,
        source_language=source_language
    )

    builder = ASTBuilder()
    return builder.build(doc_nodes, metadata, preserve_omml)


def build_book_ast(doc_nodes: DocNodeList, **kwargs) -> DocumentAST:
    """Build DocumentAST optimized for book translation."""
    return build_ast_from_semantic(
        doc_nodes,
        domain="book",
        layout_mode="book",
        **kwargs
    )


def build_academic_ast(doc_nodes: DocNodeList, **kwargs) -> DocumentAST:
    """Build DocumentAST optimized for academic/STEM documents."""
    return build_ast_from_semantic(
        doc_nodes,
        domain="stem",
        layout_mode="academic",
        preserve_omml=kwargs.pop('preserve_omml', True),  # Default True for STEM
        **kwargs
    )
