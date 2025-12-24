"""
Phase 2.0.2 - Academic DOCX Builder
====================================

DEPRECATED: This module is maintained for backward compatibility.
New code should use `core.export.docx_academic` instead.

Full implementation for Phase 2.0.2:
- Create DOCX with semantic structure
- Proper styling (headings, bold/italic for theorems/proofs)
- Centered equations (LaTeX text, no OMML conversion yet)
- Global formatting (fonts, spacing)

Phase 2.0.3b: OMML equation rendering
Phase 2.0.5: Professional aesthetic improvements
"""

from dataclasses import dataclass
from typing import List, Optional, Literal
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.structure.semantic_model import DocNode, DocNodeType, DocNodeList
from core.rendering import omml_converter
from core.export.docx_styles import AcademicStyles, StyleApplicator, THEOREM_TYPES
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AcademicLayoutConfig:
    """
    Configuration for academic DOCX layout.

    Phase 2.0.2: Basic configuration implemented.
    Phase 2.0.3b: OMML equation rendering added.
    Phase 2.0.5: Professional styling options added.

    Attributes:
        font_name: Font family for body text
        font_size: Font size in points
        line_spacing: Line spacing multiplier (1.0 = single, 1.5 = 1.5x, 2.0 = double)
        paragraph_spacing_before: Points before paragraph
        paragraph_spacing_after: Points after paragraph
        equation_rendering_mode: Equation rendering mode
            - "latex_text": Render equations as centered LaTeX text (default, backward compatible)
            - "omml": Convert LaTeX to OMML for native Word math rendering (requires pandoc)
        enable_theorem_boxes: Enable bordered boxes around theorems/lemmas/etc (Phase 2.0.5)
        enable_proof_indent: Enable proof block indentation with QED symbols (Phase 2.0.5)
        enable_advanced_equation_layout: Enable enhanced equation spacing and alignment (Phase 2.0.5)
    """
    font_name: str = "Times New Roman"  # Phase 2.0.5: Changed to Times New Roman for Vietnamese compatibility
    font_size: int = 11  # Phase 2.0.5: Changed to 11pt (academic standard)
    line_spacing: float = 1.15  # Phase 2.0.5: Changed to 1.15 (modern academic standard)
    paragraph_spacing_before: int = 6
    paragraph_spacing_after: int = 6
    equation_rendering_mode: Literal["latex_text", "omml"] = "latex_text"  # Phase 2.0.4: Default to backward-compatible LaTeX text

    # Phase 2.0.5: Professional styling features
    enable_theorem_boxes: bool = True  # Bordered boxes around theorems
    enable_proof_indent: bool = True  # Indented proofs with QED
    enable_advanced_equation_layout: bool = True  # Enhanced equation spacing


