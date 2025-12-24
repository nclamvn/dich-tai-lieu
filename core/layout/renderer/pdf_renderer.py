#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Renderer

Renders LayoutIntentPackage to professional PDF.
Uses ReportLab for PDF generation.

Version: 1.0.0
"""

from typing import List, Dict, Optional, Any, Tuple, TYPE_CHECKING
from pathlib import Path
import logging
import os

try:
    from reportlab.lib.pagesizes import A4, A5, LETTER, B5
    from reportlab.lib.units import mm, cm, inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, KeepTogether,
    )
    from reportlab.lib.colors import black, gray, white
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    # Dummy values for type checking
    A4 = A5 = LETTER = B5 = (595, 842)
    mm = cm = inch = 1

from core.contracts import (
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionType,
)
from .base_renderer import BaseRenderer

if TYPE_CHECKING:
    from ..executor.block_flow import FlowedBlock
    from ..sections.manager import SectionManager

logger = logging.getLogger(__name__)


class PDFRenderer(BaseRenderer):
    """
    Renders LayoutIntentPackage to PDF.

    Features:
    - Professional typography
    - Page headers and footers
    - Section-based page numbering
    - Table of contents
    - Print-ready output

    Usage:
        renderer = PDFRenderer(template="book", page_size="A4")
        renderer.render(lip, flowed_blocks, "output.pdf")
    """

    # Page sizes
    PAGE_SIZES: Dict[str, Tuple[float, float]] = {}

    # Template-specific settings
    TEMPLATE_SETTINGS = {
        "book": {
            "margins": {"top": 2.5, "bottom": 2.5, "left": 3, "right": 2},  # in cm
            "font_body": "Helvetica",
            "font_heading": "Helvetica-Bold",
            "font_size_body": 11,
            "line_spacing": 1.5,
        },
        "report": {
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            "font_body": "Helvetica",
            "font_heading": "Helvetica-Bold",
            "font_size_body": 10,
            "line_spacing": 1.3,
        },
        "academic": {
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            "font_body": "Helvetica",
            "font_heading": "Helvetica-Bold",
            "font_size_body": 12,
            "line_spacing": 2.0,
        },
        "default": {
            "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
            "font_body": "Helvetica",
            "font_heading": "Helvetica-Bold",
            "font_size_body": 11,
            "line_spacing": 1.4,
        },
    }

    def __init__(
        self,
        template: str = "default",
        page_size: str = "A4",
        embed_fonts: bool = False,
    ):
        """
        Initialize PDF renderer.

        Args:
            template: Template name
            page_size: Page size
            embed_fonts: Whether to embed custom fonts
        """
        super().__init__(template, page_size)

        if not HAS_REPORTLAB:
            logger.warning("reportlab not installed. PDF rendering will be simulated.")

        # Initialize page sizes if reportlab is available
        if HAS_REPORTLAB:
            self.PAGE_SIZES = {
                "A4": A4,
                "A5": A5,
                "letter": LETTER,
                "B5": B5,
            }
            self.page_dimensions = self.PAGE_SIZES.get(page_size, A4)
        else:
            self.page_dimensions = (595, 842)  # A4 default

        self.settings = self.TEMPLATE_SETTINGS.get(template, self.TEMPLATE_SETTINGS["default"])
        self.embed_fonts = embed_fonts

        # Initialize styles
        self.styles: Dict[str, Any] = {}
        if HAS_REPORTLAB:
            self.styles = self._create_styles()

        logger.info(f"PDFRenderer initialized: {template}, {page_size}")

    def _create_styles(self) -> Dict[str, Any]:
        """Create paragraph styles for different block types"""
        if not HAS_REPORTLAB:
            return {}

        base_styles = getSampleStyleSheet()
        settings = self.settings

        styles: Dict[str, ParagraphStyle] = {}

        # Title style
        styles["Title"] = ParagraphStyle(
            "Title",
            parent=base_styles["Title"],
            fontName=settings["font_heading"],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
        )

        # Subtitle style
        styles["Subtitle"] = ParagraphStyle(
            "Subtitle",
            parent=base_styles["Normal"],
            fontName=settings["font_body"],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=50,
            textColor=gray,
        )

        # Chapter style
        styles["Chapter"] = ParagraphStyle(
            "Chapter",
            parent=base_styles["Heading1"],
            fontName=settings["font_heading"],
            fontSize=20,
            spaceBefore=40,
            spaceAfter=20,
            alignment=TA_LEFT,
        )

        # Section style
        styles["Section"] = ParagraphStyle(
            "Section",
            parent=base_styles["Heading2"],
            fontName=settings["font_heading"],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        )

        # Heading styles
        styles["Heading1"] = ParagraphStyle(
            "Heading1",
            parent=base_styles["Heading1"],
            fontName=settings["font_heading"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
        )

        styles["Heading2"] = ParagraphStyle(
            "Heading2",
            parent=base_styles["Heading2"],
            fontName=settings["font_heading"],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
        )

        styles["Heading3"] = ParagraphStyle(
            "Heading3",
            parent=base_styles["Heading3"],
            fontName=settings["font_heading"],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
        )

        # Body text style
        styles["Body"] = ParagraphStyle(
            "Body",
            parent=base_styles["Normal"],
            fontName=settings["font_body"],
            fontSize=settings["font_size_body"],
            leading=settings["font_size_body"] * settings["line_spacing"],
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=12,
        )

        # Quote style
        styles["Quote"] = ParagraphStyle(
            "Quote",
            parent=styles["Body"],
            leftIndent=30,
            rightIndent=30,
            fontName="Helvetica-Oblique",
        )

        # Code style
        styles["Code"] = ParagraphStyle(
            "Code",
            parent=base_styles["Code"],
            fontName="Courier",
            fontSize=9,
            leading=11,
            leftIndent=20,
            spaceBefore=10,
            spaceAfter=10,
        )

        # TOC styles
        styles["TOC1"] = ParagraphStyle(
            "TOC1",
            parent=base_styles["Normal"],
            fontName=settings["font_heading"],
            fontSize=12,
            leftIndent=0,
            spaceBefore=8,
        )

        styles["TOC2"] = ParagraphStyle(
            "TOC2",
            parent=base_styles["Normal"],
            fontName=settings["font_body"],
            fontSize=11,
            leftIndent=20,
            spaceBefore=4,
        )

        styles["TOC3"] = ParagraphStyle(
            "TOC3",
            parent=base_styles["Normal"],
            fontName=settings["font_body"],
            fontSize=10,
            leftIndent=40,
            spaceBefore=2,
        )

        return styles

    def render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List,
        output_path: str,
        section_manager: Optional[Any] = None,
    ) -> Path:
        """
        Render to PDF file.

        Args:
            lip: LayoutIntentPackage
            flowed_blocks: Flowed blocks from executor
            output_path: Output file path
            section_manager: Optional section manager

        Returns:
            Path to created file
        """
        logger.info(f"Rendering PDF: {len(flowed_blocks)} blocks")

        output_path = Path(output_path)

        if not HAS_REPORTLAB:
            return self._simulate_render(lip, flowed_blocks, output_path)

        # Create document
        margins = self.settings["margins"]
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_dimensions,
            topMargin=margins["top"] * cm,
            bottomMargin=margins["bottom"] * cm,
            leftMargin=margins["left"] * cm,
            rightMargin=margins["right"] * cm,
        )

        # Build story (list of flowables)
        story: List[Any] = []

        # Add title page
        if lip.title:
            story.extend(self._create_title_page(lip))

        # Add TOC if present
        if lip.toc_blocks:
            story.extend(self._create_toc(lip))

        # Track for page breaks
        current_page = 1

        # Render blocks
        for fb in flowed_blocks:
            block = fb.block

            # Handle page breaks
            if fb.page_break_before and fb.page_number > current_page:
                story.append(PageBreak())
                current_page = fb.page_number

            # Render block
            flowable = self._render_block(block)
            if flowable:
                story.append(flowable)

        # Build PDF
        doc.build(
            story,
            onFirstPage=self._create_header_footer(lip, section_manager),
            onLaterPages=self._create_header_footer(lip, section_manager),
        )

        logger.info(f"PDF saved: {output_path}")

        return output_path

    def _simulate_render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List,
        output_path: Path,
    ) -> Path:
        """Simulate render when reportlab not available"""
        # Create a simple text representation
        lines = [
            f"# {lip.title}",
            f"## {lip.subtitle}" if lip.subtitle else "",
            "",
            f"Template: {self.template}",
            f"Page Size: {self.page_size}",
            f"Total Blocks: {len(flowed_blocks)}",
            "",
            "=" * 50,
            "[PDF SIMULATION - ReportLab not installed]",
            "=" * 50,
            "",
        ]

        for fb in flowed_blocks:
            block = fb.block
            lines.append(f"[Page {fb.page_number}] [{block.type.value}] {block.content[:100]}...")

        # Write as text file with .pdf extension (for testing)
        output_path.write_text("\n".join(lines), encoding="utf-8")

        logger.info(f"Simulated PDF saved: {output_path}")

        return output_path

    def _create_title_page(self, lip: LayoutIntentPackage) -> List[Any]:
        """Create title page flowables"""
        if not HAS_REPORTLAB:
            return []

        elements: List[Any] = []

        # Spacer to push title down
        elements.append(Spacer(1, 5 * cm))

        # Title
        elements.append(Paragraph(self._escape_html(lip.title), self.styles["Title"]))

        # Subtitle
        if lip.subtitle:
            elements.append(Paragraph(self._escape_html(lip.subtitle), self.styles["Subtitle"]))

        # Author
        if lip.author:
            elements.append(Spacer(1, 2 * cm))
            elements.append(Paragraph(self._escape_html(lip.author), self.styles["Subtitle"]))

        # Page break after title
        elements.append(PageBreak())

        return elements

    def _create_toc(self, lip: LayoutIntentPackage) -> List[Any]:
        """Create table of contents"""
        if not HAS_REPORTLAB:
            return []

        elements: List[Any] = []

        # TOC heading
        elements.append(Paragraph("Table of Contents", self.styles["Chapter"]))
        elements.append(Spacer(1, 1 * cm))

        # TOC entries
        for block in lip.toc_blocks:
            if block.type == BlockType.TOC_ENTRY:
                # Determine style by level
                if block.level <= 1:
                    style = self.styles["TOC1"]
                elif block.level == 2:
                    style = self.styles["TOC2"]
                else:
                    style = self.styles["TOC3"]

                # Format entry
                text = self._escape_html(block.content)
                if block.number:
                    text = f"{block.number}. {text}"

                elements.append(Paragraph(text, style))

        elements.append(PageBreak())

        return elements

    def _render_block(self, block: Block) -> Optional[Any]:
        """Render a single block to flowable"""
        if not HAS_REPORTLAB:
            return None

        # Map block type to style
        style_map = {
            BlockType.TITLE: "Title",
            BlockType.SUBTITLE: "Subtitle",
            BlockType.CHAPTER: "Chapter",
            BlockType.SECTION: "Section",
            BlockType.HEADING_1: "Heading1",
            BlockType.HEADING_2: "Heading2",
            BlockType.HEADING_3: "Heading3",
            BlockType.PARAGRAPH: "Body",
            BlockType.QUOTE: "Quote",
            BlockType.CODE: "Code",
            BlockType.LIST: "Body",
            BlockType.FOOTNOTE: "Body",
        }

        style_name = style_map.get(block.type, "Body")
        style = self.styles.get(style_name, self.styles["Body"])

        # Escape HTML entities and convert newlines
        content = self._escape_html(block.content)
        content = content.replace("\n", "<br/>")

        return Paragraph(content, style)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _create_header_footer(
        self,
        lip: LayoutIntentPackage,
        section_manager: Optional[Any],
    ):
        """Create header/footer callback function"""
        if not HAS_REPORTLAB:
            return lambda canvas, doc: None

        page_dimensions = self.page_dimensions
        title = lip.title

        def draw_header_footer(canvas, doc):
            canvas.saveState()

            page_width, page_height = page_dimensions

            # Footer with page number
            canvas.setFont("Helvetica", 9)
            page_num = canvas.getPageNumber()

            # Center page number
            canvas.drawCentredString(
                page_width / 2,
                1.5 * cm,
                str(page_num)
            )

            # Optional: Header with title
            if page_num > 1 and title:
                canvas.setFont("Helvetica-Oblique", 9)
                canvas.drawCentredString(
                    page_width / 2,
                    page_height - 1.5 * cm,
                    title[:50]  # Truncate long titles
                )

            canvas.restoreState()

        return draw_header_footer

    @classmethod
    def supports_format(cls, format_name: str) -> bool:
        return format_name.lower() == "pdf"

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        return ["pdf"]
