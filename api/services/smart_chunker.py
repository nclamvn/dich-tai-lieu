"""
Context-Aware Smart Chunker.

Improves chunking with 3 mechanisms:
1. OVERLAP: Each chunk carries context from the previous/next chunk
2. BOUNDARY: Split at section > paragraph > sentence boundaries (never mid-sentence)
3. CONTEXT HEADER: Each chunk gets metadata about position + key terms

Backward compatible: SmartChunk.__str__() returns plain text,
so existing pipeline code using str(chunk) or f"{chunk}" still works.

Standalone module — no extraction or translation imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 3000
DEFAULT_OVERLAP = 200
MAX_CONTEXT_HEADER = 300

# Sentence boundary patterns
SENTENCE_END = re.compile(
    r'(?<=[.!?。！？])'   # After sentence-ending punctuation
    r'(?:\s+|$)'          # Followed by whitespace or end
)

# Paragraph boundary
PARAGRAPH_BREAK = re.compile(r'\n\s*\n')

# Section heading patterns (markdown-like or numbered) — captures full line
SECTION_HEADING = re.compile(
    r'^(?:'
    r'#{1,6}\s+.+'              # Markdown headings: "# Title"
    r'|\d+\.\s+.+'             # Numbered: "1. Introduction"
    r'|[A-Z][A-Z\s]{2,}'      # ALL CAPS lines
    r'|Chapter\s+\d+.*'        # "Chapter 1"
    r'|CHAPTER\s+\d+.*'
    r'|Chương\s+\d+.*'         # Vietnamese
    r'|第[一二三四五六七八九十\d]+[章節].*'  # CJK chapters
    r')$',
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ChunkContext:
    """Context metadata attached to each chunk."""

    chunk_index: int
    total_chunks: int
    overlap_before: str
    overlap_after: str
    section_title: str
    key_terms: List[str]
    position_description: str  # "beginning" | "middle" | "end"

    def to_prompt_prefix(self) -> str:
        """Generate context string to prepend to chunk for translation.

        Format designed for LLM consumption — brief, structured,
        not wasteful of tokens.
        """
        parts = []

        parts.append(
            f"[Translating section {self.chunk_index + 1}/{self.total_chunks}"
            f" ({self.position_description})]"
        )

        if self.section_title:
            parts.append(f"[Current section: {self.section_title}]")

        if self.key_terms:
            terms_str = ", ".join(self.key_terms[:10])
            parts.append(f"[Key terms to keep consistent: {terms_str}]")

        if self.overlap_before:
            parts.append(
                f"[Previous context: ...{self.overlap_before.strip()}]"
            )

        return "\n".join(parts)


@dataclass
class SmartChunk:
    """A chunk with context — drop-in replacement for plain string.

    Backward compatible:
        str(chunk)  → chunk.text
        len(chunk)  → len(chunk.text)
    """

    text: str
    context: ChunkContext
    original_start: int = 0
    original_end: int = 0

    @property
    def text_with_context(self) -> str:
        """Text prefixed with context for LLM translation."""
        prefix = self.context.to_prompt_prefix()
        if prefix:
            return f"{prefix}\n\n---\n\n{self.text}"
        return self.text

    @property
    def translation_instruction(self) -> str:
        """Instruction to append to translation prompt."""
        return (
            "IMPORTANT: Only translate the text below the '---' separator. "
            "The context above is for reference only — do not include it "
            "in your translation output."
        )

    def __str__(self) -> str:
        return self.text

    def __len__(self) -> int:
        return len(self.text)


# ---------------------------------------------------------------------------
# Smart Chunker
# ---------------------------------------------------------------------------

class SmartChunker:
    """Context-aware document chunker.

    Usage::

        chunker = SmartChunker(chunk_size=3000, overlap=200)
        chunks = chunker.chunk(
            text="full document text...",
            glossary_terms=["Machine Learning", "Neural Network"],
        )

        for chunk in chunks:
            prompt = chunk.text_with_context   # with context
            plain = str(chunk)                 # backward compatible
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        max_context_header: int = MAX_CONTEXT_HEADER,
        respect_boundaries: bool = True,
    ):
        self.chunk_size = max(100, chunk_size)
        self.overlap = max(0, overlap)
        self.max_context_header = max_context_header
        self.respect_boundaries = respect_boundaries

    def chunk(
        self,
        text: str,
        glossary_terms: Optional[List[str]] = None,
    ) -> List[SmartChunk]:
        """Split text into context-aware chunks.

        Args:
            text: Full document text.
            glossary_terms: Important terms to track across chunks.

        Returns:
            List of SmartChunk objects with context.
        """
        if not text or not text.strip():
            return []

        # Step 1: Find raw split points respecting boundaries
        if self.respect_boundaries:
            raw_splits = self._split_at_boundaries(text)
        else:
            raw_splits = self._split_by_size(text)

        if not raw_splits:
            return []

        total = len(raw_splits)

        # Step 2: Detect section headings
        section_map = self._build_section_map(text)

        # Step 3: Track key terms across chunks
        terms_seen: List[str] = []
        glossary = glossary_terms or []

        # Step 4: Build SmartChunks with context
        chunks: List[SmartChunk] = []

        for i, (start, end, chunk_text) in enumerate(raw_splits):
            # Overlap from previous chunk
            if i > 0 and self.overlap > 0:
                prev_text = raw_splits[i - 1][2]
                overlap_before = prev_text[-self.overlap:]
            else:
                overlap_before = ""

            # Overlap from next chunk
            if i < total - 1 and self.overlap > 0:
                next_text = raw_splits[i + 1][2]
                overlap_after = next_text[: self.overlap]
            else:
                overlap_after = ""

            # Find nearest section heading
            section_title = self._find_section_for_position(section_map, start)

            # Track glossary terms found in this chunk
            new_terms = self._find_terms_in_text(chunk_text, glossary, terms_seen)
            terms_seen.extend(new_terms)

            # Position description
            if i == 0:
                position = "beginning"
            elif i == total - 1:
                position = "end"
            else:
                position = "middle"

            context = ChunkContext(
                chunk_index=i,
                total_chunks=total,
                overlap_before=overlap_before,
                overlap_after=overlap_after,
                section_title=section_title,
                key_terms=list(terms_seen[-15:]),
                position_description=position,
            )

            smart_chunk = SmartChunk(
                text=chunk_text,
                context=context,
                original_start=start,
                original_end=end,
            )
            chunks.append(smart_chunk)

        logger.info(
            "SmartChunker: %d chars → %d chunks "
            "(avg %d chars/chunk, overlap=%d, terms_tracked=%d)",
            len(text), len(chunks),
            len(text) // max(1, len(chunks)),
            self.overlap, len(terms_seen),
        )

        return chunks

    # --- Splitting Logic ---

    def _split_at_boundaries(
        self, text: str
    ) -> List[tuple]:
        """Split respecting natural boundaries.

        Priority: section > paragraph > sentence > size.
        Returns: [(start, end, text), ...]
        """
        split_points = self._find_split_points(text)

        result = []
        current_start = 0

        while current_start < len(text):
            target_end = min(current_start + self.chunk_size, len(text))

            if target_end >= len(text):
                chunk_text = text[current_start:]
                if chunk_text.strip():
                    result.append((current_start, len(text), chunk_text))
                break

            best_split = self._find_best_split(
                split_points, current_start, target_end,
            )

            if best_split is None:
                best_split = target_end

            chunk_text = text[current_start:best_split]
            if chunk_text.strip():
                result.append((current_start, best_split, chunk_text))

            current_start = best_split

        return result

    def _split_by_size(
        self, text: str
    ) -> List[tuple]:
        """Simple fixed-size splitting (fallback)."""
        result = []
        for i in range(0, len(text), self.chunk_size):
            end = min(i + self.chunk_size, len(text))
            chunk_text = text[i:end]
            if chunk_text.strip():
                result.append((i, end, chunk_text))
        return result

    def _find_split_points(
        self, text: str
    ) -> List[tuple]:
        """Find all natural split points with priority scores.

        Returns: [(position, priority), ...]
        Priority: 3=section, 2=paragraph, 1=sentence
        """
        points = []

        # Section headings (highest priority)
        for m in SECTION_HEADING.finditer(text):
            points.append((m.start(), 3))

        # Paragraph breaks
        for m in PARAGRAPH_BREAK.finditer(text):
            points.append((m.end(), 2))

        # Sentence endings
        for m in SENTENCE_END.finditer(text):
            points.append((m.end(), 1))

        points.sort(key=lambda x: x[0])
        return points

    def _find_best_split(
        self,
        split_points: List[tuple],
        chunk_start: int,
        target_end: int,
    ) -> Optional[int]:
        """Find best split point near target_end.

        Strategy:
        - Look in window [target_end - 20%, target_end + 10%]
        - Prefer higher priority splits
        - Among same priority, prefer closest to target
        """
        window_start = int(target_end - self.chunk_size * 0.2)
        window_end = int(target_end + self.chunk_size * 0.1)

        # Must be after chunk_start + minimum chunk size
        min_pos = chunk_start + int(self.chunk_size * 0.3)
        window_start = max(window_start, min_pos)

        candidates = [
            (pos, pri)
            for pos, pri in split_points
            if window_start <= pos <= window_end
        ]

        if not candidates:
            return None

        # Sort: highest priority first, then closest to target
        candidates.sort(key=lambda x: (-x[1], abs(x[0] - target_end)))

        return candidates[0][0]

    # --- Section Detection ---

    def _build_section_map(
        self, text: str
    ) -> List[tuple]:
        """Build map of (position, section_title) for the document."""
        sections = []
        for m in SECTION_HEADING.finditer(text):
            title = m.group().strip()
            title = re.sub(r'^#+\s*', '', title)
            title = title[:80]
            sections.append((m.start(), title))
        return sections

    def _find_section_for_position(
        self,
        section_map: List[tuple],
        position: int,
    ) -> str:
        """Find the section heading that contains this position."""
        current_section = ""
        for sec_pos, sec_title in section_map:
            if sec_pos <= position:
                current_section = sec_title
            else:
                break
        return current_section

    # --- Term Tracking ---

    def _find_terms_in_text(
        self,
        text: str,
        glossary: List[str],
        already_seen: List[str],
    ) -> List[str]:
        """Find glossary terms in this chunk not yet tracked."""
        text_lower = text.lower()
        new_terms = []
        for term in glossary:
            if (
                term.lower() in text_lower
                and term not in already_seen
                and term not in new_terms
            ):
                new_terms.append(term)
        return new_terms