def build_academic_docx(
    nodes: DocNodeList,
    output_path: str,
    config: Optional[AcademicLayoutConfig] = None,
) -> str:
    """
    Build academic DOCX from semantic node list.

    Phase 2.0.2 implementation:
    - CHAPTER/SECTION/SUBSECTION → heading styles (Heading 1/2/3)
    - THEOREM/LEMMA/etc → bold label + normal text
    - PROOF → italic header + normal text
    - EQUATION_BLOCK → centered paragraph with LaTeX text (no OMML rendering)
    - PARAGRAPH → normal paragraph
    - REFERENCES_SECTION → heading
    - REFERENCE_ENTRY → hanging indent paragraph

    Args:
        nodes: List of DocNode from semantic extractor
        output_path: Output DOCX file path
        config: Optional layout configuration (uses defaults if None)

    Returns:
        str: Absolute path to created DOCX file (Phase 2.0.8)
    """
    # Check equation nodes for LaTeX source
    logger.debug("build_academic_docx() START")
    logger.debug(f"Total nodes: {len(nodes)}")
    equation_nodes = [n for n in nodes if n.is_equation()]
    logger.debug(f"Equation nodes: {len(equation_nodes)}")

    # Check if any equations have latex_source metadata
    enriched_count = sum(1 for n in equation_nodes if n.metadata.get('latex_source'))
    logger.debug(f"Equations with latex_source: {enriched_count}/{len(equation_nodes)}")

    if equation_nodes and enriched_count == 0:
        logger.warning("No equations have latex_source metadata!")
        logger.warning("arXiv enrichment may not have been called!")

    if config is None:
        config = AcademicLayoutConfig()

    doc = Document()

    # Apply global formatting first
    _apply_global_formatting(doc, config)

    # Process each node
    for node in nodes:
        if node.is_heading():
            # Add heading with appropriate level
            level = node.level or 1
            doc.add_heading(node.text, level=level)

        elif node.is_theorem_like():
            # Add theorem block with bold label (Phase 2.0.5: optional box styling)
            _format_theorem_block(doc, node, config)

        elif node.is_proof():
            # Add proof block with italic header (Phase 2.0.5: optional indent + QED)
            _format_proof_block(doc, node, config)

        elif node.is_equation():
            # Add equation block (centered, LaTeX or OMML)
            _format_equation_block(doc, node, config)

        elif node.node_type == DocNodeType.REFERENCES_SECTION:
            # Add references heading
            doc.add_heading(node.text or "References", level=1)

        elif node.node_type == DocNodeType.REFERENCE_ENTRY:
            # Add reference entry with hanging indent
            para = doc.add_paragraph(node.text)
            para.paragraph_format.left_indent = Inches(0.5)
            para.paragraph_format.first_line_indent = Inches(-0.5)

        else:  # PARAGRAPH or UNKNOWN
            # Add normal paragraph
            doc.add_paragraph(node.text)

    # Save
    doc.save(output_path)

    # Phase 2.0.8: Return absolute path for verification
    import os
    return os.path.abspath(output_path)


def _apply_global_formatting(doc: Document, config: AcademicLayoutConfig):
    """
    Apply global formatting to document.

    Sets default font, size, line spacing, and paragraph spacing for Normal style.

    Args:
        doc: python-docx Document object
        config: Layout configuration
    """
    # Get Normal style (base for all paragraphs)
    style = doc.styles['Normal']

    # Set font
    font = style.font
    font.name = config.font_name
    font.size = Pt(config.font_size)

    # Set paragraph formatting
    paragraph_format = style.paragraph_format
    paragraph_format.line_spacing = config.line_spacing
    paragraph_format.space_before = Pt(config.paragraph_spacing_before)
    paragraph_format.space_after = Pt(config.paragraph_spacing_after)


def _format_theorem_block(doc: Document, node: DocNode, config: Optional[AcademicLayoutConfig] = None):
    """
    Format a theorem-like block with bold label and optional box styling.

    Phase 2.0.2: Bold label + normal text
    Phase 2.0.5: Optional bordered box with background color

    Creates paragraph with:
    - Bold label (e.g., "Theorem 1.1. ")
    - Normal text for content
    - Optional: Border and background color (if config.enable_theorem_boxes)

    Args:
        doc: python-docx Document object
        node: DocNode with theorem-like type
        config: Optional layout configuration
    """
    if config is None:
        config = AcademicLayoutConfig()

    para = doc.add_paragraph()

    # Add bold label if present
    if node.title:
        label_run = para.add_run(f"{node.title}. ")
        label_run.bold = True

    # Add theorem text
    # If text starts with the label, strip it to avoid duplication
    text = node.text
    if node.title and text.startswith(node.title):
        # Strip "Theorem 1.1. " from "Theorem 1.1. Content"
        text = text[len(node.title):].lstrip('. ')

    para.add_run(text)

    # Phase 2.0.5: Apply theorem box styling if enabled
    if config.enable_theorem_boxes:
        # Determine theorem type from node type
        box_type = _map_node_type_to_box_type(node.node_type)
        try:
            StyleApplicator.apply_theorem_box(para, box_type)
        except Exception as e:
            logger.warning(f"Failed to apply theorem box styling: {e}")
            # Continue without styling - don't break document generation


