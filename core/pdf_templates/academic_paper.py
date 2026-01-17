"""
Academic Paper Template
Bài nghiên cứu - Academic and scholarly documents

Best for: Bài nghiên cứu, luận văn, journal articles
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class AcademicPaperTemplate(BaseTemplate):
    """
    Academic Paper - Bài nghiên cứu học thuật

    Features:
    - Times New Roman / Noto Serif font (academic standard)
    - A4 page size
    - Double-spaced (configurable)
    - Title page with abstract
    - Running header with shortened title
    - Page numbers top-right
    - Footnotes/endnotes support
    - Bibliography/References section
    - Figure and Table captions
    - Equations with numbering
    - Block quotes indented
    """

    @property
    def display_name(self) -> str:
        return "Academic Paper"

    @property
    def description(self) -> str:
        return "Thiết kế học thuật chuẩn cho bài nghiên cứu, luận văn và journal articles"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Bài nghiên cứu", "Luận văn", "Journal articles", "Thesis"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A4
                page_size_name="A4",
                page_width_mm=210,
                page_height_mm=297,

                # Margins - wider for binding
                margin_top=25,
                margin_bottom=25,
                margin_inner=30,
                margin_outer=25,

                # Typography - Academic standard
                body_font="NotoSerif",
                body_size=12,
                line_height=2.0,  # Double-spaced
                first_line_indent=36,  # 0.5 inch
                paragraph_spacing=0,

                heading_font="NotoSerif",
                chapter_title_size=14,
                section_title_size=12,
                subsection_title_size=12,

                # Features
                justify_text=True,
                drop_cap=False,
                page_numbers=True,
                page_number_position="top_outer",
                running_header=True,
                header_font_size=10,
                ornaments=False,
                section_dividers=False,
                chapter_page_break=True,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for academic papers"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT

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
            "h1": ParagraphStyle(
                name="Heading1",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * line_height,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=6,
            ),
            "h3": ParagraphStyle(
                name="Heading3",
                fontName=f"{font}-BoldItalic",
                fontSize=self.config.subsection_title_size,
                leading=self.config.subsection_title_size * line_height,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * line_height,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=6,
            ),
            "title": ParagraphStyle(
                name="Title",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=24,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=24,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=12,
                leading=body_size * line_height,
                alignment=TA_CENTER,
            ),
            "abstract_title": ParagraphStyle(
                name="AbstractTitle",
                fontName=f"{font}-Bold",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "abstract": ParagraphStyle(
                name="Abstract",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=36,
                rightIndent=36,
                spaceBefore=0,
                spaceAfter=12,
            ),
            "keywords": ParagraphStyle(
                name="Keywords",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                leftIndent=36,
                rightIndent=36,
            ),
            "block_quote": ParagraphStyle(
                name="BlockQuote",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=72,  # 1 inch indent
                rightIndent=0,
                spaceBefore=12,
                spaceAfter=12,
            ),
            "figure_caption": ParagraphStyle(
                name="FigureCaption",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER,
                spaceBefore=6,
                spaceAfter=12,
            ),
            "table_caption": ParagraphStyle(
                name="TableCaption",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
            ),
            "table_note": ParagraphStyle(
                name="TableNote",
                fontName=font,
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                spaceBefore=3,
            ),
            "equation": ParagraphStyle(
                name="Equation",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=12,
                spaceAfter=12,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=10,
                alignment=TA_RIGHT,
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=font,
                fontSize=10,
                alignment=TA_LEFT,
            ),
            "bibliography_title": ParagraphStyle(
                name="BibliographyTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "bibliography_entry": ParagraphStyle(
                name="BibliographyEntry",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=36,
                firstLineIndent=-36,  # Hanging indent
                spaceBefore=0,
                spaceAfter=12,
            ),
            "footnote": ParagraphStyle(
                name="Footnote",
                fontName=font,
                fontSize=10,
                leading=12,
                alignment=TA_JUSTIFY,
                firstLineIndent=18,
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=12,
                leading=body_size * line_height,
                alignment=TA_LEFT,
            ),
        }

    def get_table_style(self) -> List:
        """Get ReportLab TableStyle for academic tables (APA style)"""
        from reportlab.lib import colors

        return [
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), f"{self.config.body_font}-Bold"),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), self.config.body_font),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),

            # APA style: top and bottom lines only
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ]
