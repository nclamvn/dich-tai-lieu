"""
Ebook PDF Template - For novels, non-fiction, literary works.

Features:
- Trade paperback size (14 x 21.5 cm)
- DejaVu Serif fonts (full Vietnamese support)
- Elegant chapter openings
- Justified text with first-line indent
- Centered page numbers
- No headers (clean look)
"""

from typing import Dict
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from .base import (
    PdfTemplate, TemplateType, PageSpec, FontSpec, ParagraphSpec,
    HeaderFooterSpec, TocSpec
)


class EbookPdfTemplate(PdfTemplate):
    """
    Professional ebook/novel PDF template.

    Typography: DejaVu Serif (full Vietnamese support)
    Page size: Trade paperback (14 x 21.5 cm)
    Style: Elegant, book-like, easy to read
    """

    # Font family names (as registered in ReportLab)
    SERIF = 'DejaVuSerif'
    MONO = 'DejaVuSansMono'

    # Colors
    CHAPTER_COLOR = HexColor('#2C3E50')  # Dark blue-gray
    TEXT_COLOR = black

    @property
    def name(self) -> str:
        return "Ebook PDF"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.EBOOK

    def get_page_spec(self) -> PageSpec:
        return PageSpec.trade_paperback()

    def get_fonts(self) -> Dict[str, str]:
        """DejaVu Serif family for full Vietnamese support"""
        return {
            'regular': 'DejaVuSerif.ttf',
            'bold': 'DejaVuSerif-Bold.ttf',
            'italic': 'DejaVuSerif-Italic.ttf',
            'bold_italic': 'DejaVuSerif-BoldItalic.ttf',
            'mono': 'DejaVuSansMono.ttf',
            'mono_bold': 'DejaVuSansMono-Bold.ttf',
        }

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        return {
            # ═══════════════════════════════════════════════════════════
            # TITLE PAGE
            # ═══════════════════════════════════════════════════════════

            'title': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=28,
                    leading=34,
                    bold=True,
                    color=self.TEXT_COLOR
                ),
                alignment=TA_CENTER,
                space_before=72,
                space_after=18
            ),

            'subtitle': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=16,
                    leading=20,
                    italic=True,
                    color=HexColor('#555555')
                ),
                alignment=TA_CENTER,
                space_after=36
            ),

            'author': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=14,
                    leading=18
                ),
                alignment=TA_CENTER,
                space_before=48
            ),

            # ═══════════════════════════════════════════════════════════
            # HEADINGS
            # ═══════════════════════════════════════════════════════════

            'heading_1': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=22,
                    leading=28,
                    bold=True,
                    color=self.CHAPTER_COLOR
                ),
                alignment=TA_CENTER,
                space_before=48,
                space_after=24,
                keep_with_next=True
            ),

            'heading_2': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=14,
                    leading=18,
                    bold=True
                ),
                alignment=TA_LEFT,
                space_before=18,
                space_after=9,
                keep_with_next=True
            ),

            'heading_3': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=12,
                    leading=15,
                    bold=True,
                    italic=True
                ),
                alignment=TA_LEFT,
                space_before=12,
                space_after=6,
                keep_with_next=True
            ),

            # ═══════════════════════════════════════════════════════════
            # BODY TEXT
            # ═══════════════════════════════════════════════════════════

            'body': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=16
                ),
                alignment=TA_JUSTIFY,
                first_line_indent=18,  # ~0.5cm
                space_after=0  # No space between paragraphs (book style)
            ),

            'body_first': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=16
                ),
                alignment=TA_JUSTIFY,
                first_line_indent=0,  # No indent for first para
                space_after=0
            ),

            # ═══════════════════════════════════════════════════════════
            # SPECIAL BLOCKS
            # ═══════════════════════════════════════════════════════════

            'quote': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=10,
                    leading=14,
                    italic=True
                ),
                alignment=TA_JUSTIFY,
                left_indent=24,
                right_indent=24,
                space_before=12,
                space_after=12
            ),

            'epigraph': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=10,
                    leading=14,
                    italic=True
                ),
                alignment=TA_CENTER,
                space_before=24,
                space_after=36
            ),

            'code': ParagraphSpec(
                font=FontSpec(
                    family=self.MONO,
                    size=9,
                    leading=12
                ),
                alignment=TA_LEFT,
                left_indent=12,
                space_before=6,
                space_after=6
            ),

            'list_item': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=15
                ),
                alignment=TA_LEFT,
                left_indent=18,
                first_line_indent=-12,  # Hanging indent for bullet
                space_after=3
            ),

            'caption': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=10,
                    leading=13,
                    italic=True
                ),
                alignment=TA_CENTER,
                space_before=6,
                space_after=12
            ),

            # ═══════════════════════════════════════════════════════════
            # TABLE OF CONTENTS
            # ═══════════════════════════════════════════════════════════

            'toc_title': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=22,
                    leading=28,
                    bold=True,
                    color=self.CHAPTER_COLOR
                ),
                alignment=TA_CENTER,
                space_after=24
            ),

            'toc_1': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=12,
                    leading=18,
                    bold=True
                ),
                alignment=TA_LEFT,
                space_before=6,
                space_after=3
            ),

            'toc_2': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=15
                ),
                alignment=TA_LEFT,
                left_indent=18,
                space_after=2
            ),

            'toc_3': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=10,
                    leading=13
                ),
                alignment=TA_LEFT,
                left_indent=36,
                space_after=2
            ),

            # ═══════════════════════════════════════════════════════════
            # GLOSSARY
            # ═══════════════════════════════════════════════════════════

            'glossary_term': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=15,
                    bold=True
                ),
                alignment=TA_LEFT,
                space_before=6
            ),

            'glossary_def': ParagraphSpec(
                font=FontSpec(
                    family=self.SERIF,
                    size=11,
                    leading=15
                ),
                alignment=TA_JUSTIFY,
                left_indent=12,
                space_after=6
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=False,  # Clean look for ebooks
            show_footer=True,

            footer_center="{page}",  # Page number only

            font=FontSpec(
                family=self.SERIF,
                size=10,
                leading=12
            ),

            different_first_page=True,
            header_line=False,
            footer_line=False
        )

    def get_chapter_break(self) -> str:
        return 'page'  # New page for each chapter