def _map_node_type_to_box_type(node_type: DocNodeType) -> str:
    """
    Map DocNodeType to theorem box type for styling.

    Args:
        node_type: DocNodeType enum

    Returns:
        str: Box type ('theorem', 'lemma', 'corollary', etc.)
    """
    mapping = {
        DocNodeType.THEOREM: 'theorem',
        DocNodeType.LEMMA: 'lemma',
        DocNodeType.COROLLARY: 'corollary',
        DocNodeType.PROPOSITION: 'proposition',
        DocNodeType.DEFINITION: 'definition',
        DocNodeType.EXAMPLE: 'example',
    }
    return mapping.get(node_type, 'theorem')  # Default to 'theorem'


def _format_proof_block(doc: Document, node: DocNode, config: Optional[AcademicLayoutConfig] = None):
    """
    Format a proof block with italic header and optional indentation.

    Phase 2.0.2: Italic header + normal text
    Phase 2.0.5: Optional indentation + QED symbol

    Creates paragraph with:
    - Italic "Proof." or "Chứng minh." header
    - Normal text for content
    - Optional: Left indentation (if config.enable_proof_indent)
    - Optional: QED symbol at end (□)

    Args:
        doc: python-docx Document object
        node: DocNode with PROOF type
        config: Optional layout configuration
    """
    if config is None:
        config = AcademicLayoutConfig()

    para = doc.add_paragraph()

    # Determine proof header from node title or detect from text
    if node.title:
        proof_header = node.title
    elif "Chứng minh" in node.text[:20]:
        proof_header = "Chứng minh"
    else:
        proof_header = "Proof"

    # Add italic header
    header_run = para.add_run(f"{proof_header}. ")
    header_run.italic = True

    # Add proof text
    # If text starts with proof header, strip it to avoid duplication
    text = node.text
    if text.startswith(proof_header):
        text = text[len(proof_header):].lstrip('. :')
    elif text.startswith("Proof.") or text.startswith("Proof:"):
        text = text[6:].lstrip('. :')

    # Check if text already has QED marker
    has_qed = any(marker in text for marker in ['□', '■', '∎', 'Q.E.D', 'Đpcm'])

    # Add QED marker if enabled and not present
    if config.enable_proof_indent and not has_qed:
        text = text.rstrip() + "  □"  # Add QED square at end

    para.add_run(text)

    # Phase 2.0.5: Apply proof indentation if enabled
    if config.enable_proof_indent:
        try:
            StyleApplicator.apply_proof_style(para)
        except Exception as e:
            logger.warning(f"Failed to apply proof styling: {e}")
            # Continue without styling - don't break document generation


