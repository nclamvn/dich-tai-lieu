#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Templates Module.

Provides a flexible template system for document formatting with
preset styles for different document types.

Templates:
- BookTemplate: Novels, non-fiction, textbooks
- ReportTemplate: Business reports, technical docs
- LegalTemplate: Contracts, legal documents
- AcademicTemplate: Research papers, theses

Usage:
    from core.formatting.templates import TemplateFactory, BookTemplate

    # Get template by name
    template = TemplateFactory.get_template("book")
    config = template.get_config()

    # Auto-detect template
    template_name = TemplateFactory.auto_detect(document_text)

    # Customize template
    custom = template.customize(margins="wide", page_size="Letter")
"""

from .base_template import BaseTemplate, TemplateConfig
from .book_template import BookTemplate
from .report_template import ReportTemplate
from .legal_template import LegalTemplate
from .academic_template import AcademicTemplate
from .template_factory import TemplateFactory

__all__ = [
    # Base classes
    "BaseTemplate",
    "TemplateConfig",
    # Template implementations
    "BookTemplate",
    "ReportTemplate",
    "LegalTemplate",
    "AcademicTemplate",
    # Factory
    "TemplateFactory",
]
