"""
PDF Screenplay Exporter

Generates professional-looking screenplay PDFs following
industry standard formatting:
- Monospace Unicode font (supports Vietnamese diacriticals)
- Proper margins
- Scene headers with scene numbers
- Character/dialogue formatting
- Transitions (CUT TO, FADE IN/OUT)
"""

import logging
import platform
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
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
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

    # Font search paths by platform
    _FONT_CANDIDATES = [
        # DejaVu Sans Mono — widely available, full Unicode
        ("DejaVuSansMono", [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
            "/usr/local/share/fonts/DejaVuSansMono.ttf",
            "/Library/Fonts/DejaVuSansMono.ttf",
            "C:/Windows/Fonts/DejaVuSansMono.ttf",
        ]),
        ("DejaVuSansMono-Bold", [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
            "/usr/local/share/fonts/DejaVuSansMono-Bold.ttf",
            "/Library/Fonts/DejaVuSansMono-Bold.ttf",
            "C:/Windows/Fonts/DejaVuSansMono-Bold.ttf",
        ]),
        # Courier New — macOS/Windows, decent Unicode coverage
        ("CourierNew", [
            "/Library/Fonts/Courier New.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
            "C:/Windows/Fonts/cour.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/cour.ttf",
        ]),
        ("CourierNew-Bold", [
            "/Library/Fonts/Courier New Bold.ttf",
            "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
            "C:/Windows/Fonts/courbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/courbd.ttf",
        ]),
        # Noto Sans Mono — Google's comprehensive Unicode font
        ("NotoSansMono", [
            "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
            "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf",
            "/Library/Fonts/NotoSansMono-Regular.ttf",
            "C:/Windows/Fonts/NotoSansMono-Regular.ttf",
        ]),
        ("NotoSansMono-Bold", [
            "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf",
            "/usr/share/fonts/google-noto/NotoSansMono-Bold.ttf",
            "/Library/Fonts/NotoSansMono-Bold.ttf",
            "C:/Windows/Fonts/NotoSansMono-Bold.ttf",
        ]),
    ]

    def __init__(self):
        if not HAS_REPORTLAB:
            raise ImportError(
                "reportlab is required for PDF export. "
                "Install with: pip install reportlab"
            )
        self._font_name, self._font_name_bold = self._register_unicode_font()
        self._setup_styles()

    def _register_unicode_font(self) -> tuple:
        """Register a Unicode-capable monospace font. Returns (regular, bold) font names."""
        registered = {}

        for font_name, paths in self._FONT_CANDIDATES:
            for font_path in paths:
                if Path(font_path).exists():
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        registered[font_name] = True
                        logger.debug(f"Registered font: {font_name} from {font_path}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to register {font_name} from {font_path}: {e}")

        # Find a matching regular+bold pair, or regular-only
        font_families = [
            ("DejaVuSansMono", "DejaVuSansMono-Bold"),
            ("CourierNew", "CourierNew-Bold"),
            ("NotoSansMono", "NotoSansMono-Bold"),
        ]

        for regular, bold in font_families:
            if regular in registered:
                bold_name = bold if bold in registered else regular
                logger.info(f"Using Unicode font: {regular}")
                return regular, bold_name

        # Fallback to built-in Courier (ASCII only)
        logger.warning("No Unicode monospace font found — falling back to Courier (Vietnamese will show ■)")
        return "Courier", "Courier-Bold"

    def _setup_styles(self):
        """Setup paragraph styles for screenplay elements"""
        self.styles = getSampleStyleSheet()
        fn = self._font_name
        fn_bold = self._font_name_bold

        # Action style (left-aligned)
        self.action_style = ParagraphStyle(
            'Action',
            parent=self.styles['Normal'],
            fontName=fn,
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
            fontName=fn_bold,
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
            fontName=fn,
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
            fontName=fn,
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
            fontName=fn,
            fontSize=12,
            leading=14,
            leftIndent=1.0 * 72,
            rightIndent=1.5 * 72,
            spaceAfter=12,
        )

        # Transition style (right-aligned)
        self.transition_style = ParagraphStyle(
            'Transition',
            parent=self.styles['Normal'],
            fontName=fn,
            fontSize=12,
            leading=14,
            alignment=TA_RIGHT,
            spaceAfter=12,
            spaceBefore=12,
        )

        # Title style
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Normal'],
            fontName=fn_bold,
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=24,
        )

        # Author style
        self.author_style = ParagraphStyle(
            'Author',
            parent=self.styles['Normal'],
            fontName=fn,
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=12,
        )

    def _build_screenplay_elements(self, screenplay: Screenplay) -> list:
        """Build all PDF elements for a screenplay"""
        elements = []

        # Title page
        elements.extend(self._build_title_page(screenplay))

        # Page break after title
        elements.append(Spacer(1, 4 * 72))

        # FADE IN:
        elements.append(Paragraph(self._escape_text("FADE IN:"), self.action_style))

        # Scenes
        total_scenes = len(screenplay.scenes)
        for i, scene in enumerate(screenplay.scenes):
            elements.extend(self._build_scene(scene))

            # Add transition between scenes
            is_last = (i == total_scenes - 1)
            if is_last:
                elements.append(Paragraph(self._escape_text("FADE OUT."), self.transition_style))
            else:
                transition = getattr(scene, 'transition_out', '') or "CUT TO:"
                if not transition.endswith(":"):
                    transition += ":"
                elements.append(Paragraph(self._escape_text(transition), self.transition_style))

        return elements

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

        elements = self._build_screenplay_elements(screenplay)
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

        elements = self._build_screenplay_elements(screenplay)
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

        # Scene heading with scene number prefix
        heading_text = f"{scene.scene_number}    {str(scene.heading).upper()}"
        heading_text = self._escape_text(heading_text)
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
