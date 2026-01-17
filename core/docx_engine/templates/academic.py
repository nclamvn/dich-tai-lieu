"""
Academic Template - For papers, theses, research documents.

Features:
- Times New Roman throughout
- A4 page size
- Footnotes support
- Bibliography section
- Formal heading hierarchy
- Page numbers in footer
"""

from typing import Dict, Optional
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .base import (
    DocxTemplate, TemplateType, PageSetup, ParagraphSpec, FontSpec,
    HeaderFooterSpec, TocSpec
)


class AcademicTemplate(DocxTemplate):
    """
    Academic paper/thesis template.

    Typography: Times New Roman
    Page size: A4
    Style: Formal, structured, citation-ready
    """

    MAIN_FONT = "Times New Roman"

    @property
    def name(self) -> str:
        return "Academic"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.ACADEMIC

    def get_page_setup(self) -> PageSetup:
        return PageSetup.a4()

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        return {
            # Document title
            "title": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(18), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(48),
                space_after=Pt(12),
                line_spacing=1.0
            ),

            # Subtitle / Affiliation
            "subtitle": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_after=Pt(24),
                line_spacing=1.0
            ),

            # Author
            "author": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_after=Pt(6),
                line_spacing=1.0
            ),

            # Abstract title
            "abstract_title": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(24),
                space_after=Pt(12)
            ),

            # Abstract body
            "abstract": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                space_after=Pt(12),
                line_spacing=1.15
                # Indent both sides - handled in renderer
            ),

            # Chapter/Section title (H1)
            "heading_1": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(14), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(24),
                space_after=Pt(12),
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Subsection (H2)
            "heading_2": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(18),
                space_after=Pt(6),
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Sub-subsection (H3)
            "heading_3": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12), bold=True, italic=True),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(12),
                space_after=Pt(6),
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Body text
            "body": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(1.27),  # 0.5 inch standard
                space_after=Pt(0),
                line_spacing=1.5  # Double or 1.5 spacing typical
            ),

            # First paragraph (no indent)
            "body_first": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),
                space_after=Pt(0),
                line_spacing=1.5
            ),

            # Block quote
            "quote": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                space_before=Pt(12),
                space_after=Pt(12),
                line_spacing=1.15
            ),

            # Code
            "code": ParagraphSpec(
                font=FontSpec(name="Courier New", size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(6),
                space_after=Pt(6),
                line_spacing=1.0
            ),

            # Lists
            "list_bullet": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(6),
                line_spacing=1.5
            ),

            "list_numbered": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(6),
                line_spacing=1.5
            ),

            # Footnote
            "footnote": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                space_after=Pt(3),
                line_spacing=1.0
            ),

            # Caption
            "caption": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(6),
                space_after=Pt(12),
                line_spacing=1.0
            ),

            # Bibliography entry
            "bibliography": ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(6),
                line_spacing=1.15
                # Hanging indent - handled in renderer
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=True,
            show_footer=True,
            header_right="{title}",  # Running title
            footer_center="{page}",
            different_first_page=True,
            font=FontSpec(name=self.MAIN_FONT, size=Pt(10))
        )

    def get_toc_spec(self) -> TocSpec:
        return TocSpec(
            title="Table of Contents",
            title_style=ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(14), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_after=Pt(18)
            ),
            level1_style=ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12), bold=True),
                space_before=Pt(6),
                space_after=Pt(3)
            ),
            level2_style=ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(12)),
                space_after=Pt(2)
            ),
            level3_style=ParagraphSpec(
                font=FontSpec(name=self.MAIN_FONT, size=Pt(11)),
                space_after=Pt(2)
            ),
            show_page_numbers=True,
            dot_leader=True
        )

    def get_chapter_break_type(self) -> str:
        return 'page'  # New page for major sections

    def get_custom_style(self, name: str) -> Optional[ParagraphSpec]:
        custom = {
            "equation": ParagraphSpec(
                font=FontSpec(name="Cambria Math", size=Pt(12)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(12),
                space_after=Pt(12)
            ),
        }
        return custom.get(name)
