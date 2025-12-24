"""
STEM-Aware Translation Module

This module provides specialized translation capabilities for STEM documents,
including:
- Formula detection and preservation (LaTeX, Unicode math)
- Code block detection and preservation
- Layout-aware processing with PyMuPDF
- Technical term glossaries
- PDF layout extraction and reconstruction (Phase 1 skeleton)
"""

from .formula_detector import FormulaDetector, FormulaMatch
from .code_detector import CodeDetector, CodeMatch
from .placeholder_manager import PlaceholderManager, ProcessedContent
from .stem_translator import STEMTranslator
from .layout_extractor import LayoutExtractor, DocumentLayout, PageLayout, TextBlock
from .pdf_reconstructor import PDFReconstructor

__all__ = [
    # Phase 0: Core STEM translation
    'FormulaDetector',
    'FormulaMatch',
    'CodeDetector',
    'CodeMatch',
    'PlaceholderManager',
    'ProcessedContent',
    'STEMTranslator',
    # Phase 1: Layout-aware processing
    'LayoutExtractor',
    'DocumentLayout',
    'PageLayout',
    'TextBlock',
    'PDFReconstructor',
]

__version__ = '1.1.0'  # Phase 0 + Phase 1 skeleton
