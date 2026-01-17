"""
Business Report Template
Báo cáo kinh doanh - Professional business documents

Best for: Báo cáo kinh doanh, proposal, quarterly reports
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class BusinessReportTemplate(BaseTemplate):
    """
    Business Report - Báo cáo kinh doanh chuyên nghiệp

    Features:
    - Source Sans Pro / Inter font (professional sans-serif)
    - A4 page size (standard business)
    - Header with optional logo
    - Footer with page numbers and document title
    - Table of Contents
    - Numbered sections (1.1, 1.2, 2.1...)
    - Professional table styling
    - Executive summary box
    - Callout boxes for key metrics
    """

    # Color scheme
    COLORS = {
        "primary": "#1E3A5F",      # Navy blue
        "secondary": "#4A90A4",    # Teal
        "accent": "#E67E22",       # Orange for highlights
        "text": "#333333",
        "text_light": "#666666",
        "bg_light": "#F5F5F5",
        "border": "#DDDDDD",
    }

    @property
    def display_name(self) -> str:
        return "Business Report"

    @property
    def description(self) -> str:
        return "Thiết kế chuyên nghiệp cho báo cáo kinh doanh, proposal và quarterly reports"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["Báo cáo kinh doanh", "Proposal", "Quarterly reports", "Business plans"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A4 (standard business)
                page_size_name="A4",
                page_width_mm=210,
                page_height_mm=297,

                # Margins
                margin_top=25,
                margin_bottom=25,
                margin_inner=25,
                margin_outer=20,

                # Typography
                body_font="SourceSansPro",
                body_size=11,
                line_height=1.4,
                first_line_indent=0,
                paragraph_spacing=8,

                heading_font="SourceSansPro",
                chapter_title_size=18,
                section_title_size=14,
                subsection_title_size=12,

                # Features
                justify_text=True,
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=9,
                ornaments=False,
                section_dividers=True,
                chapter_page_break=False,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for business documents"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.colors import HexColor

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
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=self.config.paragraph_spacing,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "body_first": ParagraphStyle(
                name="BodyFirst",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=self.config.paragraph_spacing,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "h1": ParagraphStyle(
                name="Heading1",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=24,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h3": ParagraphStyle(
                name="Heading3",
                fontName=f"{font}-Bold",
                fontSize=self.config.subsection_title_size,
                leading=self.config.subsection_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=24,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=28,
                leading=34,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "executive_summary": ParagraphStyle(
                name="ExecutiveSummary",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=15,
                rightIndent=15,
                spaceBefore=12,
                spaceAfter=12,
                backColor=HexColor(self.COLORS["bg_light"]),
                borderPadding=12,
            ),
            "callout": ParagraphStyle(
                name="Callout",
                fontName=f"{font}-Bold",
                fontSize=body_size + 2,
                leading=(body_size + 2) * line_height,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["primary"]),
                backColor=HexColor("#E8F4F8"),
                borderPadding=15,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=9,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=font,
                fontSize=9,
                alignment=TA_RIGHT,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "toc_title": ParagraphStyle(
                name="TOCTitle",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_LEFT,
                spaceBefore=20,
                spaceAfter=15,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=11,
                leading=16,
                alignment=TA_LEFT,
            ),
            "table_header": ParagraphStyle(
                name="TableHeader",
                fontName=f"{font}-Bold",
                fontSize=10,
                leading=14,
                alignment=TA_CENTER,
                textColor=HexColor("#FFFFFF"),
            ),
            "table_cell": ParagraphStyle(
                name="TableCell",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
            ),
            "table_cell_number": ParagraphStyle(
                name="TableCellNumber",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_RIGHT,
            ),
            "footnote": ParagraphStyle(
                name="Footnote",
                fontName=font,
                fontSize=8,
                leading=10,
                alignment=TA_LEFT,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
        }

    def get_table_style(self) -> List:
        """Get ReportLab TableStyle for business tables"""
        from reportlab.lib import colors
        from reportlab.lib.colors import HexColor

        return [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(self.COLORS["primary"])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
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
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor(self.COLORS["bg_light"])]),

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(self.COLORS["border"])),
        ]
