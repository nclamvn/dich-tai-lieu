"""
Data models for DOCX Template Engine.
All models use dataclasses for simplicity.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class BlockType(Enum):
    """Content block types"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    FIGURE = "figure"
    QUOTE = "quote"
    CODE = "code"
    FOOTNOTE = "footnote"
    PAGE_BREAK = "page_break"


class ListType(Enum):
    """List types"""
    BULLET = "bullet"
    NUMBERED = "numbered"


@dataclass
class InlineStyle:
    """Inline text formatting"""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    superscript: bool = False
    subscript: bool = False
    code: bool = False  # Inline code


@dataclass
class TextRun:
    """A run of text with consistent styling"""
    text: str
    style: InlineStyle = field(default_factory=InlineStyle)


@dataclass
class ContentBlock:
    """Universal content block"""
    type: BlockType
    level: int = 1  # For headings: 1-6, for lists: nesting level
    content: Any = None  # str, List[TextRun], List[ListItem], TableData, etc.
    style_hints: Dict[str, Any] = field(default_factory=dict)

    # Optional metadata
    id: Optional[str] = None  # For cross-references
    caption: Optional[str] = None  # For figures/tables


@dataclass
class ListItem:
    """A single list item (can contain nested content)"""
    content: List[TextRun]
    children: List['ListItem'] = field(default_factory=list)  # Nested items


@dataclass
class TableCell:
    """Table cell"""
    content: List[TextRun]
    colspan: int = 1
    rowspan: int = 1
    is_header: bool = False


@dataclass
class TableData:
    """Table structure"""
    rows: List[List[TableCell]]
    has_header_row: bool = True
    caption: Optional[str] = None


@dataclass
class Footnote:
    """Footnote reference"""
    id: str
    content: List[TextRun]


@dataclass
class Chapter:
    """A chapter in the document"""
    number: int
    title: str
    content: List[ContentBlock]

    # Optional
    subtitle: Optional[str] = None
    epigraph: Optional[str] = None  # Opening quote
    footnotes: List[Footnote] = field(default_factory=list)


@dataclass
class FrontMatterItem:
    """Front matter section (dedication, preface, etc.)"""
    type: str  # "dedication", "preface", "acknowledgments", "foreword"
    title: Optional[str]
    content: List[ContentBlock]


@dataclass
class FrontMatter:
    """All front matter"""
    items: List[FrontMatterItem] = field(default_factory=list)


@dataclass
class TocItem:
    """Table of contents entry"""
    title: str
    level: int  # 1 = chapter, 2 = section, etc.
    page_number: Optional[int] = None  # Filled during render
    chapter_number: Optional[int] = None


@dataclass
class TableOfContents:
    """Table of contents"""
    title: str = "Table of Contents"
    items: List[TocItem] = field(default_factory=list)
    auto_generate: bool = True  # Generate from headings


@dataclass
class GlossaryItem:
    """Glossary entry"""
    term: str
    definition: str
    source_term: Optional[str] = None  # Original language term


@dataclass
class Glossary:
    """Glossary section"""
    title: str = "Glossary"
    items: List[GlossaryItem] = field(default_factory=list)


@dataclass
class BibliographyItem:
    """Bibliography/reference entry"""
    id: str
    formatted: str  # Pre-formatted citation string
    type: str = "book"  # book, article, website, etc.


@dataclass
class Bibliography:
    """Bibliography section"""
    title: str = "References"
    items: List[BibliographyItem] = field(default_factory=list)


@dataclass
class Appendix:
    """Appendix section"""
    letter: str  # A, B, C...
    title: str
    content: List[ContentBlock]


@dataclass
class DocumentDNA:
    """Document characteristics from translation phase"""
    genre: str = "general"  # novel, academic, business, technical
    tone: str = "neutral"  # formal, casual, literary
    has_formulas: bool = False
    has_code: bool = False
    has_tables: bool = False
    source_language: str = "en"
    target_language: str = "vi"

    # Detected entities
    characters: List[str] = field(default_factory=list)
    key_terms: Dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentMeta:
    """Document metadata"""
    title: str
    subtitle: Optional[str] = None
    author: str = "Unknown"
    translator: Optional[str] = None
    publisher: Optional[str] = None
    date: Optional[str] = None
    language: str = "vi"
    isbn: Optional[str] = None

    # For headers/footers
    running_title: Optional[str] = None  # Short title for header


@dataclass
class NormalizedDocument:
    """
    Universal document structure for rendering.
    This is the contract between Normalizer and Renderer.
    """
    # Metadata
    meta: DocumentMeta

    # Document DNA
    dna: DocumentDNA

    # Structure
    front_matter: FrontMatter = field(default_factory=FrontMatter)
    toc: TableOfContents = field(default_factory=TableOfContents)
    chapters: List[Chapter] = field(default_factory=list)
    appendices: List[Appendix] = field(default_factory=list)
    glossary: Optional[Glossary] = None
    bibliography: Optional[Bibliography] = None

    def total_chapters(self) -> int:
        return len(self.chapters)

    def all_headings(self) -> List[TocItem]:
        """Extract all headings for TOC generation"""
        items = []
        for chapter in self.chapters:
            items.append(TocItem(
                title=chapter.title,
                level=1,
                chapter_number=chapter.number
            ))
            for block in chapter.content:
                if block.type == BlockType.HEADING:
                    items.append(TocItem(
                        title=block.content if isinstance(block.content, str) else str(block.content),
                        level=block.level + 1  # Chapter is level 1
                    ))
        return items
