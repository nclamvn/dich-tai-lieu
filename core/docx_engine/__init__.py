"""
DOCX Template Engine for AI Publisher Pro

Professional document rendering with multiple templates.
"""

from .models import (
    NormalizedDocument,
    DocumentMeta,
    DocumentDNA,
    Chapter,
    ContentBlock,
    BlockType,
    TextRun,
    InlineStyle,
    ListItem,
    TableData,
    TableCell,
    Glossary,
    GlossaryItem,
    Bibliography,
    BibliographyItem,
    FrontMatter,
    FrontMatterItem,
    TableOfContents,
    TocItem,
    Appendix,
)
from .normalizer import DocumentNormalizer
from .renderer import DocxRenderer
from .style_mapper import StyleMapper, RenderContext
from .layout_engine import LayoutEngine
from .templates import (
    DocxTemplate,
    TemplateType,
    create_template,
    PageSetup,
    ParagraphSpec,
    FontSpec,
    EbookTemplate,
    AcademicTemplate,
    BusinessTemplate,
)

__version__ = "1.0.0"

__all__ = [
    # Main classes
    'DocxRenderer',
    'DocumentNormalizer',
    'StyleMapper',
    'RenderContext',
    'LayoutEngine',

    # Models
    'NormalizedDocument',
    'DocumentMeta',
    'DocumentDNA',
    'Chapter',
    'ContentBlock',
    'BlockType',
    'TextRun',
    'InlineStyle',
    'ListItem',
    'TableData',
    'TableCell',
    'Glossary',
    'GlossaryItem',
    'Bibliography',
    'BibliographyItem',
    'FrontMatter',
    'FrontMatterItem',
    'TableOfContents',
    'TocItem',
    'Appendix',

    # Templates
    'DocxTemplate',
    'TemplateType',
    'create_template',
    'PageSetup',
    'ParagraphSpec',
    'FontSpec',
    'EbookTemplate',
    'AcademicTemplate',
    'BusinessTemplate',
]
