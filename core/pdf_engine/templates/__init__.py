"""
PDF Template module exports.
"""

from .base import (
    PdfTemplate,
    TemplateType,
    PageSpec,
    FontSpec,
    ParagraphSpec,
    HeaderFooterSpec,
    TocSpec,
    create_pdf_template,
)

from .ebook_pdf import EbookPdfTemplate
from .academic_pdf import AcademicPdfTemplate
from .business_pdf import BusinessPdfTemplate


__all__ = [
    # Base classes
    'PdfTemplate',
    'TemplateType',
    'PageSpec',
    'FontSpec',
    'ParagraphSpec',
    'HeaderFooterSpec',
    'TocSpec',

    # Factory
    'create_pdf_template',

    # Template implementations
    'EbookPdfTemplate',
    'AcademicPdfTemplate',
    'BusinessPdfTemplate',
]
