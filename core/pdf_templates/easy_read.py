"""
Easy Read Template
Dễ đọc - Accessibility-focused design

Best for: Sách cho người lớn tuổi, accessibility, giáo dục
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class EasyReadTemplate(BaseTemplate):
    """
    Easy Read - Thiết kế dễ đọc (Accessibility)

    Features:
    - Atkinson Hyperlegible font (designed for low vision)
    - A4 page size (large format)
    - High contrast, clear letterforms
    - Extra spacing between paragraphs
    - Large page numbers
    - Dyslexia-friendly
    """

    @property
    def display_name(self) -> str:
        return "Easy Read"

    @property
    def description(self) -> str:
        return "Thiết kế accessibility với font siêu rõ, tối ưu cho người lớn tuổi và khó đọc"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["Người lớn tuổi", "Accessibility", "Giáo dục", "Tài liệu hướng dẫn"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A4 (large format)
                page_size_name="A4",
                page_width_mm=210,
                page_height_mm=297,

                # Margins - Wide for easy holding
                margin_top=30,
                margin_bottom=30,
                margin_inner=30,
                margin_outer=30,

                # Typography - Large and clear
                body_font="AtkinsonHyperlegible",
                body_size=13,
                line_height=1.8,
                first_line_indent=0,
                paragraph_spacing=12,

                heading_font="AtkinsonHyperlegible",
                chapter_title_size=22,
                section_title_size=16,

                # Features - Accessibility
                justify_text=False,  # Left-aligned is easier for dyslexia
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_center",
                running_header=True,
                header_font_size=11,
                ornaments=False,
                section_dividers=True,
                chapter_page_break=True,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        font = self.config.body_font
        body_size = self.config.body_size
        line_height = self.config.line_height

        return {
            "body": ParagraphStyle(
                name="Body",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=self.config.paragraph_spacing,
            ),
            "body_first": ParagraphStyle(
                name="BodyFirst",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=self.config.paragraph_spacing,
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=40,
                spaceAfter=24,
                textColor="#1a1a1a",
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=f"{font}-Bold",
                fontSize=14,
                leading=18,
                alignment=TA_LEFT,
                textColor="#555555",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=24,
                spaceAfter=16,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=32,
                leading=40,
                alignment=TA_CENTER,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                textColor="#444444",
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=18,
                leading=24,
                alignment=TA_CENTER,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=f"{font}-Bold",
                fontSize=12,
                alignment=TA_CENTER,
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=font,
                fontSize=11,
                alignment=TA_CENTER,
                textColor="#666666",
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=13,
                leading=22,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                leftIndent=25,
                borderLeftWidth=4,
                borderLeftColor="#cccccc",
                borderPadding=12,
                spaceBefore=16,
                spaceAfter=16,
                backColor="#f8f8f8",
            ),
            "important": ParagraphStyle(
                name="Important",
                fontName=f"{font}-Bold",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                backColor="#fff3cd",
                borderWidth=1,
                borderColor="#ffc107",
                borderPadding=12,
                spaceBefore=16,
                spaceAfter=16,
            ),
            "note": ParagraphStyle(
                name="Note",
                fontName=font,
                fontSize=body_size - 1,
                leading=(body_size - 1) * line_height,
                alignment=TA_LEFT,
                backColor="#e8f4f8",
                borderWidth=1,
                borderColor="#17a2b8",
                borderPadding=12,
                spaceBefore=16,
                spaceAfter=16,
            ),
        }
