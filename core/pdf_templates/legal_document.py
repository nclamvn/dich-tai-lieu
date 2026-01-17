"""
Legal Document Template
Văn bản pháp lý - Legal contracts and documents

Best for: Hợp đồng, biên bản, văn bản pháp luật
"""

from typing import Dict, List, Optional
from .base_template import BaseTemplate, TemplateConfig


class LegalDocumentTemplate(BaseTemplate):
    """
    Legal Document - Văn bản pháp lý

    Features:
    - Times New Roman / Noto Serif font (legal standard)
    - A4 page size
    - Numbered paragraphs (Article 1, Section 1.1)
    - Line numbers in margin (optional)
    - Signature blocks
    - Witness sections
    - Exhibit/Appendix markers
    - Header with document ID
    - Footer with page/total
    """

    @property
    def display_name(self) -> str:
        return "Legal Document"

    @property
    def description(self) -> str:
        return "Định dạng chuẩn cho hợp đồng, biên bản và văn bản pháp lý"

    @property
    def font_style(self) -> str:
        return "serif"

    @property
    def best_for(self) -> List[str]:
        return ["Hợp đồng", "Biên bản", "Văn bản pháp luật", "Legal contracts"]

    @property
    def config(self) -> TemplateConfig:
        if self._config is None:
            self._config = TemplateConfig(
                # Page Size - A4
                page_size_name="A4",
                page_width_mm=210,
                page_height_mm=297,

                # Margins - wider for legal
                margin_top=25,
                margin_bottom=30,
                margin_inner=30,
                margin_outer=25,

                # Typography
                body_font="NotoSerif",
                body_size=11,
                line_height=1.5,
                first_line_indent=0,
                paragraph_spacing=6,

                heading_font="NotoSerif",
                chapter_title_size=14,
                section_title_size=12,
                subsection_title_size=11,

                # Features
                justify_text=True,
                drop_cap=False,
                page_numbers=True,
                page_number_position="bottom_center",
                running_header=True,
                header_font_size=9,
                ornaments=False,
                section_dividers=False,
                chapter_page_break=False,
            )
        return self._config

    def get_styles(self) -> Dict:
        """Get ReportLab paragraph styles for legal documents"""
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
            ),
            "h1": ParagraphStyle(
                name="Heading1",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.4,
                alignment=TA_CENTER,
                spaceBefore=18,
                spaceAfter=12,
                textTransform="uppercase",
            ),
            "h2": ParagraphStyle(
                name="Heading2",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
            ),
            "h3": ParagraphStyle(
                name="Heading3",
                fontName=f"{font}-Bold",
                fontSize=self.config.subsection_title_size,
                leading=self.config.subsection_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=8,
                spaceAfter=4,
            ),
            "chapter_title": ParagraphStyle(
                name="ChapterTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.chapter_title_size,
                leading=self.config.chapter_title_size * 1.4,
                alignment=TA_CENTER,
                spaceBefore=18,
                spaceAfter=12,
            ),
            "section_title": ParagraphStyle(
                name="SectionTitle",
                fontName=f"{font}-Bold",
                fontSize=self.config.section_title_size,
                leading=self.config.section_title_size * 1.4,
                alignment=TA_LEFT,
                spaceBefore=12,
                spaceAfter=6,
            ),
            "document_title": ParagraphStyle(
                name="DocumentTitle",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=30,
            ),
            "cover_title": ParagraphStyle(
                name="CoverTitle",
                fontName=f"{font}-Bold",
                fontSize=16,
                leading=22,
                alignment=TA_CENTER,
                spaceBefore=40,
                spaceAfter=30,
            ),
            "cover_subtitle": ParagraphStyle(
                name="CoverSubtitle",
                fontName=font,
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
            ),
            "cover_author": ParagraphStyle(
                name="CoverAuthor",
                fontName=font,
                fontSize=11,
                leading=15,
                alignment=TA_CENTER,
            ),
            "article": ParagraphStyle(
                name="Article",
                fontName=f"{font}-Bold",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_CENTER,
                spaceBefore=18,
                spaceAfter=12,
            ),
            "clause": ParagraphStyle(
                name="Clause",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=24,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "subclause": ParagraphStyle(
                name="SubClause",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=48,
                spaceBefore=4,
                spaceAfter=4,
            ),
            "whereas": ParagraphStyle(
                name="Whereas",
                fontName=f"{font}-Italic",
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "signature_block": ParagraphStyle(
                name="SignatureBlock",
                fontName=font,
                fontSize=body_size,
                leading=body_size * 1.8,
                alignment=TA_LEFT,
                spaceBefore=40,
            ),
            "signature_line": ParagraphStyle(
                name="SignatureLine",
                fontName=font,
                fontSize=body_size,
                leading=body_size * 1.2,
                alignment=TA_LEFT,
                borderWidth=0,
            ),
            "witness": ParagraphStyle(
                name="Witness",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=20,
            ),
            "exhibit_title": ParagraphStyle(
                name="ExhibitTitle",
                fontName=f"{font}-Bold",
                fontSize=12,
                leading=16,
                alignment=TA_CENTER,
                spaceBefore=24,
                spaceAfter=12,
            ),
            "page_number": ParagraphStyle(
                name="PageNumber",
                fontName=font,
                fontSize=10,
                alignment=TA_CENTER,
            ),
            "running_header": ParagraphStyle(
                name="RunningHeader",
                fontName=font,
                fontSize=9,
                alignment=TA_CENTER,
                textColor=HexColor("#666666"),
            ),
            "document_id": ParagraphStyle(
                name="DocumentID",
                fontName=font,
                fontSize=9,
                alignment=TA_RIGHT,
                textColor=HexColor("#666666"),
            ),
            "toc_entry": ParagraphStyle(
                name="TOCEntry",
                fontName=font,
                fontSize=11,
                leading=16,
                alignment=TA_LEFT,
            ),
            "definition": ParagraphStyle(
                name="Definition",
                fontName=font,
                fontSize=body_size,
                leading=body_size * line_height,
                alignment=TA_JUSTIFY,
                leftIndent=24,
                firstLineIndent=-24,
                spaceBefore=4,
                spaceAfter=4,
            ),
        }
