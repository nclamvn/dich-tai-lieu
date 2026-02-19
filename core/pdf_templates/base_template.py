"""
Base Template - Abstract class for PDF templates
AI Publisher Pro

All templates inherit from this class and implement their specific styles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum

from core.i18n import format_chapter_title


class PageSize(Enum):
    """Standard page sizes"""
    A4 = ("A4", 210, 297)
    A5 = ("A5", 148, 210)
    A6 = ("A6", 105, 148)
    B5 = ("B5", 176, 250)
    LETTER = ("Letter", 216, 279)
    TRADE = ("Trade Paperback", 140, 215)
    ROYAL = ("Royal", 156, 234)
    CUSTOM = ("Custom", 0, 0)


@dataclass
class TemplateConfig:
    """Template configuration settings"""

    # Page Size
    page_size_name: str = "A5"
    page_width_mm: float = 148
    page_height_mm: float = 210

    # Margins (mm)
    margin_top: float = 20
    margin_bottom: float = 25
    margin_inner: float = 20  # Binding side
    margin_outer: float = 15

    # Typography - Body
    body_font: str = "NotoSerif"
    body_size: float = 11
    line_height: float = 1.6
    first_line_indent: float = 20  # First paragraph indent (pt)
    paragraph_spacing: float = 0  # Space between paragraphs (pt)

    # Typography - Headings
    heading_font: str = "NotoSerif"
    chapter_title_size: float = 24
    section_title_size: float = 16
    subsection_title_size: float = 13

    # Features
    justify_text: bool = True
    hyphenation: bool = False
    drop_cap: bool = False
    drop_cap_lines: int = 3

    # Page Numbers
    page_numbers: bool = True
    page_number_position: str = "bottom_center"  # bottom_center, bottom_outer, top_outer

    # Headers/Footers
    running_header: bool = False
    header_font_size: float = 9

    # Chapter styling
    chapter_page_break: bool = True
    chapter_start_recto: bool = False  # Start chapters on right page only
    chapter_drop_lines: int = 3  # Lines to drop before chapter title

    # Decorations
    ornaments: bool = False
    section_dividers: bool = False

    # Font files (paths)
    font_regular: str = ""
    font_bold: str = ""
    font_italic: str = ""
    font_bold_italic: str = ""

    def to_dict(self) -> Dict:
        """Convert config to dictionary"""
        return {
            "page_size": {
                "name": self.page_size_name,
                "width_mm": self.page_width_mm,
                "height_mm": self.page_height_mm,
            },
            "margins": {
                "top": self.margin_top,
                "bottom": self.margin_bottom,
                "inner": self.margin_inner,
                "outer": self.margin_outer,
            },
            "typography": {
                "body_font": self.body_font,
                "body_size": self.body_size,
                "line_height": self.line_height,
                "heading_font": self.heading_font,
            },
            "features": {
                "justify": self.justify_text,
                "drop_cap": self.drop_cap,
                "page_numbers": self.page_numbers,
                "running_header": self.running_header,
            },
        }


class BaseTemplate(ABC):
    """
    Abstract base class for PDF templates.

    All templates must implement:
    - config property (TemplateConfig)
    - get_styles() method
    - create_cover() method (optional)
    """

    def __init__(self):
        self._config: Optional[TemplateConfig] = None
        self._styles: Optional[Dict] = None

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable template name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the template"""
        pass

    @property
    @abstractmethod
    def font_style(self) -> str:
        """Font style category (serif/sans-serif)"""
        pass

    @property
    @abstractmethod
    def best_for(self) -> List[str]:
        """List of best use cases"""
        pass

    @property
    @abstractmethod
    def config(self) -> TemplateConfig:
        """Get template configuration"""
        pass

    @abstractmethod
    def get_styles(self) -> Dict:
        """
        Get ReportLab paragraph styles for this template.

        Returns:
            Dict with style names as keys and ParagraphStyle objects as values
        """
        pass

    def get_page_size(self) -> Tuple[float, float]:
        """Get page size in points (1mm = 2.83465pt)"""
        MM_TO_PT = 2.83465
        return (
            self.config.page_width_mm * MM_TO_PT,
            self.config.page_height_mm * MM_TO_PT
        )

    def get_margins(self) -> Dict[str, float]:
        """Get margins in points"""
        MM_TO_PT = 2.83465
        return {
            "top": self.config.margin_top * MM_TO_PT,
            "bottom": self.config.margin_bottom * MM_TO_PT,
            "inner": self.config.margin_inner * MM_TO_PT,
            "outer": self.config.margin_outer * MM_TO_PT,
        }

    def register_fonts(self) -> bool:
        """
        Register fonts for this template.

        Returns:
            True if fonts registered successfully
        """
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.pdfbase.pdfmetrics import registerFontFamily

            font_name = self.config.body_font

            # Check if fonts exist
            fonts_dir = Path(__file__).parent / "fonts"
            font_paths = self._get_font_paths(fonts_dir)

            if not font_paths:
                # Use fallback system fonts
                font_paths = self._get_fallback_fonts()

            if not font_paths:
                return False

            # Register fonts
            pdfmetrics.registerFont(TTFont(font_name, font_paths["regular"]))
            if font_paths.get("bold"):
                pdfmetrics.registerFont(TTFont(f"{font_name}-Bold", font_paths["bold"]))
            if font_paths.get("italic"):
                pdfmetrics.registerFont(TTFont(f"{font_name}-Italic", font_paths["italic"]))
            if font_paths.get("bold_italic"):
                pdfmetrics.registerFont(TTFont(f"{font_name}-BoldItalic", font_paths["bold_italic"]))

            # Register font family
            registerFontFamily(
                font_name,
                normal=font_name,
                bold=f"{font_name}-Bold" if font_paths.get("bold") else font_name,
                italic=f"{font_name}-Italic" if font_paths.get("italic") else font_name,
                boldItalic=f"{font_name}-BoldItalic" if font_paths.get("bold_italic") else font_name,
            )

            return True

        except Exception as e:
            print(f"Font registration error: {e}")
            return False

    def _get_font_paths(self, fonts_dir: Path) -> Optional[Dict[str, str]]:
        """Get font file paths from templates fonts directory"""
        font_name = self.config.body_font

        # Common font file patterns
        patterns = {
            "regular": [f"{font_name}-Regular.ttf", f"{font_name}.ttf"],
            "bold": [f"{font_name}-Bold.ttf"],
            "italic": [f"{font_name}-Italic.ttf"],
            "bold_italic": [f"{font_name}-BoldItalic.ttf"],
        }

        result = {}
        for style, filenames in patterns.items():
            for filename in filenames:
                path = fonts_dir / filename
                if path.exists():
                    result[style] = str(path)
                    break

        return result if result.get("regular") else None

    def _get_fallback_fonts(self) -> Optional[Dict[str, str]]:
        """Get fallback system fonts with Vietnamese support"""
        import platform

        system = platform.system()

        # Fallback font paths by system
        if system == "Darwin":  # macOS
            base = "/System/Library/Fonts"
            return {
                "regular": f"{base}/Supplemental/Times New Roman.ttf",
                "bold": f"{base}/Supplemental/Times New Roman Bold.ttf",
                "italic": f"{base}/Supplemental/Times New Roman Italic.ttf",
            }
        elif system == "Linux":
            base = "/usr/share/fonts/truetype/dejavu"
            return {
                "regular": f"{base}/DejaVuSerif.ttf",
                "bold": f"{base}/DejaVuSerif-Bold.ttf",
                "italic": f"{base}/DejaVuSerif-Italic.ttf",
                "bold_italic": f"{base}/DejaVuSerif-BoldItalic.ttf",
            }
        else:  # Windows
            base = "C:/Windows/Fonts"
            return {
                "regular": f"{base}/times.ttf",
                "bold": f"{base}/timesbd.ttf",
                "italic": f"{base}/timesi.ttf",
            }

    def create_cover(
        self,
        title: str,
        author: str,
        subtitle: Optional[str] = None,
    ) -> List:
        """
        Create cover page elements.

        Override in subclass for custom cover design.

        Returns:
            List of ReportLab flowables for cover page
        """
        from reportlab.platypus import Spacer, Paragraph, PageBreak
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER

        styles = self.get_styles()
        elements = []

        # Add spacing from top
        elements.append(Spacer(1, 100))

        # Title
        title_style = styles.get("cover_title", styles.get("chapter_title"))
        elements.append(Paragraph(title, title_style))

        # Subtitle
        if subtitle:
            elements.append(Spacer(1, 20))
            subtitle_style = styles.get("cover_subtitle", styles.get("body"))
            elements.append(Paragraph(subtitle, subtitle_style))

        # Author
        elements.append(Spacer(1, 40))
        author_style = styles.get("cover_author", styles.get("body"))
        elements.append(Paragraph(author, author_style))

        # Page break after cover
        elements.append(PageBreak())

        return elements

    def create_chapter_opening(self, title: str, number: Optional[int] = None, lang: str = "en") -> List:
        """
        Create chapter opening elements.

        Override in subclass for custom chapter design.

        Returns:
            List of ReportLab flowables for chapter opening
        """
        from reportlab.platypus import Spacer, Paragraph, PageBreak

        styles = self.get_styles()
        elements = []

        # Page break before chapter (if configured)
        if self.config.chapter_page_break:
            elements.append(PageBreak())

        # Drop lines before title
        if self.config.chapter_drop_lines > 0:
            drop_space = self.config.chapter_drop_lines * self.config.body_size * self.config.line_height
            elements.append(Spacer(1, drop_space))

        # Chapter number
        if number is not None:
            chapter_num_style = styles.get("chapter_number", styles.get("body"))
            chapter_label = format_chapter_title(number, "", lang)
            elements.append(Paragraph(chapter_label, chapter_num_style))
            elements.append(Spacer(1, 10))

        # Chapter title
        chapter_style = styles.get("chapter_title")
        elements.append(Paragraph(title, chapter_style))

        # Space after title
        elements.append(Spacer(1, 30))

        return elements

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.display_name}>"
