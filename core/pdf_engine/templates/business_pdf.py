"""
Business PDF Template - For reports, proposals, presentations.

Features:
- A4 with narrow margins
- Sans-serif font (DejaVu Sans)
- Blue accent color
- Clean tables
- Company header support
"""

from typing import Dict
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4

from .base import (
    PdfTemplate, TemplateType, PageSpec, FontSpec, ParagraphSpec,
    HeaderFooterSpec
)


class BusinessPdfTemplate(PdfTemplate):
    """
    Business report PDF template.

    Typography: DejaVu Sans
    Page size: A4 with narrow margins
    Style: Clean, professional, corporate
    """

    SANS = 'DejaVuSans'
    MONO = 'DejaVuSansMono'

    # Colors
    ACCENT_COLOR = HexColor('#0070C0')  # Professional blue
    HEADING_COLOR = HexColor('#1F4E79')  # Darker blue
    TEXT_COLOR = HexColor('#333333')

    @property
    def name(self) -> str:
        return "Business PDF"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.BUSINESS

    def get_page_spec(self) -> PageSpec:
        # A4 with narrower margins for more content
        return PageSpec(
            width=A4[0],  # A4 width in points
            height=A4[1],  # A4 height in points
            top_margin=2*cm,
            right_margin=1.5*cm,
            bottom_margin=2*cm,
            left_margin=1.5*cm
        )

    def get_fonts(self) -> Dict[str, str]:
        return {
            'regular': 'DejaVuSans.ttf',
            'bold': 'DejaVuSans-Bold.ttf',
            'italic': 'DejaVuSans-Oblique.ttf',
            'bold_italic': 'DejaVuSans-BoldOblique.ttf',
            'mono': 'DejaVuSansMono.ttf',
        }

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        return {
            # Title page
            'title': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=24,
                    leading=30,
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=TA_LEFT,
                space_before=24,
                space_after=12
            ),

            'subtitle': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=14,
                    leading=18,
                    color=self.TEXT_COLOR
                ),
                alignment=TA_LEFT,
                space_after=24
            ),

            'author': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=11, leading=14),
                alignment=TA_LEFT,
                space_after=6
            ),

            # Headings
            'heading_1': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=16,
                    leading=22,
                    bold=True,
                    color=self.HEADING_COLOR
                ),
                alignment=TA_LEFT,
                space_before=18,
                space_after=9,
                keep_with_next=True
            ),

            'heading_2': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=13,
                    leading=18,
                    bold=True,
                    color=self.HEADING_COLOR
                ),
                alignment=TA_LEFT,
                space_before=12,
                space_after=6,
                keep_with_next=True
            ),

            'heading_3': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=11,
                    leading=15,
                    bold=True,
                    color=self.TEXT_COLOR
                ),
                alignment=TA_LEFT,
                space_before=9,
                space_after=6,
                keep_with_next=True
            ),

            # Body - no first-line indent for business
            'body': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=11,
                    leading=15,
                    color=self.TEXT_COLOR
                ),
                alignment=TA_JUSTIFY,
                first_line_indent=0,
                space_after=9
            ),

            'body_first': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=11,
                    leading=15,
                    color=self.TEXT_COLOR
                ),
                alignment=TA_JUSTIFY,
                first_line_indent=0,
                space_after=9
            ),

            # Special
            'quote': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=10,
                    leading=14,
                    italic=True,
                    color=HexColor('#666666')
                ),
                alignment=TA_LEFT,
                left_indent=18,
                space_before=9,
                space_after=9
            ),

            'epigraph': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=10,
                    leading=14,
                    italic=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=TA_CENTER,
                space_before=18,
                space_after=24
            ),

            'callout': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=11,
                    leading=15,
                    color=self.ACCENT_COLOR
                ),
                alignment=TA_LEFT,
                left_indent=12,
                space_before=9,
                space_after=9
            ),

            'code': ParagraphSpec(
                font=FontSpec(family=self.MONO, size=9, leading=12),
                alignment=TA_LEFT,
                left_indent=12,
                space_before=6,
                space_after=6
            ),

            'list_item': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=11, leading=15),
                alignment=TA_LEFT,
                left_indent=18,
                first_line_indent=-12,
                space_after=3
            ),

            'caption': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=10,
                    leading=13,
                    italic=True
                ),
                alignment=TA_CENTER,
                space_before=6,
                space_after=12
            ),

            # TOC
            'toc_title': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=16,
                    leading=22,
                    bold=True,
                    color=self.HEADING_COLOR
                ),
                alignment=TA_LEFT,
                space_after=18
            ),

            'toc_1': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=11, leading=16, bold=True),
                alignment=TA_LEFT,
                space_before=6,
                space_after=3
            ),

            'toc_2': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=10, leading=14),
                alignment=TA_LEFT,
                left_indent=18,
                space_after=2
            ),

            'toc_3': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=9, leading=12),
                alignment=TA_LEFT,
                left_indent=36,
                space_after=2
            ),

            # Glossary
            'glossary_term': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=10, leading=14, bold=True),
                alignment=TA_LEFT,
                space_before=6
            ),

            'glossary_def': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=10, leading=14),
                alignment=TA_LEFT,
                left_indent=12,
                space_after=6
            ),

            # Table styles
            'table_header': ParagraphSpec(
                font=FontSpec(
                    family=self.SANS,
                    size=10,
                    leading=13,
                    bold=True,
                    color=white
                ),
                alignment=TA_CENTER
            ),

            'table_cell': ParagraphSpec(
                font=FontSpec(family=self.SANS, size=9, leading=12),
                alignment=TA_LEFT
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=True,
            show_footer=True,

            header_left="{title}",
            header_right="{date}",

            footer_right="Trang {page}",

            font=FontSpec(
                family=self.SANS,
                size=9,
                leading=11,
                color=self.TEXT_COLOR
            ),

            different_first_page=True,
            header_line=True,
            footer_line=False
        )

    def get_chapter_break(self) -> str:
        return 'none'  # No page breaks in business reports
