"""
Business Template - For reports, proposals, presentations.

Features:
- Clean sans-serif fonts (Calibri)
- A4 page size with narrow margins
- Logo header support
- Executive summary box
- Professional tables
- Page numbers
"""

from typing import Dict, Optional
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .base import (
    DocxTemplate, TemplateType, PageSetup, ParagraphSpec, FontSpec,
    HeaderFooterSpec, TocSpec
)


class BusinessTemplate(DocxTemplate):
    """
    Business report template.

    Typography: Calibri
    Page size: A4 with narrow margins
    Style: Clean, professional, corporate
    """

    HEADING_FONT = "Calibri Light"
    BODY_FONT = "Calibri"
    ACCENT_COLOR = RGBColor(0, 112, 192)  # Professional blue

    @property
    def name(self) -> str:
        return "Business"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.BUSINESS

    def get_page_setup(self) -> PageSetup:
        # A4 with narrow margins for more content
        return PageSetup(
            width=Cm(21), height=Cm(29.7),
            top_margin=Cm(2), bottom_margin=Cm(2),
            left_margin=Cm(2), right_margin=Cm(2)
        )

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        return {
            # Document title
            "title": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(28),
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(36),
                space_after=Pt(12),
                line_spacing=1.0
            ),

            # Subtitle
            "subtitle": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(14),
                    color=RGBColor(89, 89, 89)
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(24),
                line_spacing=1.0
            ),

            # Author/Date
            "author": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(6)
            ),

            # Section heading (H1)
            "heading_1": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(18),
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(24),
                space_after=Pt(12),
                keep_with_next=True,
                page_break_before=False  # No page break in business docs
            ),

            # Subsection (H2)
            "heading_2": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(14),
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(18),
                space_after=Pt(6),
                keep_with_next=True
            ),

            # Sub-subsection (H3)
            "heading_3": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(12),
                    bold=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(12),
                space_after=Pt(6),
                keep_with_next=True
            ),

            # Body
            "body": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),  # No indent in business docs
                space_after=Pt(8),
                line_spacing=1.15
            ),

            # First para (same as body for business)
            "body_first": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),
                space_after=Pt(8),
                line_spacing=1.15
            ),

            # Quote / Callout
            "quote": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11),
                    italic=True,
                    color=RGBColor(89, 89, 89)
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(12),
                space_after=Pt(12),
                line_spacing=1.15
            ),

            # Code
            "code": ParagraphSpec(
                font=FontSpec(name="Consolas", size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(6),
                space_after=Pt(6),
                line_spacing=1.0
            ),

            # Lists
            "list_bullet": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(4),
                line_spacing=1.15
            ),

            "list_numbered": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(4),
                line_spacing=1.15
            ),

            # Footnote
            "footnote": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(9)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(3),
                line_spacing=1.0
            ),

            # Caption
            "caption": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(10),
                    italic=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(6),
                space_after=Pt(12)
            ),

            # Table header
            "table_header": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11),
                    bold=True,
                    color=RGBColor(255, 255, 255)
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER
            ),

            # Table cell
            "table_cell": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                line_spacing=1.0
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=True,
            show_footer=True,
            header_left="{title}",
            header_right="{date}",
            footer_right="Page {page}",
            different_first_page=True,
            font=FontSpec(name=self.BODY_FONT, size=Pt(9))
        )

    def get_toc_spec(self) -> TocSpec:
        return TocSpec(
            title="Table of Contents",
            title_style=ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(18),
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                space_after=Pt(18)
            ),
            level1_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(12), bold=True),
                space_before=Pt(6),
                space_after=Pt(3)
            ),
            level2_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                space_after=Pt(2)
            ),
            level3_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(10)),
                space_after=Pt(2)
            ),
            show_page_numbers=True,
            dot_leader=True
        )

    def get_chapter_break_type(self) -> str:
        return 'none'  # No breaks between sections

    def get_custom_style(self, name: str) -> Optional[ParagraphSpec]:
        custom = {
            # Executive summary box
            "executive_summary": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(12),
                space_after=Pt(12),
                line_spacing=1.15
                # Box border handled in renderer
            ),

            # Key metric / KPI
            "metric": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(36),
                    bold=True,
                    color=self.ACCENT_COLOR
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER
            ),

            "metric_label": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER
            ),
        }
        return custom.get(name)
