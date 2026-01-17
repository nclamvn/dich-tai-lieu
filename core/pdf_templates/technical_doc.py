"""
Technical Documentation Template
Tài liệu kỹ thuật - Technical manuals and guides

Best for: User manuals, API docs, technical guides
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class TechnicalDocTemplate(BaseTemplate):
    """
    Technical Documentation - Tài liệu kỹ thuật

    Features:
    - Inter / Roboto font (modern sans-serif)
    - JetBrains Mono for code blocks
    - A4 or Letter page size
    - Code blocks with syntax highlighting colors
    - Warning/Info/Tip boxes
    - Step-by-step numbered instructions
    - API endpoint tables
    - Version info in header
    """

    # Color scheme for boxes
    COLORS = {
        "text": "#333333",
        "text_light": "#666666",
        "code_bg": "#F5F5F5",
        "code_border": "#E0E0E0",
        "warning_bg": "#FFF3CD",
        "warning_border": "#FFE69C",
        "warning_text": "#856404",
        "info_bg": "#D1ECF1",
        "info_border": "#BEE5EB",
        "info_text": "#0C5460",
        "tip_bg": "#D4EDDA",
        "tip_border": "#C3E6CB",
        "tip_text": "#155724",
        "danger_bg": "#F8D7DA",
        "danger_border": "#F5C6CB",
        "danger_text": "#721C24",
    }

    @property
    def display_name(self) -> str:
        return "Technical Documentation"

    @property
    def description(self) -> str:
        return "Thiết kế cho tài liệu kỹ thuật, user manuals và API documentation"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["User manuals", "API documentation", "Technical guides", "Developer docs"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A4
                page_size_name="A4",
                page_width_mm=210,
                page_height_mm=297,

                # Margins
                margin_top=20,
                margin_bottom=20,
                margin_inner=25,
                margin_outer=20,

                # Typography
                body_font="Inter",
                body_size=10,
                line_height=1.4,
                first_line_indent=0,
                paragraph_spacing=8,

                heading_font="Inter",
                chapter_title_size=18,
                section_title_size=14,
                subsection_title_size=12,

                # Features
                justify_text=False,  # Left-aligned for technical docs
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=9,
                ornaments=False,
                section_dividers=True,
                chapter_page_break=True,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for technical documentation"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib.colors import HexColor

        font = self.config.body_font
        code_font = "JetBrainsMono"  # Fallback to Courier if not available
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
                textColor=HexColor(self.COLORS["text"]),
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
                textColor=HexColor(self.COLORS["text"]),
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["text"]),
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
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.3,
                alignment=TA_LEFT,
                spaceBefore=18,
                spaceAfter=8,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=24,
                leading=30,
                alignment=TA_LEFT,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_LEFT,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=11,
                leading=15,
                alignment=TA_LEFT,
            ),
            "code": ParagraphStyle(
                name="Code",
                fontName="Courier",  # Fallback, should use JetBrainsMono
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["code_bg"]),
                borderWidth=1,
                borderColor=HexColor(self.COLORS["code_border"]),
                borderPadding=10,
                spaceBefore=8,
                spaceAfter=8,
            ),
            "code_inline": ParagraphStyle(
                name="CodeInline",
                fontName="Courier",
                fontSize=9,
                backColor=HexColor(self.COLORS["code_bg"]),
                borderPadding=2,
            ),
            "warning": ParagraphStyle(
                name="Warning",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["warning_bg"]),
                borderWidth=1,
                borderColor=HexColor(self.COLORS["warning_border"]),
                borderPadding=12,
                textColor=HexColor(self.COLORS["warning_text"]),
                spaceBefore=12,
                spaceAfter=12,
            ),
            "info": ParagraphStyle(
                name="Info",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["info_bg"]),
                borderWidth=1,
                borderColor=HexColor(self.COLORS["info_border"]),
                borderPadding=12,
                textColor=HexColor(self.COLORS["info_text"]),
                spaceBefore=12,
                spaceAfter=12,
            ),
            "tip": ParagraphStyle(
                name="Tip",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["tip_bg"]),
                borderWidth=1,
                borderColor=HexColor(self.COLORS["tip_border"]),
                borderPadding=12,
                textColor=HexColor(self.COLORS["tip_text"]),
                spaceBefore=12,
                spaceAfter=12,
            ),
            "danger": ParagraphStyle(
                name="Danger",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["danger_bg"]),
                borderWidth=1,
                borderColor=HexColor(self.COLORS["danger_border"]),
                borderPadding=12,
                textColor=HexColor(self.COLORS["danger_text"]),
                spaceBefore=12,
                spaceAfter=12,
            ),
            "step_number": ParagraphStyle(
                name="StepNumber",
                fontName=f"{font}-Bold",
                fontSize=body_size + 2,
                leading=(body_size + 2) * line_height,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=4,
            ),
            "step_content": ParagraphStyle(
                name="StepContent",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                leftIndent=24,
                spaceAfter=8,
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
                alignment=TA_LEFT,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=10,
                leading=16,
                alignment=TA_LEFT,
            ),
            "api_endpoint": ParagraphStyle(
                name="APIEndpoint",
                fontName="Courier",
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                backColor=HexColor("#E8F4F8"),
                borderPadding=8,
                spaceBefore=8,
                spaceAfter=8,
            ),
        }
