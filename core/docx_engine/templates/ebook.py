"""
Ebook Template - For novels, non-fiction books, literary works.

Features:
- Elegant serif fonts (Georgia/Garamond)
- Trade paperback size
- Drop caps option
- Chapter page breaks
- Minimal headers
- Centered page numbers
"""

from typing import Dict, Optional
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .base import (
    DocxTemplate, TemplateType, PageSetup, ParagraphSpec, FontSpec,
    HeaderFooterSpec, TocSpec
)


class EbookTemplate(DocxTemplate):
    """
    Professional ebook/novel template.

    Typography: Georgia (body), Cormorant Garamond (headings)
    Page size: Trade paperback (14 x 21.5 cm)
    Style: Elegant, readable, book-like
    """

    # Fonts
    HEADING_FONT = "Cormorant Garamond"  # Elegant serif for titles
    BODY_FONT = "Georgia"                 # Readable serif for body

    # Fallback fonts (if primary not available)
    HEADING_FONT_FALLBACK = "Times New Roman"
    BODY_FONT_FALLBACK = "Times New Roman"

    @property
    def name(self) -> str:
        return "Ebook"

    @property
    def template_type(self) -> TemplateType:
        return TemplateType.EBOOK

    def get_page_setup(self) -> PageSetup:
        return PageSetup.trade_paperback()

    def get_styles(self) -> Dict[str, ParagraphSpec]:
        return {
            # Document title (title page)
            "title": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(32),
                    bold=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(72),
                space_after=Pt(24),
                line_spacing=1.0
            ),

            # Subtitle
            "subtitle": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(18),
                    italic=True,
                    color=RGBColor(80, 80, 80)
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_after=Pt(36),
                line_spacing=1.0
            ),

            # Author name (title page)
            "author": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(14)
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(48),
                line_spacing=1.0
            ),

            # Chapter title (H1)
            "heading_1": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(24),
                    bold=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(72),  # Large space at chapter start
                space_after=Pt(24),
                page_break_before=True,  # New page for each chapter
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Section title (H2)
            "heading_2": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(16),
                    bold=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(24),
                space_after=Pt(12),
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Subsection title (H3)
            "heading_3": ParagraphSpec(
                font=FontSpec(
                    name=self.HEADING_FONT,
                    size=Pt(13),
                    bold=True,
                    italic=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(18),
                space_after=Pt(6),
                keep_with_next=True,
                line_spacing=1.0
            ),

            # Normal body text
            "body": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11)
                ),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0.75),  # First line indent
                space_after=Pt(0),  # No space between paragraphs (book style)
                line_spacing=1.4  # Comfortable reading
            ),

            # First paragraph after heading (no indent - book convention)
            "body_first": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11)
                ),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),  # No indent
                space_after=Pt(0),
                line_spacing=1.4
            ),

            # Block quote
            "quote": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(10),
                    italic=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),
                space_before=Pt(12),
                space_after=Pt(12),
                line_spacing=1.3
                # Note: Left/right indent handled in renderer
            ),

            # Code block
            "code": ParagraphSpec(
                font=FontSpec(
                    name="Consolas",  # Monospace
                    size=Pt(9)
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                first_line_indent=Cm(0),
                space_before=Pt(6),
                space_after=Pt(6),
                line_spacing=1.0
            ),

            # Bullet list
            "list_bullet": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11)
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                first_line_indent=Cm(0),
                space_after=Pt(3),
                line_spacing=1.3
            ),

            # Numbered list
            "list_numbered": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(11)
                ),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                first_line_indent=Cm(0),
                space_after=Pt(3),
                line_spacing=1.3
            ),

            # Footnote
            "footnote": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(9)
                ),
                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
                first_line_indent=Cm(0),
                space_after=Pt(3),
                line_spacing=1.0
            ),

            # Figure/table caption
            "caption": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(10),
                    italic=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(6),
                space_after=Pt(12),
                line_spacing=1.0
            ),

            # Epigraph (chapter opening quote)
            "epigraph": ParagraphSpec(
                font=FontSpec(
                    name=self.BODY_FONT,
                    size=Pt(10),
                    italic=True
                ),
                alignment=WD_ALIGN_PARAGRAPH.RIGHT,
                space_before=Pt(24),
                space_after=Pt(36),
                line_spacing=1.2
            ),
        }

    def get_header_footer(self) -> HeaderFooterSpec:
        return HeaderFooterSpec(
            show_header=True,
            show_footer=True,

            # Header: Book title (even) | Chapter (odd)
            # Simplified: Just book title centered
            header_center="{title}",

            # Footer: Page number centered
            footer_center="{page}",

            # No header/footer on first page (title page)
            different_first_page=True,

            font=FontSpec(name=self.BODY_FONT, size=Pt(9))
        )

    def get_toc_spec(self) -> TocSpec:
        return TocSpec(
            title="Table of Contents",
            title_style=ParagraphSpec(
                font=FontSpec(name=self.HEADING_FONT, size=Pt(24), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_after=Pt(24)
            ),
            level1_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(12), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_before=Pt(6),
                space_after=Pt(3)
            ),
            level2_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(11)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(2)
                # Note: Left indent handled in renderer
            ),
            level3_style=ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(10)),
                alignment=WD_ALIGN_PARAGRAPH.LEFT,
                space_after=Pt(2)
            ),
            show_page_numbers=True,
            dot_leader=True
        )

    def get_chapter_break_type(self) -> str:
        return 'page'  # New page for each chapter

    def get_drop_cap_enabled(self) -> bool:
        return False  # Can enable for more decorative style

    def get_custom_style(self, name: str) -> Optional[ParagraphSpec]:
        """Custom ebook-specific styles"""
        custom_styles = {
            # Part title (Part I, Part II, etc.)
            "part_title": ParagraphSpec(
                font=FontSpec(name=self.HEADING_FONT, size=Pt(36), bold=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(144),
                page_break_before=True
            ),

            # Scene break marker (e.g., * * *)
            "scene_break": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(14)),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(18),
                space_after=Pt(18)
            ),

            # Dedication
            "dedication": ParagraphSpec(
                font=FontSpec(name=self.BODY_FONT, size=Pt(12), italic=True),
                alignment=WD_ALIGN_PARAGRAPH.CENTER,
                space_before=Pt(144)
            ),
        }
        return custom_styles.get(name)
