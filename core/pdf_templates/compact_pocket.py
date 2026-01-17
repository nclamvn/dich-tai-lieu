"""
Compact Pocket Template
Sách bỏ túi - Pocket-size books

Best for: Light novels, truyện ngắn, sách du lịch
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class CompactPocketTemplate(BaseTemplate):
    """
    Compact Pocket - Sách bỏ túi

    Features:
    - Literata font (optimized for small sizes)
    - A6 page size (pocket)
    - Compact but readable
    - Simple chapter markers
    - Page numbers on outer edge
    """

    @property
    def display_name(self) -> str:
        return "Compact Pocket"

    @property
    def description(self) -> str:
        return "Thiết kế nhỏ gọn, tối ưu cho sách bỏ túi và đọc di động"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Light novels", "Truyện ngắn", "Sách du lịch", "Guidebooks"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A6 (Pocket)
                page_size_name="A6",
                page_width_mm=105,
                page_height_mm=148,

                # Margins - Compact
                margin_top=12,
                margin_bottom=15,
                margin_inner=12,
                margin_outer=10,

                # Typography - Optimized for small size
                body_font="Literata",
                body_size=9.5,
                line_height=1.45,
                first_line_indent=12,
                paragraph_spacing=0,

                heading_font="Literata",
                chapter_title_size=16,
                section_title_size=11,

                # Features
                justify_text=True,
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=False,
                ornaments=False,
                section_dividers=False,
                chapter_page_break=True,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT

        font = self.config.body_font
        body_size = self.config.body_size
        line_height = self.config.line_height

        return {
            "body": ParagraphStyle(
                name="Body",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                firstLineIndent=self.config.first_line_indent,
                spaceBefore=0,
                spaceAfter=0,
            ),
            "body_first": ParagraphStyle(
                name="BodyFirst",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=0,
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_CENTER,
                spaceBefore=20,
                spaceAfter=16,
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=font,
                fontSize=9,
                leading=12,
                alignment=TA_CENTER,
                textColor="#666666",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=8,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=20,
                leading=24,
                alignment=TA_CENTER,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=10,
                leading=13,
                alignment=TA_CENTER,
                textColor="#555555",
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=11,
                leading=14,
                alignment=TA_CENTER,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=8,
                alignment=TA_CENTER,
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=9,
                leading=13,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=f"{font}-Italic",
                fontSize=body_size - 0.5,
                leading=(body_size - 0.5) * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=15,
                rightIndent=15,
                spaceBefore=8,
                spaceAfter=8,
            ),
        }
