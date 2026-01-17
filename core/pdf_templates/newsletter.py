"""
Newsletter Template
Bản tin - Magazine and newsletter layouts

Best for: Bản tin công ty, magazine, periodicals
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class NewsletterTemplate(BaseTemplate):
    """
    Newsletter - Bản tin tạp chí

    Features:
    - Open Sans / Source Sans font (friendly, readable)
    - A4 page size
    - Multi-column support (2 columns)
    - Pull quotes
    - Image captions
    - Sidebar boxes
    - Section headers with color
    - Masthead/banner area
    """

    # Color scheme
    COLORS = {
        "primary": "#2C5282",      # Blue
        "secondary": "#48BB78",    # Green
        "accent": "#ED8936",       # Orange
        "text": "#2D3748",
        "text_light": "#718096",
        "bg_light": "#F7FAFC",
        "border": "#E2E8F0",
    }

    @property
    def display_name(self) -> str:
        return "Newsletter"

    @property
    def description(self) -> str:
        return "Thiết kế bắt mắt cho bản tin, tạp chí và nội dung định kỳ"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["Bản tin công ty", "Magazine", "Tạp chí", "Periodicals"]

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
                margin_inner=20,
                margin_outer=20,

                # Typography
                body_font="SourceSansPro",
                body_size=10,
                line_height=1.4,
                first_line_indent=0,
                paragraph_spacing=8,

                heading_font="SourceSansPro",
                chapter_title_size=24,
                section_title_size=16,
                subsection_title_size=12,

                # Features
                justify_text=True,
                drop_cap=True,  # Magazine style
                page_numbers=True,
                page_number_position="bottom_outer",
                running_header=True,
                header_font_size=8,
                ornaments=False,
                section_dividers=True,
                chapter_page_break=False,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for newsletter"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
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
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=16,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h3": ParagraphStyle(
                name="Heading3",
                fontName=f"{font}-Bold",
                fontSize=self.config.subsection_title_size,
                leading=self.config.subsection_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=8,
                spaceAfter=4,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=16,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "masthead": ParagraphStyle(
                name="Masthead",
                fontName=f"{font}-Bold",
                fontSize=36,
                leading=42,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=36,
                leading=42,
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
                fontSize=11,
                leading=15,
                alignment=TA_CENTER,
            ),
            "issue_info": ParagraphStyle(
                name="IssueInfo",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "headline": ParagraphStyle(
                name="Headline",
                fontName=f"{font}-Bold",
                fontSize=20,
                leading=24,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "subheadline": ParagraphStyle(
                name="Subheadline",
                fontName=font,
                fontSize=12,
                leading=16,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "byline": ParagraphStyle(
                name="Byline",
                fontName=f"{font}-Italic",
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "pull_quote": ParagraphStyle(
                name="PullQuote",
                fontName=f"{font}-Bold",
                fontSize=14,
                leading=20,
                alignment=TA_CENTER,
                leftIndent=20,
                rightIndent=20,
                spaceBefore=16,
                spaceAfter=16,
                textColor=HexColor(self.COLORS["primary"]),
                borderWidth=2,
                borderColor=HexColor(self.COLORS["secondary"]),
                borderPadding=15,
            ),
            "sidebar": ParagraphStyle(
                name="Sidebar",
                fontName=font,
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                backColor=HexColor(self.COLORS["bg_light"]),
                borderPadding=10,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "sidebar_title": ParagraphStyle(
                name="SidebarTitle",
                fontName=f"{font}-Bold",
                fontSize=11,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=6,
                textColor=HexColor(self.COLORS["secondary"]),
            ),
            "caption": ParagraphStyle(
                name="Caption",
                fontName=font,
                fontSize=8,
                leading=10,
                alignment=TA_CENTER,
                spaceBefore=4,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "drop_cap": ParagraphStyle(
                name="DropCap",
                fontName=f"{font}-Bold",
                fontSize=36,
                leading=36,
                textColor=HexColor(self.COLORS["primary"]),
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
                fontSize=8,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=10,
                leading=16,
                alignment=TA_LEFT,
            ),
            "callout": ParagraphStyle(
                name="Callout",
                fontName=f"{font}-Bold",
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
                backColor=HexColor(self.COLORS["accent"]),
                textColor=HexColor("#FFFFFF"),
                borderPadding=12,
                spaceBefore=12,
                spaceAfter=12,
            ),
        }
