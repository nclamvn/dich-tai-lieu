"""
Presentation Template
Bài thuyết trình - Slide-style document layout

Best for: Slide decks, pitch decks, presentation handouts
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class PresentationTemplate(BaseTemplate):
    """
    Presentation - Bài thuyết trình

    Features:
    - Modern sans-serif font (Inter/Source Sans)
    - 16:9 or 4:3 aspect ratio options
    - Large headings
    - Bullet points styled
    - Speaker notes area (optional)
    - Slide numbers
    - Minimal text per slide
    - High contrast
    """

    # Color scheme - modern presentation
    COLORS = {
        "primary": "#1A365D",      # Dark blue
        "secondary": "#3182CE",    # Bright blue
        "accent": "#F6AD55",       # Orange
        "text": "#2D3748",
        "text_light": "#A0AEC0",
        "bg_slide": "#FFFFFF",
        "bg_alt": "#EDF2F7",
    }

    @property
    def display_name(self) -> str:
        return "Presentation"

    @property
    def description(self) -> str:
        return "Định dạng slide deck cho thuyết trình và pitch decks"

    @property
    def font_style(self) -> str:
        return "sans-serif"

    @property
    def best_for(self) -> List[str]:
        return ["Slide decks", "Pitch decks", "Presentation handouts", "Training materials"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - 16:9 aspect ratio (landscape)
                page_size_name="16:9",
                page_width_mm=297,  # A4 landscape width
                page_height_mm=167,  # 16:9 ratio

                # Margins - generous for slides
                margin_top=20,
                margin_bottom=25,
                margin_inner=30,
                margin_outer=30,

                # Typography - large for presentation
                body_font="Inter",
                body_size=14,
                line_height=1.5,
                first_line_indent=0,
                paragraph_spacing=12,

                heading_font="Inter",
                chapter_title_size=32,
                section_title_size=24,
                subsection_title_size=18,

                # Features
                justify_text=False,  # Left-align for slides
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_right",
                running_header=False,
                header_font_size=10,
                ornaments=False,
                section_dividers=False,
                chapter_page_break=True,  # Each slide is a page
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for presentations"""
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
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
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=20,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=16,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "h3": ParagraphStyle(
                name="Heading3",
                fontName=f"{font}-Bold",
                fontSize=self.config.subsection_title_size,
                leading=self.config.subsection_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=20,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.2,
                alignment=TA_LEFT,
                spaceBefore=16,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "slide_title": ParagraphStyle(
                name="SlideTitle",
                fontName=f"{font}-Bold",
                fontSize=32,
                leading=38,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=24,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=42,
                leading=50,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["primary"]),
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=20,
                leading=26,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["secondary"]),
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "bullet": ParagraphStyle(
                name="Bullet",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_LEFT,
                leftIndent=30,
                bulletIndent=15,
                spaceBefore=8,
                spaceAfter=8,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "bullet_sub": ParagraphStyle(
                name="BulletSub",
                fontName=font,
                fontSize=body_size - 2,
                leading=(body_size - 2) * line_height,
                alignment=TA_LEFT,
                leftIndent=50,
                bulletIndent=35,
                spaceBefore=4,
                spaceAfter=4,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "key_point": ParagraphStyle(
                name="KeyPoint",
                fontName=f"{font}-Bold",
                fontSize=18,
                leading=24,
                alignment=TA_CENTER,
                spaceBefore=20,
                spaceAfter=20,
                textColor=HexColor(self.COLORS["secondary"]),
            ),
            "quote": ParagraphStyle(
                name="Quote",
                fontName=f"{font}-Italic",
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                leftIndent=40,
                rightIndent=40,
                spaceBefore=20,
                spaceAfter=12,
                textColor=HexColor(self.COLORS["text"]),
            ),
            "quote_author": ParagraphStyle(
                name="QuoteAuthor",
                fontName=font,
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "callout": ParagraphStyle(
                name="Callout",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                backColor=HexColor(self.COLORS["accent"]),
                textColor=HexColor("#FFFFFF"),
                borderPadding=15,
                spaceBefore=16,
                spaceAfter=16,
            ),
            "stat_number": ParagraphStyle(
                name="StatNumber",
                fontName=f"{font}-Bold",
                fontSize=48,
                leading=56,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["secondary"]),
            ),
            "stat_label": ParagraphStyle(
                name="StatLabel",
                fontName=font,
                fontSize=14,
                leading=18,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["text_light"]),
            ),
            "speaker_notes": ParagraphStyle(
                name="SpeakerNotes",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                textColor=HexColor(self.COLORS["text_light"]),
                backColor=HexColor(self.COLORS["bg_alt"]),
                borderPadding=10,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=10,
                alignment=TA_RIGHT,
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
                fontSize=14,
                leading=20,
                alignment=TA_LEFT,
            ),
            "section_divider": ParagraphStyle(
                name="SectionDivider",
                fontName=f"{font}-Bold",
                fontSize=36,
                leading=44,
                alignment=TA_CENTER,
                textColor=HexColor(self.COLORS["primary"]),
                backColor=HexColor(self.COLORS["bg_alt"]),
            ),
        }
