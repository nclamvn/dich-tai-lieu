#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Formatting Engine v1.0

Professional document formatting system for AI Translator Pro.
Provides structure detection, style application, and export capabilities.

Stages:
1. Structure Detection - Detect headings, lists, tables, etc.
2. Document Model - Build AST and validate hierarchy
3. Style Application - Apply professional formatting
4. Export - Generate DOCX/Markdown output
"""

__version__ = "1.0.0"

# Stage 1 & 2: Detection and Model
from .detector import (
    StructureDetector,
    DocumentElement,
    LineContext,
    ListItem,
    ListElement,
    TableCell,
    TableRow,
    TableElement,
    # Advanced elements
    CodeBlockElement,
    FormulaElement,
    BlockquoteElement,
    FootnoteRef,
    FootnoteDef,
    FigureElement,
    HorizontalRuleElement,
)
from .document_model import DocumentModel, TocEntry, ValidationError

# Stage 3: Style Engine
from .style_engine import (
    StyleEngine,
    StyledDocument,
    StyledElement,
    StyledListItem,
    StyledList,
    StyledTableCell,
    StyledTableRow,
    StyledTable,
    # Advanced styled elements
    StyledCodeBlock,
    StyledBlockquote,
    StyledFigure,
    StyledHorizontalRule,
)

# Page Layout
from .page_layout import (
    PageLayoutManager,
    PageDimensions,
    Margins,
    ContentArea,
    HeaderFooterConfig,
)

# TOC Generator
from .toc_generator import (
    TocGenerator,
    TocElement,
    TocEntry as TocGeneratorEntry,  # Alias to avoid conflict with document_model.TocEntry
    generate_toc_from_headings,
)

# Stage 4: Exporters
from .exporters import DocxStyleExporter, MarkdownStyleExporter

# Templates
from .templates import (
    BaseTemplate,
    TemplateConfig,
    BookTemplate,
    ReportTemplate,
    LegalTemplate,
    AcademicTemplate,
    TemplateFactory,
)

__all__ = [
    # Detection
    "StructureDetector",
    "DocumentElement",
    "LineContext",
    # List structures
    "ListItem",
    "ListElement",
    # Table structures
    "TableCell",
    "TableRow",
    "TableElement",
    # Advanced elements
    "CodeBlockElement",
    "FormulaElement",
    "BlockquoteElement",
    "FootnoteRef",
    "FootnoteDef",
    "FigureElement",
    "HorizontalRuleElement",
    # Model
    "DocumentModel",
    "TocEntry",
    "ValidationError",
    # Styling
    "StyleEngine",
    "StyledDocument",
    "StyledElement",
    # Styled List
    "StyledListItem",
    "StyledList",
    # Styled Table
    "StyledTableCell",
    "StyledTableRow",
    "StyledTable",
    # Styled Advanced Elements
    "StyledCodeBlock",
    "StyledBlockquote",
    "StyledFigure",
    "StyledHorizontalRule",
    # Page Layout
    "PageLayoutManager",
    "PageDimensions",
    "Margins",
    "ContentArea",
    "HeaderFooterConfig",
    # TOC Generator
    "TocGenerator",
    "TocElement",
    "TocGeneratorEntry",
    "generate_toc_from_headings",
    # Export
    "DocxStyleExporter",
    "MarkdownStyleExporter",
    # Templates
    "BaseTemplate",
    "TemplateConfig",
    "BookTemplate",
    "ReportTemplate",
    "LegalTemplate",
    "AcademicTemplate",
    "TemplateFactory",
]
