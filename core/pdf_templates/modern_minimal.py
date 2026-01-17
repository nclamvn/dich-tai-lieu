"""
Modern Minimal Template
Hiện đại tối giản - Clean contemporary design

Best for: Self-help, phi hư cấu, essays
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class ModernMinimalTemplate(BaseTemplate):
    """
    Modern Minimal - Thiết kế hiện đại tối giản

    Features:
    - Inter/Source Sans Pro font (clean sans-serif)
    - B5 page size
    - Generous whitespace
    - Left-aligned chapter titles
    - Minimal decorations
    """

    @property
    def display_name(self) -> str:
        return "Modern Minimal"

    @property
    def description(self) -> str:
        return "Thiết kế hiện đại, tối giản với font sans-serif và khoảng trắng rộng rãi"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["Self-help", "Phi hư cấu", "Essays", "Sách kinh doanh"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - B5
                page_size_name="B5",
                page_width_mm=176,
                page_height_mm=250,

                # Margins - Equal all sides
                margin_top=25,
                margin_bottom=25,
                margin_inner=25,
                margin_outer=25,

                # Typography
                body_font="Inter",
                body_size=10.5,
                line_height=1.5,
                first_line_indent=0,  # No indent, use paragraph spacing
                paragraph_spacing=8,

                heading_font="Inter",
                chapter_title_size=20,
                section_title_size=14,

                # Features
                justify_text=False,  # Left-aligned for modern look
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=8,
                ornaments=False,
                section_dividers=False,
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
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=60,
                spaceAfter=24,
                textColor="#1a1a1a",
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=font,
                fontSize=11,
                leading=14,
                alignment=TA_LEFT,
                textColor="#888888",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=28,
                leading=34,
                alignment=TA_LEFT,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_LEFT,
                textColor="#666666",
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_LEFT,
                textColor="#333333",
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=9,
                alignment=TA_CENTER,
                textColor="#888888",
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=font,
                fontSize=8,
                alignment=TA_CENTER,
                textColor="#aaaaaa",
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=10,
                leading=16,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                leftIndent=20,
                borderLeftWidth=3,
                borderLeftColor="#e0e0e0",
                borderPadding=10,
                spaceBefore=16,
                spaceAfter=16,
                textColor="#555555",
            ),
        }
