"""
Translation Memory Module
Store and reuse previously translated segments.

Key components:
- TMService: Main service for TM operations
- TMRepository: Database operations
- Segmenter: Split text into segments
- Matcher: Find similar segments
"""

from .service import TMService, get_tm_service
from .matcher import TMMatcher
from .segmenter import Segmenter
from .models import TranslationMemory, TMSegment

__all__ = [
    "TMService",
    "get_tm_service",
    "TMMatcher",
    "Segmenter",
    "TranslationMemory",
    "TMSegment",
]
