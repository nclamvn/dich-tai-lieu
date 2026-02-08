"""
Base template classes for PDF rendering with ReportLab.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List
from enum import Enum

from reportlab.lib.units import cm, mm, inch
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.colors import Color, black, white, HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY


class TemplateType(Enum):
    """PDF template types"""
    EBOOK = "ebook"
    ACADEMIC = "academic"
    BUSINESS = "business"


@dataclass
class PageSpec:
    """Page layout specification"""
    width: float       # in points
    height: float      # in points
    top_margin: float
    right_margin: float
    bottom_margin: float
    left_margin: float

    @property
    def size(self) -> Tuple[float, float]:
        return (self.width, self.height)

    @property
    def margins(self) -> Tuple[float, float, float, float]:
        """(top, right, bottom, left)"""
        return (self.top_margin, self.right_margin, self.bottom_margin, self.left_margin)

    @classmethod
    def a4(cls, margins: Tuple[float, float, float, float] = None) -> 'PageSpec':
        """Standard A4 (210 x 297 mm)"""
        m = margins or (2.5*cm, 2*cm, 2.5*cm, 2*cm)
        return cls(
            width=A4[0], height=A4[1],
            top_margin=m[0], right_margin=m[1],
            bottom_margin=m[2], left_margin=m[3]
        )

    @classmethod
    def trade_paperback(cls) -> 'PageSpec':
        """Trade paperback (14 x 21.5 cm / 5.5 x 8.5 in)"""
        return cls(
            width=14*cm, height=21.5*cm,
            top_margin=2*cm, right_margin=1.5*cm,
            bottom_margin=2*cm, left_margin=1.5*cm
        )

    @classmethod
    def us_letter(cls) -> 'PageSpec':
        """US Letter (8.5 x 11 in)"""
        return cls(
            width=LETTER[0], height=LETTER[1],
            top_margin=1*inch, right_margin=1*inch,
            bottom_margin=1*inch, left_margin=1*inch
        )


@dataclass
class FontSpec:
    """Font specification for PDF"""
    family: str          # Font family name (must be registered)
    size: float          # Font size in points
    leading: float       # Line height in points (usually size * 1.2-1.5)
    bold: bool = False
    italic: bool = False
    color: Color = field(default_factory=lambda: black)

    def get_font_name(self) -> str:
        """Get ReportLab font name based on style"""
        base = self.family
        if self.bold and self.italic:
            return f"{base}-BoldItalic"
        elif self.bold:
            return f"{base}-Bold"
        elif self.italic:
            return f"{base}-Italic"
        return base


@dataclass
class ParagraphSpec:
    """Paragraph style specification for PDF"""
    font: FontSpec
    alignment: int = TA_JUSTIFY  # TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    space_before: float = 0      # points
    space_after: float = 6       # points
    first_line_indent: float = 0 # points
    left_indent: float = 0       # points
    right_indent: float = 0      # points

    # Advanced
    keep_with_next: bool = False
    allow_widows: bool = True
    allow_orphans: bool = True


@dataclass
class HeaderFooterSpec:
    """Header and footer specification"""
    show_header: bool = True
    show_footer: bool = True

    # Header content (use {title}, {author}, {page}, {date} as placeholders)
    header_left: Optional[str] = None
    header_center: Optional[str] = None
    header_right: Optional[str] = None

    # Footer content
    footer_left: Optional[str] = None
    footer_center: str = "{page}"
    footer_right: Optional[str] = None

    # Styling
    font: FontSpec = field(default_factory=lambda: FontSpec(
        family='DejaVuSerif', size=9, leading=11
    ))

    # Different first page (title page)
    different_first_page: bool = True

    # Line separator
    header_line: bool = False
    footer_line: bool = False


@dataclass
class TocSpec:
    """Table of contents specification"""
    title: str = "Table of Contents"

    # Styles for each level
    title_style: Optional[ParagraphSpec] = None
    level1_style: Optional[ParagraphSpec] = None
    level2_style: Optional[ParagraphSpec] = None
    level3_style: Optional[ParagraphSpec] = None

    # Formatting
    show_page_numbers: bool = True
    dot_leader: bool = True
    indent_per_level: float = 18  # points


class PdfTemplate(ABC):
    """
    Abstract base class for PDF templates.

    All PDF templates must implement these methods to define
    page layout, fonts, and styling.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Template display name"""
        pass

    @property
    @abstractmethod
    def template_type(self) -> TemplateType:
        """Template type enum"""
        pass

    @abstractmethod
    def get_page_spec(self) -> PageSpec:
        """Return page size and margins"""
        pass

    @abstractmethod
    def get_fonts(self) -> Dict[str, str]:
        """
        Return font file mapping for registration.
        Keys: 'regular', 'bold', 'italic', 'bold_italic', 'mono'
        Values: Font file names (e.g., 'DejaVuSerif.ttf')
        """
        pass

    @abstractmethod
    def get_styles(self) -> Dict[str, ParagraphSpec]:
        """
        Return style mapping for document elements.

        Required keys:
        - title: Document title
        - subtitle: Document subtitle
        - author: Author name
        - heading_1: Chapter titles
        - heading_2: Section titles
        - heading_3: Subsection titles
        - body: Normal paragraphs
        - body_first: First paragraph after heading
        - quote: Block quotes
        - code: Code blocks
        - list_item: List items
        - caption: Figure/table captions
        - toc_title: TOC title
        - toc_1, toc_2, toc_3: TOC entries
        - glossary_term: Glossary term
        - glossary_def: Glossary definition
        """
        pass

    @abstractmethod
    def get_header_footer(self) -> HeaderFooterSpec:
        """Return header/footer configuration"""
        pass

    def get_toc_spec(self) -> TocSpec:
        """Return TOC configuration. Override for custom TOC."""
        styles = self.get_styles()
        return TocSpec(
            title="Table of Contents",
            title_style=styles.get('toc_title'),
            level1_style=styles.get('toc_1'),
            level2_style=styles.get('toc_2'),
            level3_style=styles.get('toc_3'),
        )

    def get_chapter_break(self) -> str:
        """
        Return chapter break type.
        'page': New page for each chapter
        'none': No page break
        """
        return 'page'

    def get_font_search_paths(self) -> List[str]:
        """Return paths to search for font files"""
        return [
            '/usr/share/fonts/truetype/dejavu/',
            '/usr/share/fonts/TTF/',
            '/usr/local/share/fonts/',
            '~/.fonts/',
            './fonts/',
            './assets/fonts/',
        ]


def create_pdf_template(template_type: str) -> PdfTemplate:
    """
    Factory function to create PDF template by name.

    Args:
        template_type: 'ebook', 'academic', or 'business'

    Returns:
        PdfTemplate instance
    """
    from .ebook_pdf import EbookPdfTemplate
    from .academic_pdf import AcademicPdfTemplate
    from .business_pdf import BusinessPdfTemplate

    templates = {
        'ebook': EbookPdfTemplate,
        'academic': AcademicPdfTemplate,
        'business': BusinessPdfTemplate,
    }

    template_class = templates.get(template_type.lower())
    if not template_class:
        raise ValueError(
            f"Unknown PDF template: {template_type}. "
            f"Available: {list(templates.keys())}"
        )

    return template_class()
