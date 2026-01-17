"""
Classic Serif Template
Cổ điển trang nhã - Traditional book design

Best for: Tiểu thuyết, văn học kinh điển, hồi ký
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class ClassicSerifTemplate(BaseTemplate):
    """
    Classic Serif - Thiết kế sách truyền thống

    Features:
    - Noto Serif font (excellent Vietnamese support)
    - A5 page size (standard book)
    - Drop caps for chapter openings
    - Ornamental dividers
    - Centered page numbers
    """

    @property
    def display_name(self) -> str:
        return "Classic Serif"

    @property
    def description(self) -> str:
        return "Thiết kế sách truyền thống với font có chân, dễ đọc cho văn bản dài"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Tiểu thuyết", "Văn học kinh điển", "Hồi ký", "Truyện dài"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A5 (standard book)
                page_size_name="A5",
                page_width_mm=148,
                page_height_mm=210,

                # Margins
                margin_top=20,
                margin_bottom=25,
                margin_inner=20,
                margin_outer=15,

                # Typography
                body_font="NotoSerif",
                body_size=11,
                line_height=1.6,
                first_line_indent=20,
                paragraph_spacing=0,

                heading_font="NotoSerif",
                chapter_title_size=24,
                section_title_size=16,

                # Features
                justify_text=True,
                drop_cap=True,
                drop_cap_lines=3,
                page_numbers=True,
                page_number_position="bottom_center",
                running_header=False,
                ornaments=True,
                section_dividers=True,
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
                firstLineIndent=0,  # No indent for first paragraph
                spaceBefore=0,
                spaceAfter=0,
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.3,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=30,
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=font,
                fontSize=12,
                leading=14,
                alignment=TA_CENTER,
                textColor="#666666",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=20,
                spaceAfter=12,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=32,
                leading=38,
                alignment=TA_CENTER,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=f"{font}-Italic",
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
                textColor="#444444",
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=10,
                alignment=TA_CENTER,
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=11,
                leading=16,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=f"{font}-Italic",
                fontSize=body_size - 1,
                leading=(body_size - 1) * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=30,
                rightIndent=30,
                spaceBefore=12,
                spaceAfter=12,
            ),
        }
