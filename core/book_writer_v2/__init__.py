"""
Book Writer v2.0 - Professional Book Generation Pipeline

A complete rewrite focused on delivering EXACT page counts with high quality.

Key Features:
- Section-by-section writing (not chapter-by-chapter)
- Continuous word count tracking
- Expansion loops until target reached
- Quality gate enforcement
- 9-agent pipeline

Usage:
    from core.book_writer_v2 import BookWriterPipeline, BookWriterConfig

    config = BookWriterConfig(target_pages=300)
    pipeline = BookWriterPipeline(config)

    project = await pipeline.create_book(
        title="AI in Healthcare",
        description="A comprehensive guide...",
        target_pages=300
    )
"""

from .config import BookWriterConfig
from .models import (
    BookProject,
    BookBlueprint,
    Part,
    Chapter,
    Section,
    BookStatus,
    SectionStatus,
    WordCountTarget,
)
from .pipeline import BookWriterPipeline
from .exceptions import (
    BookWriterError,
    QualityGateFailedError,
    ExpansionLimitError,
    AgentError,
)

__version__ = "2.0.0"
__all__ = [
    # Config
    "BookWriterConfig",
    # Models
    "BookProject",
    "BookBlueprint",
    "Part",
    "Chapter",
    "Section",
    "BookStatus",
    "SectionStatus",
    "WordCountTarget",
    # Pipeline
    "BookWriterPipeline",
    # Exceptions
    "BookWriterError",
    "QualityGateFailedError",
    "ExpansionLimitError",
    "AgentError",
]
