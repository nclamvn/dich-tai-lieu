"""
Phase 2.0.7 - Typography System

Centralized typography definitions for professional academic Word documents.
Provides font sizes, styles, and spacing for all document elements.
"""

from dataclasses import dataclass
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import logging

logger = logging.getLogger(__name__)


@dataclass
class TypographyStyle:
    """Definition for a typography style."""
    font_size: int  # in points
    bold: bool = False
    italic: bool = False
    alignment: int = WD_ALIGN_PARAGRAPH.LEFT  # 0=left, 1=center, 2=right, 3=justify
    space_before: int = 0  # in points
    space_after: int = 0  # in points
    color: RGBColor = None  # None = default (black)


class AcademicTypography:
    """
    Professional academic typography system.

    Defines hierarchy:
    - Title (H0): 18pt, Bold, Center
    - Heading 1: 16pt, Bold, Left
    - Heading 2: 14pt, Bold, Left
    - Heading 3: 12pt, SemiBold, Left
    - Body: 11pt, Normal, Justify
    - Abstract: 11pt, Italic, Justify
    """

    # Font family
    FONT_FAMILY = "Cambria"
    FONT_FAMILY_FALLBACK = "Times New Roman"

    # Style definitions
    STYLES = {
        'title': TypographyStyle(
            font_size=18,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=0,
            space_after=18
        ),

        'subtitle': TypographyStyle(
            font_size=14,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=6,
            space_after=12
        ),

        'author': TypographyStyle(
            font_size=12,
            bold=False,
            italic=True,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=0,
            space_after=12
        ),

        'abstract_label': TypographyStyle(
            font_size=12,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=12,
            space_after=6
        ),

        'abstract_text': TypographyStyle(
            font_size=11,
            bold=False,
            italic=True,
            alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
            space_before=0,
            space_after=12
        ),

        'heading_1': TypographyStyle(
            font_size=16,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=18,
            space_after=12
        ),

        'heading_2': TypographyStyle(
            font_size=14,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=14,
            space_after=8
        ),

        'heading_3': TypographyStyle(
            font_size=12,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=12,
            space_after=6
        ),

        'body': TypographyStyle(
            font_size=11,
            bold=False,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
            space_before=6,
            space_after=6
        ),

        'theorem_label': TypographyStyle(
            font_size=12,
            bold=True,
            italic=False,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=12,
            space_after=6,
            color=RGBColor(70, 130, 180)  # Steel blue
        ),

        'proof_header': TypographyStyle(
            font_size=11,
            bold=False,
            italic=True,
            alignment=WD_ALIGN_PARAGRAPH.LEFT,
            space_before=6,
            space_after=0
        ),

        'quotation': TypographyStyle(
            font_size=11,
            bold=False,
            italic=True,
            alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
            space_before=6,
            space_after=6
        ),
    }

    @classmethod
    def apply_style(cls, paragraph, style_name: str):
        """
        Apply typography style to a paragraph.

        Args:
            paragraph: python-docx Paragraph object
            style_name: Style name from STYLES dict
        """
        if style_name not in cls.STYLES:
            logger.warning(f"Unknown typography style: {style_name}")
            return

        style = cls.STYLES[style_name]

        try:
            # Apply font formatting to all runs
            for run in paragraph.runs:
                run.font.name = cls.FONT_FAMILY
                run.font.size = Pt(style.font_size)
                run.bold = style.bold
                run.italic = style.italic

                if style.color:
                    run.font.color.rgb = style.color

            # If paragraph has no runs, create one
            if not paragraph.runs:
                run = paragraph.add_run()
                run.font.name = cls.FONT_FAMILY
                run.font.size = Pt(style.font_size)
                run.bold = style.bold
                run.italic = style.italic

                if style.color:
                    run.font.color.rgb = style.color

            # Apply paragraph formatting
            paragraph.alignment = style.alignment
            paragraph.paragraph_format.space_before = Pt(style.space_before)
            paragraph.paragraph_format.space_after = Pt(style.space_after)
            paragraph.paragraph_format.line_spacing = 1.15

            logger.debug(f"Applied typography style '{style_name}' to paragraph")

        except Exception as e:
            logger.error(f"Failed to apply typography style '{style_name}': {e}")


class TypographyManager:
    """
    Manages typography application across document.

    Usage:
        manager = TypographyManager()
        manager.apply_to_headings(doc)
        manager.apply_to_body(doc)
    """

    def __init__(self):
        self.typography = AcademicTypography()

    def enhance_heading(self, paragraph, level: int):
        """
        Apply heading typography based on level.

        Args:
            paragraph: Paragraph object
            level: Heading level (1, 2, or 3)
        """
        style_map = {
            1: 'heading_1',
            2: 'heading_2',
            3: 'heading_3',
        }

        style_name = style_map.get(level, 'heading_1')
        self.typography.apply_style(paragraph, style_name)

    def enhance_body_paragraphs(self, doc):
        """
        Apply body typography to all non-special paragraphs.

        Args:
            doc: python-docx Document
        """
        enhanced_count = 0

        for para in doc.paragraphs:
            # Skip empty paragraphs
            if not para.text.strip():
                continue

            # Skip headings
            if para.style.name.startswith('Heading'):
                continue

            # Skip if has special formatting (theorem boxes, etc.)
            if self._has_special_formatting(para):
                continue

            # Apply body typography
            self.typography.apply_style(para, 'body')
            enhanced_count += 1

        logger.info(f"Enhanced typography for {enhanced_count} body paragraphs")
        return enhanced_count

    def _has_special_formatting(self, para) -> bool:
        """Check if paragraph has special formatting."""
        try:
            pPr = para._element.get_or_add_pPr()

            # Check for borders
            if pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr') is not None:
                return True

            # Check for shading
            if pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd') is not None:
                return True

        except Exception:
            pass

        return False