def _format_equation_block(doc: Document, node: DocNode, config: AcademicLayoutConfig):
    """
    Format an equation block.

    Phase 2.0.2: Center-aligned LaTeX text
    Phase 2.0.3b: Convert LaTeX → OMML if config.equation_rendering_mode == "omml"
    Phase 2.0.5: Enhanced spacing and layout

    Args:
        doc: python-docx Document object
        node: DocNode with EQUATION_BLOCK type
        config: Layout configuration with equation_rendering_mode

    Rendering Logic:
        - If equation_rendering_mode == "omml" AND pandoc available:
            * Try to convert LaTeX to OMML
            * If conversion succeeds: inject OMML into paragraph
            * If conversion fails: fallback to LaTeX text
        - If equation_rendering_mode == "latex_text" OR pandoc unavailable:
            * Render as centered LaTeX text (backward compatible)

    Safety:
        - Never crashes, never loses equations
        - Math correctness > layout > formatting
        - Fallback always preserves original LaTeX text
    """
    # Create centered paragraph
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Phase 2.0.5: Apply enhanced equation spacing if enabled
    if config.enable_advanced_equation_layout:
        try:
            StyleApplicator.apply_equation_style(para, centered=True, numbered=False)
        except Exception as e:
            logger.warning(f"Failed to apply equation styling: {e}")
            # Continue without advanced styling

    # Check if OMML rendering is requested
    if config.equation_rendering_mode == "omml":
        # Check if pandoc is available
        if not omml_converter.is_pandoc_available():
            logger.warning(
                "OMML rendering requested but pandoc not available - "
                "falling back to LaTeX text. Install pandoc for OMML support."
            )
            # Fallback: render as LaTeX text
            para.add_run(node.text)
            return

        # Try to convert LaTeX to OMML
        try:
            # Phase 2.2.0: LaTeX equation splitter for compound blocks
            # If latex_source exists (Phase 2.1.0) but latex_equation_primary doesn't exist,
            # try splitting the compound block
            latex_source_raw = node.metadata.get('latex_source')
            latex_equation_primary = node.metadata.get('latex_equation_primary')

            if latex_source_raw and not latex_equation_primary:
                # Phase 2.2.0: Try to split compound LaTeX block
                try:
                    from core.latex.eq_splitter import split_latex_equations

                    split_result = split_latex_equations(latex_source_raw)

                    if split_result.is_confident and split_result.equation_segments:
                        logger.debug(f"Phase 2.2.0: Successfully split LaTeX into {len(split_result.equation_segments)} equation(s)")

                        # Try to convert each segment
                        # For Phase 2.2.0, we use the first segment (most important equation)
                        # Future: could render multiple equations, but keep it simple for now
                        for eq in split_result.equation_segments[:1]:  # Only first equation for Phase 2.2.0
                            omml_xml = omml_converter.latex_to_omml(eq)

                            if omml_xml:
                                success = omml_converter.inject_omml_as_display(para, omml_xml)

                                if success:
                                    logger.debug(f"Phase 2.2.0: OMML rendering successful for split equation")
                                    return
                                else:
                                    logger.debug(f"Phase 2.2.0: OMML injection failed, trying fallback")
                            else:
                                logger.debug(f"Phase 2.2.0: OMML conversion failed for split equation")

                        # If we reach here, splitting succeeded but OMML conversion failed
                        # Fall through to try the regular path below
                        logger.debug(f"Phase 2.2.0: Split succeeded but OMML failed, using fallback")
                    else:
                        # Not confident or no segments, use regular path
                        logger.debug(f"Phase 2.2.0: Not confident about splitting (reason: {split_result.reason}), using fallback")

                except Exception as e:
                    logger.debug(f"Phase 2.2.0: Splitter error: {e}, using fallback")
                    # Continue to regular path

            # Regular path: Phase 2.1.2 / 2.1.0 / fallback
            # This gives us clean, isolated equations from compound LaTeX blocks
            latex_content = (
                node.metadata.get('latex_equation_primary') or  # Phase 2.1.2: Clean single equation
                node.metadata.get('latex_source') or             # Phase 2.1.0: Fallback to compound block
                node.text or                                     # Last resort: PDF text
                ""
            )

            if node.metadata.get('latex_equation_primary'):
                logger.debug(f"✅ Phase 2.1.2: Using primary equation (length: {len(latex_content)})")
            elif node.metadata.get('latex_source'):
                logger.debug(f"⚠️  Phase 2.1.0: Using compound LaTeX source (length: {len(latex_content)})")

            # Convert to OMML
            omml_xml = omml_converter.latex_to_omml(latex_content)

            if omml_xml:
                # Phase 2.1.1: Use DISPLAY MODE (fixes equations split into multiple lines)
                # Successfully converted - inject OMML as display mode equation
                success = omml_converter.inject_omml_as_display(para, omml_xml)

                if success:
                    logger.debug(f"OMML display mode rendering successful for equation: {latex_content[:50]}...")
                    return
                else:
                    logger.warning(f"OMML display injection failed for: {latex_content[:50]}... - falling back to LaTeX text")
            else:
                logger.debug(f"OMML conversion returned None for: {latex_content[:50]}... - falling back to LaTeX text")

        except Exception as e:
            logger.error(f"Unexpected error in OMML rendering: {e} - falling back to LaTeX text")

        # Fallback: render as LaTeX text
        para.add_run(node.text)

    else:
        # Default: render as LaTeX text (backward compatible)
        para.add_run(node.text)
