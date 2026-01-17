"""
Premium Hardcover Template
Bìa cứng cao cấp - Luxury collector editions

Best for: Collector's editions, sách quà tặng, kinh điển
"""

from typing import Dict, List
from .base_template import BaseTemplate, TemplateConfig


class PremiumHardcoverTemplate(BaseTemplate):
    """
    Premium Hardcover - Bìa cứng cao cấp

    Features:
    - EB Garamond font (classic book font)
    - Royal page size (156x234mm)
    - Generous spacing, luxurious feel
    - Ornate drop caps
    - Decorative page borders
    - Half-title pages
    """

    @property
    def display_name(self) -> str:
        return "Premium Hardcover"

    @property
    def description(self) -> str:
        return "Thiết kế cao cấp cho sách bìa cứng, collector editions với typography sang trọng"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Collector's editions", "Sách quà tặng", "Kinh điển", "Sách nghệ thuật"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - Royal
                page_size_name="Royal",
                page_width_mm=156,
                page_height_mm=234,

                # Margins - Generous
                margin_top=25,
                margin_bottom=35,
                margin_inner=25,
                margin_outer=20,

                # Typography - Luxurious
                body_font="EBGaramond",
                body_size=12,
                line_height=1.8,
                first_line_indent=24,
                paragraph_spacing=0,

                heading_font="EBGaramond",
                chapter_title_size=32,
                section_title_size=18,

                # Features - Full luxury
                justify_text=True,
                drop_cap=True,
                drop_cap_lines=4,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=10,
                ornaments=True,
                section_dividers=True,
                chapter_page_break=True,
                chapter_start_recto=True,
                chapter_drop_lines=5,
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
                spaceBefore=80,
                spaceAfter=50,
                textColor="#1a1a1a",
            ),
            "chapter_number": ParagraphStyle(
                name="ChapterNumber",
                fontName=f"{font}-Italic",
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
                textColor="#666666",
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=30,
                spaceAfter=18,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=42,
                leading=50,
                alignment=TA_CENTER,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=f"{font}-Italic",
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
            "half_title": ParagraphStyle(
                name="HalfTitle",
                fontName=f"{font}-Bold",
                fontSize=28,
                leading=34,
                alignment=TA_CENTER,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=11,
                alignment=TA_CENTER,
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=f"{font}-Italic",
                fontSize=10,
                alignment=TA_CENTER,
                textColor="#777777",
            ),
            "toc_title": ParagraphStyle(
                name="TOCTitle",
                fontName=f"{font}-Bold",
                fontSize=24,
                leading=30,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=30,
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=12,
                leading=20,
                alignment=TA_LEFT,
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=f"{font}-Italic",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=35,
                rightIndent=35,
                spaceBefore=18,
                spaceAfter=18,
            ),
            "dedication": ParagraphStyle(
                name="Dedication",
                fontName=f"{font}-Italic",
                fontSize=14,
                leading=20,
                alignment=TA_CENTER,
                textColor="#555555",
            ),
            "epigraph": ParagraphStyle(
                name="Epigraph",
                fontName=f"{font}-Italic",
                fontSize=11,
                leading=16,
                alignment=TA_CENTER,
                textColor="#666666",
                spaceBefore=40,
                spaceAfter=40,
            ),
        }

    def create_half_title_page(self, title: str) -> List:
        """Create half-title page (first page with just book title)"""
        from reportlab.platypus import Spacer, Paragraph, PageBreak

        styles = self.get_styles()
        elements = []

        # Center title vertically
        elements.append(Spacer(1, 150))
        elements.append(Paragraph(title, styles["half_title"]))
        elements.append(PageBreak())

        return elements
