"""Template exports"""

from .base import DocxTemplate, TemplateType, create_template, PageSetup, ParagraphSpec, FontSpec
from .ebook import EbookTemplate
from .academic import AcademicTemplate
from .business import BusinessTemplate

__all__ = [
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
