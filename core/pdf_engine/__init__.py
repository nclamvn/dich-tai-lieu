"""
PDF Engine - Professional PDF generation using ReportLab.

This module provides:
- PDF templates (ebook, academic, business)
- Font management with Vietnamese support
- Style building from templates
- PDF rendering from NormalizedDocument

Usage:
    from core.pdf_engine import PdfRenderer, create_pdf_template

    # Render from markdown
    renderer = PdfRenderer(template="ebook")
    result = renderer.render_markdown(
        markdown_content="# Hello\\n\\nWorld",
        output_path="output.pdf",
        title="My Document"
    )

    # Render from Agent 2 output folder
    renderer = PdfRenderer(template="academic")
    result = renderer.render_from_folder(
        source_folder="book_output/",
        output_path="book.pdf"
    )

Key components:
- PdfRenderer: Main renderer class
- PdfTemplate: Abstract base for templates
- create_pdf_template: Factory function
- FontManager: Font registration
- StyleBuilder: Style conversion
"""

from .renderer import PdfRenderer
from .style_builder import FontManager, StyleBuilder, create_style_builder
from .templates import (
    PdfTemplate,
    TemplateType,
    PageSpec,
    FontSpec,
    ParagraphSpec,
    HeaderFooterSpec,
    TocSpec,
    create_pdf_template,
    EbookPdfTemplate,
    AcademicPdfTemplate,
    BusinessPdfTemplate,
)


__all__ = [
    # Main renderer
    'PdfRenderer',

    # Style utilities
    'FontManager',
    'StyleBuilder',
    'create_style_builder',

    # Template base
    'PdfTemplate',
    'TemplateType',
    'PageSpec',
    'FontSpec',
    'ParagraphSpec',
    'HeaderFooterSpec',
    'TocSpec',

    # Factory
    'create_pdf_template',

    # Concrete templates
    'EbookPdfTemplate',
    'AcademicPdfTemplate',
    'BusinessPdfTemplate',
]


__version__ = '1.0.0'
