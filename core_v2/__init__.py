"""
Core V2 - Claude-Native Universal Publishing Pipeline

This module implements a revolutionary approach to document translation and publishing:
- Let Claude handle ALL content decisions (formatting, style, terminology)
- Code only handles orchestration, chunking boundaries, and file I/O
- Supports 20+ publishing genres with ZERO formatting code

Architecture:
    DocumentDNA → SemanticChunker → Claude Translation → OutputConverter
"""

from .publishing_profiles import PublishingProfile, PROFILES
from .document_dna import DocumentDNA, extract_dna, quick_dna
from .semantic_chunker import SemanticChunker, SemanticChunk
from .output_converter import OutputConverter
from .verifier import QualityVerifier, VerificationResult
from .orchestrator import UniversalPublisher, PublishingJob
from .table_extractor import TableExtractor, ExtractedTable, TableCell
from .vision_reader import VisionReader, VisionDocument, PageContent

# Optional imports (require python-docx)
try:
    from .layout_preserver import LayoutPreserver, DocumentStyle, create_formatted_docx
    HAS_LAYOUT_PRESERVER = True
except ImportError:
    HAS_LAYOUT_PRESERVER = False

__version__ = "2.0.0"
__all__ = [
    "UniversalPublisher",
    "PublishingJob",
    "SemanticChunker",
    "SemanticChunk",
    "DocumentDNA",
    "extract_dna",
    "quick_dna",
    "OutputConverter",
    "PublishingProfile",
    "PROFILES",
    "QualityVerifier",
    "VerificationResult",
    # New in IMPL-004
    "TableExtractor",
    "ExtractedTable",
    "TableCell",
    "VisionReader",
    "VisionDocument",
    "PageContent",
    "LayoutPreserver",
    "DocumentStyle",
    "create_formatted_docx",
]
