"""
Academic PDF Template - For papers, theses, research documents.

Features:
- A4 page size
- DejaVu Serif (Times-like)
- 1.5 line spacing
- Running header with title
- Page numbers in footer
- Formal structure
"""

from typing import Dict
from reportlab.lib.colors import black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import cm

from .base import (
    PdfTemplate, TemplateType, PageSpec, FontSpec, ParagraphSpec,
    HeaderFooterSpec
)


class AcademicPdfTemplate(PdfTemplate):
    """
    Academic paper/thesis PDF template.

    Typography: DejaVu Serif
    Page size: A4
    Style: Formal, structured, citation-ready
    """

    SERIF = 'DejaVuSerif'
    MONO = 'DejaVuSansMono'

    @property
    def name(self) -> str:
        return "Academic PDF"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.ACADEMIC

    def get_page_spec(self) -> PageSpec:
        return PageSpec.a4(margins=(2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm))

    def get_fonts(self) -> Dict[str, str]:
        return {
            'regular': 'DejaVuSerif.ttf',
            'bold': 'DejaVuSerif-Bold.ttf',
            'italic': 'DejaVuSerif-Italic.ttf',
            'bold_italic': 'DejaVuSerif-BoldItalic.ttf',
            'mono': 'DejaVuSansMono.ttf',
        }

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        # 1.5 line spacing for body = size 12 with leading 18
        return {
            # Title page
            'title': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=18, leading=24, bold=True),
                alignment=TA_CENTER,
                space_before=36,
                space_after=12
            ),

            'subtitle': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=14, leading=18),
                alignment=TA_CENTER,
                space_after=24
            ),

            'author': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=16),
                alignment=TA_CENTER,
                space_after=6
            ),

            # Abstract
            'abstract_title': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=16, bold=True),
                alignment=TA_CENTER,
                space_before=18,
                space_after=9
            ),

            'abstract': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15),
                alignment=TA_JUSTIFY,
                left_indent=36,
                right_indent=36,
                space_after=18
            ),

            # Headings
            'heading_1': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=14, leading=20, bold=True),
                alignment=TA_LEFT,
                space_before=18,
                space_after=9,
                keep_with_next=True
            ),

            'heading_2': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=16, bold=True),
                alignment=TA_LEFT,
                space_before=12,
                space_after=6,
                keep_with_next=True
            ),

            'heading_3': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=16, bold=True, italic=True),
                alignment=TA_LEFT,
                space_before=9,
                space_after=6,
                keep_with_next=True
            ),

            # Body - 1.5 spacing
            'body': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=18),
                alignment=TA_JUSTIFY,
                first_line_indent=36,  # ~1.27cm standard
                space_after=0
            ),

            'body_first': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=18),
                alignment=TA_JUSTIFY,
                first_line_indent=0,
                space_after=0
            ),

            # Special
            'quote': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15),
                alignment=TA_JUSTIFY,
                left_indent=36,
                right_indent=36,
                space_before=9,
                space_after=9
            ),

            'epigraph': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15, italic=True),
                alignment=TA_CENTER,
                space_before=18,
                space_after=24
            ),

            'code': ParagraphSpec(
                font=FontSpec(family=self.MONO, size=10, leading=13),
                alignment=TA_LEFT,
                left_indent=18,
                space_before=6,
                space_after=6
            ),

            'list_item': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=18),
                alignment=TA_LEFT,
                left_indent=36,
                first_line_indent=-18,
                space_after=3
            ),

            'caption': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=10, leading=13),
                alignment=TA_CENTER,
                space_before=6,
                space_after=12
            ),

            # TOC
            'toc_title': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=14, leading=20, bold=True),
                alignment=TA_CENTER,
                space_after=18
            ),

            'toc_1': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=12, leading=16, bold=True),
                alignment=TA_LEFT,
                space_before=6,
                space_after=3
            ),

            'toc_2': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15),
                alignment=TA_LEFT,
                left_indent=18,
                space_after=2
            ),

            'toc_3': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=10, leading=13),
                alignment=TA_LEFT,
                left_indent=36,
                space_after=2
            ),

            # Bibliography
            'bibliography': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15),
                alignment=TA_JUSTIFY,
                left_indent=36,
                first_line_indent=-36,  # Hanging indent
                space_after=6
            ),

            # Glossary
            'glossary_term': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15, bold=True),
                alignment=TA_LEFT,
                space_before=6
            ),

            'glossary_def': ParagraphSpec(
                font=FontSpec(family=self.SERIF, size=11, leading=15),
                alignment=TA_JUSTIFY,
                left_indent=18,
                space_after=6
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=True,
            show_footer=True,

            header_right="{title}",  # Running title
            footer_center="{page}",

            font=FontSpec(family=self.SERIF, size=10, leading=12),

            different_first_page=True,
            header_line=True,  # Line under header
            footer_line=False
        )

    def get_chapter_break(self) -> str:
        return 'page'  # New page for major sections
