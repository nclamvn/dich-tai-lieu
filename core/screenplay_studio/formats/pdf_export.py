"""
PDF Screenplay Exporter

Generates professional-looking screenplay PDFs following
industry standard formatting:
- Courier 12pt font
- Proper margins
- Scene headers
- Character/dialogue formatting
"""

import logging
from pathlib import Path
from io import BytesIO

from ..models import Screenplay, Scene, DialogueBlock, ActionBlock

logger = logging.getLogger(__name__)

# Try to import PDF libraries
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.debug("reportlab not installed - PDF export disabled")


class ScreenplayPDFExporter:
    """Export Screenplay to PDF format"""

    # Industry standard margins
    LEFT_MARGIN = 1.5 * 72   # 1.5 inches in points
    RIGHT_MARGIN = 1.0 * 72
    TOP_MARGIN = 1.0 * 72
    BOTTOM_MARGIN = 1.0 * 72

    def __init__(self):
        if not HAS_REPORTLAB:
            raise ImportError(
                "reportlab is required for PDF export. "
                "Install with: pip install reportlab"
            )
        self._setup_styles()

    def _setup_styles(self):
        """Setup paragraph styles for screenplay elements"""
        self.styles = getSampleStyleSheet()

        # Action style (left-aligned)
        self.action_style = ParagraphStyle(
            'Action',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=14,
            leftIndent=0,
            rightIndent=0,
            spaceAfter=12,
        )

        # Scene heading style
        self.heading_style = ParagraphStyle(
            'SceneHeading',
            parent=self.styles['Normal'],
            fontName='Courier-Bold',
            fontSize=12,
            leading=14,
            leftIndent=0,
            spaceAfter=12,
            spaceBefore=24,
        )

        # Character name style
        self.character_style = ParagraphStyle(
            'Character',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=14,
            leftIndent=2.2 * 72,
            spaceAfter=0,
            spaceBefore=12,
        )

        # Parenthetical style
        self.parenthetical_style = ParagraphStyle(
            'Parenthetical',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=14,
            leftIndent=1.6 * 72,
            rightIndent=2.0 * 72,
            spaceAfter=0,
        )

        # Dialogue style
        self.dialogue_style = ParagraphStyle(
            'Dialogue',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=14,
            leftIndent=1.0 * 72,
            rightIndent=1.5 * 72,
            spaceAfter=12,
        )

        # Title style
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Normal'],
            fontName='Courier-Bold',
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=24,
        )

        # Author style
        self.author_style = ParagraphStyle(
            'Author',
            parent=self.styles['Normal'],
            fontName='Courier',
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=12,
        )

    def export(self, screenplay: Screenplay, filepath: str) -> str:
        """Export screenplay to PDF file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            leftMargin=self.LEFT_MARGIN,
            rightMargin=self.RIGHT_MARGIN,
            topMargin=self.TOP_MARGIN,
            bottomMargin=self.BOTTOM_MARGIN,
        )

        elements = []

        # Title page
        elements.extend(self._build_title_page(screenplay))

        # Page break after title
        elements.append(Spacer(1, 4 * 72))

        # Scenes
        for scene in screenplay.scenes:
            elements.extend(self._build_scene(scene))

        # Build PDF
        doc.build(elements)

        logger.info(f"Exported PDF: {filepath}")
        return filepath

    def export_to_bytes(self, screenplay: Screenplay) -> bytes:
        """Export screenplay to PDF bytes"""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=self.LEFT_MARGIN,
            rightMargin=self.RIGHT_MARGIN,
            topMargin=self.TOP_MARGIN,
            bottomMargin=self.BOTTOM_MARGIN,
        )

        elements = []
        elements.extend(self._build_title_page(screenplay))
        elements.append(Spacer(1, 4 * 72))

        for scene in screenplay.scenes:
            elements.extend(self._build_scene(scene))

        doc.build(elements)

        return buffer.getvalue()

    def _build_title_page(self, screenplay: Screenplay) -> list:
        """Build title page elements"""
        elements = []

        elements.append(Spacer(1, 2 * 72))
        elements.append(Paragraph(self._escape_text(screenplay.title.upper()), self.title_style))
        elements.append(Spacer(1, 0.5 * 72))
        elements.append(Paragraph("Written by", self.author_style))
        elements.append(Paragraph(self._escape_text(screenplay.author), self.author_style))

        if screenplay.draft_number > 1:
            elements.append(Spacer(1, 0.5 * 72))
            elements.append(Paragraph(
                f"Draft {screenplay.draft_number}",
                self.author_style
            ))

        return elements

    def _build_scene(self, scene: Scene) -> list:
        """Build scene elements"""
        elements = []

        # Scene heading
        heading_text = self._escape_text(str(scene.heading).upper())
        elements.append(Paragraph(heading_text, self.heading_style))

        # Scene elements
        for element in scene.elements:
            if isinstance(element, ActionBlock):
                text = self._escape_text(element.text)
                elements.append(Paragraph(text, self.action_style))

            elif isinstance(element, DialogueBlock):
                # Character name
                elements.append(Paragraph(
                    self._escape_text(element.character.upper()),
                    self.character_style
                ))

                # Parenthetical
                if element.parenthetical:
                    paren_text = element.parenthetical
                    if not paren_text.startswith("("):
                        paren_text = f"({paren_text})"
                    elements.append(Paragraph(
                        self._escape_text(paren_text),
                        self.parenthetical_style
                    ))

                # Dialogue
                dialogue_text = self._escape_text(element.dialogue)
                elements.append(Paragraph(
                    dialogue_text,
                    self.dialogue_style
                ))

        return elements

    def _escape_text(self, text: str) -> str:
        """Escape special characters for ReportLab"""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text
