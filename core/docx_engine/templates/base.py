"""
Base template class for DOCX rendering.
All templates must inherit from DocxTemplate.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum

from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE


class TemplateType(Enum):
    """Available template types"""
    EBOOK = "ebook"
    ACADEMIC = "academic"
    BUSINESS = "business"


@dataclass
class FontSpec:
    """Font specification"""
    name: str
    size: Pt
    bold: bool = False
    italic: bool = False
    color: Optional[RGBColor] = None


@dataclass
class ParagraphSpec:
    """Paragraph style specification"""
    font: FontSpec
    alignment: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY
    line_spacing: float = 1.15  # Multiple
    space_before: Pt = field(default_factory=lambda: Pt(0))
    space_after: Pt = field(default_factory=lambda: Pt(6))
    first_line_indent: Optional[Cm] = None
    keep_with_next: bool = False
    page_break_before: bool = False
    widow_control: bool = True


@dataclass
class PageSetup:
    """Page layout specification"""
    width: Cm
    height: Cm
    top_margin: Cm
    bottom_margin: Cm
    left_margin: Cm
    right_margin: Cm
    gutter: Cm = field(default_factory=lambda: Cm(0))
    mirror_margins: bool = False  # For book binding

    @classmethod
    def a4(cls) -> 'PageSetup':
        """Standard A4"""
        return cls(
            width=Cm(21), height=Cm(29.7),
            top_margin=Cm(2.5), bottom_margin=Cm(2.5),
            left_margin=Cm(2.5), right_margin=Cm(2.5)
        )

    @classmethod
    def trade_paperback(cls) -> 'PageSetup':
        """Trade paperback (14x21.5cm / 5.5x8.5in)"""
        return cls(
            width=Cm(14), height=Cm(21.5),
            top_margin=Cm(2), bottom_margin=Cm(2),
            left_margin=Cm(2), right_margin=Cm(2),
            mirror_margins=True
        )

    @classmethod
    def us_letter(cls) -> 'PageSetup':
        """US Letter"""
        return cls(
            width=Inches(8.5), height=Inches(11),
            top_margin=Inches(1), bottom_margin=Inches(1),
            left_margin=Inches(1), right_margin=Inches(1)
        )


@dataclass
class HeaderFooterSpec:
    """Header/footer specification"""
    show_header: bool = True
    show_footer: bool = True

    # Header content
    header_left: Optional[str] = None   # e.g., book title
    header_center: Optional[str] = None
    header_right: Optional[str] = None  # e.g., chapter title

    # Footer content (use {page} for page number)
    footer_left: Optional[str] = None
    footer_center: str = "{page}"  # Page number
    footer_right: Optional[str] = None

    # Different first page
    different_first_page: bool = True

    # Font
    font: FontSpec = field(default_factory=lambda: FontSpec(name="Arial", size=Pt(9)))


@dataclass
class TocSpec:
    """Table of contents specification"""
    title: str = "Table of Contents"
    title_style: Optional[ParagraphSpec] = None
    level1_style: Optional[ParagraphSpec] = None  # Chapters
    level2_style: Optional[ParagraphSpec] = None  # Sections
    level3_style: Optional[ParagraphSpec] = None  # Subsections
    show_page_numbers: bool = True
    dot_leader: bool = True  # Dots between title and page number


class DocxTemplate(ABC):
    """
    Abstract base class for DOCX templates.

    Subclasses must implement all abstract methods to define
    how different document elements should be styled.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Template name"""
        pass

    @property
    @abstractmethod
    def template_type(self) -> TemplateType:
        """Template type enum"""
        pass

    @abstractmethod
    def get_page_setup(self) -> PageSetup:
        """Return page layout configuration"""
        pass

    @abstractmethod
    def get_styles(self) -> Dict[str, ParagraphSpec]:
        """
        Return mapping of semantic style names to specifications.

        Required keys:
        - title: Document title
        - subtitle: Document subtitle
        - heading_1: Chapter titles (H1)
        - heading_2: Section titles (H2)
        - heading_3: Subsection titles (H3)
        - body: Normal paragraphs
        - body_first: First paragraph after heading (no indent)
        - quote: Block quotes
        - code: Code blocks
        - list_bullet: Bullet list items
        - list_numbered: Numbered list items
        - footnote: Footnote text
        - caption: Figure/table captions
        """
        pass

    @abstractmethod
    def get_header_footer(self) -> HeaderFooterSpec:
        """Return header/footer configuration"""
        pass

    @abstractmethod
    def get_toc_spec(self) -> TocSpec:
        """Return table of contents configuration"""
        pass

    def get_chapter_break_type(self) -> str:
        """
        Return chapter break type.
        Options: 'page', 'odd_page', 'section', 'none'
        Default: 'page' (new page for each chapter)
        """
        return 'page'

    def get_drop_cap_enabled(self) -> bool:
        """Whether to use drop caps for first letter of chapters"""
        return False

    def get_custom_style(self, name: str) -> Optional[ParagraphSpec]:
        """
        Get a custom style by name.
        Override in subclass to add template-specific styles.
        """
        return None


def create_template(template_type: str) -> DocxTemplate:
    """
    Factory function to create template by name.

    Args:
        template_type: 'ebook', 'academic', or 'business'

    Returns:
        DocxTemplate instance
    """
    from .ebook import EbookTemplate
    from .academic import AcademicTemplate
    from .business import BusinessTemplate

    templates = {
        'ebook': EbookTemplate,
        'academic': AcademicTemplate,
        'business': BusinessTemplate,
    }

    template_class = templates.get(template_type.lower())
    if not template_class:
        raise ValueError(f"Unknown template type: {template_type}. Available: {list(templates.keys())}")

    return template_class()
