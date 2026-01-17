"""
Literary Elegant Template
Văn chương sang trọng - Refined literary style

Best for: Thơ, truyện ngắn cao cấp, văn học đương đại
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class LiteraryElegantTemplate(BaseTemplate):
    """
    Literary Elegant - Văn chương sang trọng

    Features:
    - Crimson Pro font (elegant serif)
    - Trade Paperback size (140x215mm)
    - Generous line height (1.7)
    - Decorative chapter openings
    - Running headers with book/chapter title
    """

    @property
    def display_name(self) -> str:
        return "Literary Elegant"

    @property
    def description(self) -> str:
        return "Thiết kế văn chương tinh tế với typography thanh lịch, phù hợp thơ văn"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Thơ", "Truyện ngắn cao cấp", "Văn học đương đại", "Tiểu luận văn học"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - Trade Paperback
                page_size_name="Trade Paperback",
                page_width_mm=140,
                page_height_mm=215,

                # Margins
                margin_top=22,
                margin_bottom=28,
                margin_inner=22,
                margin_outer=18,

                # Typography
                body_font="CrimsonPro",
                body_size=11.5,
                line_height=1.7,
                first_line_indent=18,
                paragraph_spacing=0,

                heading_font="CrimsonPro",
                chapter_title_size=28,
                section_title_size=15,

                # Features
                justify_text=True,
                drop_cap=True,
                drop_cap_lines=2,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=9,
                ornaments=True,
                section_dividers=True,
                chapter_page_break=True,
                chapter_start_recto=True,  # Start on right page
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
                spaceBefore=50,
                spaceAfter=35,
                textColor="#2c2c2c",
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=f"{font}-Italic",
                fontSize=13,
                leading=16,
                alignment=TA_CENTER,
                textColor="#777777",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=24,
                spaceAfter=14,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=36,
                leading=42,
                alignment=TA_CENTER,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=f"{font}-Italic",
                fontSize=15,
                leading=20,
                alignment=TA_CENTER,
                textColor="#555555",
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
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=f"{font}-Italic",
                fontSize=9,
                alignment=TA_CENTER,
                textColor="#888888",
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=11,
                leading=18,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=f"{font}-Italic",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=25,
                rightIndent=25,
                spaceBefore=14,
                spaceAfter=14,
            ),
            "poem": ParagraphStyle(
                name="Poem",
                fontName=f"{font}-Italic",
                fontSize=body_size,
                leading=body_size * 1.8,
                alignment=TA_LEFT,
                leftIndent=40,
                spaceBefore=20,
                spaceAfter=20,
            ),
            "epigraph": ParagraphStyle(
                name="Epigraph",
                fontName=f"{font}-Italic",
                fontSize=10,
                leading=14,
                alignment=TA_CENTER,
                textColor="#666666",
                spaceBefore=30,
                spaceAfter=30,
            ),
        }
