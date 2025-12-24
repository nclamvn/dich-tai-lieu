"""
Academic Document Export - Phase 1.4 Consolidation
===================================================

This package provides tools for exporting documents with academic layout.

Module structure:
- docx_styles: Shared styling constants and classes
- docx_base: Base exporter class
- docx_exporter: Basic text-to-DOCX exporter
- docx_academic: Semantic node-based academic exporter
- docx_presentation: Text-based exporter with formula handling

Backward compatibility:
- docx_academic_builder: Legacy wrapper for docx_academic
"""

# Base classes and configurations
from .docx_base import (
    DocxExporterBase,
    ExportConfig,
)

# Styling
from .docx_styles import (
    PAGE_MARGINS,
    PAGE_SIZES,
    DEFAULT_OPTIONS,
    AcademicStyles,
    StyleApplicator,
    THEOREM_TYPES,
    HEADING_LEVELS,
)

# Basic exporter
from .docx_exporter import (
    BasicDocxExporter,
    BasicExportConfig,
    export_basic_docx,
)

# Academic exporter (semantic nodes)
from .docx_academic import (
    AcademicDocxExporter,
    AcademicExportConfig,
    export_academic_docx,
)

# Presentation exporter (text with formulas)
from .docx_presentation import (
    PresentationDocxExporter,
    PresentationExportConfig,
    export_presentation_docx,
)

# Backward compatibility - legacy names
from .docx_academic_builder import (
    AcademicLayoutConfig,
    build_academic_docx,
)

__all__ = [
    # Base
    'DocxExporterBase',
    'ExportConfig',

    # Styling
    'PAGE_MARGINS',
    'PAGE_SIZES',
    'DEFAULT_OPTIONS',
    'AcademicStyles',
    'StyleApplicator',
    'THEOREM_TYPES',
    'HEADING_LEVELS',

    # Basic exporter
    'BasicDocxExporter',
    'BasicExportConfig',
    'export_basic_docx',

    # Academic exporter
    'AcademicDocxExporter',
    'AcademicExportConfig',
    'export_academic_docx',

    # Presentation exporter
    'PresentationDocxExporter',
    'PresentationExportConfig',
    'export_presentation_docx',

    # Backward compatibility
    'AcademicLayoutConfig',
    'build_academic_docx',
]
