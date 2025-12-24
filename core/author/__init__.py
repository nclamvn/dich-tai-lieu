"""
Phase 4.1 + 4.3: Author Engine with Memory

Provides co-writing and ghostwriting capabilities:
- Co-write mode: AI proposes next paragraphs with variations
- Rewrite mode: Improve existing text
- Expand mode: Develop brief ideas into full content

Phase 4.1: Prompt-based style control (skips Phase 4.2 corpus learning)
Phase 4.3: Memory tracking for characters, timeline, plot consistency
"""

from .author_engine import AuthorEngine
from .models import AuthorProject, Variation, AuthorConfig
from .memory_store import (
    MemoryStore,
    Character,
    TimelineEvent,
    PlotPoint,
    WorldElement,
    EntityType
)
from .vector_memory import VectorMemory, MemoryChunk
from .advanced import (
    VariationScorer,
    ScoredVariation,
    MemoryContextBuilder,
    ExportUtilities
)
from .book_export import BookExporter

__all__ = [
    # Core classes
    "AuthorEngine",
    "AuthorProject",
    "Variation",
    "AuthorConfig",
    # Memory classes (Phase 4.3)
    "MemoryStore",
    "Character",
    "TimelineEvent",
    "PlotPoint",
    "WorldElement",
    "EntityType",
    "VectorMemory",
    "MemoryChunk",
    # Advanced features (Phase 4.4)
    "VariationScorer",
    "ScoredVariation",
    "MemoryContextBuilder",
    "ExportUtilities",
    "BookExporter",
]
