#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SmartChunker - Intelligent text chunking with context preservation.

This module provides intelligent text chunking for translation workflows,
with special handling for:
- Paragraph and sentence boundary detection
- Context preservation between chunks
- STEM content protection (formulas, code blocks)
- Multi-language support (Latin, CJK)

Usage:
    from core.chunker import SmartChunker, TranslationChunk

    # Standard chunking
    chunker = SmartChunker(max_chars=2000, context_window=200)
    chunks = chunker.create_chunks(document_text)

    # STEM-aware chunking (preserves formulas/code)
    stem_chunker = SmartChunker(max_chars=2000, context_window=200, stem_mode=True)
    chunks = stem_chunker.create_chunks(latex_document)

Classes:
    TranslationChunk: Data class representing a text chunk with metadata.
    SmartChunker: Main chunking engine with context-aware splitting.

Dependencies:
    - STEM modules (optional): formula_detector, code_detector
"""

import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class TranslationChunk:
    """
    A text chunk ready for translation with context and metadata.

    Represents a segment of text that can be translated independently while
    maintaining awareness of surrounding context for coherent translations.

    Attributes:
        id: Unique identifier for this chunk (1-indexed).
        text: The main text content to translate.
        context_before: Text appearing before this chunk (for context).
        context_after: Text appearing after this chunk (for context).
        paragraph_boundaries: List of paragraph break positions within text.
        estimated_tokens: Rough token count estimate (chars / 4).
        metadata: Additional data (e.g., STEM content counts).

    Example:
        >>> chunk = TranslationChunk(
        ...     id=1,
        ...     text="Hello world.",
        ...     context_before="Introduction:",
        ...     context_after="More content..."
        ... )
        >>> print(chunk.estimated_tokens)
        3
    """
    id: int
    text: str
    context_before: str = ""
    context_after: str = ""
    overlap_char_count: int = 0  # FIX-001: Số ký tự overlap để merger biết cắt
    paragraph_boundaries: List[int] = None
    estimated_tokens: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Initialize computed fields after dataclass creation."""
        if self.paragraph_boundaries is None:
            self.paragraph_boundaries = []
        self.estimated_tokens = len(self.text) // 4


class SmartChunker:
    """
    Advanced text chunker with context preservation and STEM awareness.

    Splits large documents into translation-friendly chunks while:
    - Preserving paragraph and sentence boundaries
    - Providing surrounding context for each chunk
    - Protecting STEM content (formulas, code) from being split

    Attributes:
        max_chars: Maximum characters per chunk.
        context_window: Characters of context to include before/after.
        stem_mode: Enable STEM-aware chunking (preserves formulas/code).

    Example:
        >>> chunker = SmartChunker(max_chars=2000, context_window=200)
        >>> chunks = chunker.create_chunks(long_document)
        >>> for chunk in chunks:
        ...     print(f"Chunk {chunk.id}: {len(chunk.text)} chars")
    """

    def __init__(self, max_chars: int, context_window: int, stem_mode: bool = False):
        """
        Initialize SmartChunker.

        Args:
            max_chars: Maximum characters per chunk (recommended: 1500-3000).
            context_window: Characters of context to capture (recommended: 150-300).
            stem_mode: If True, enables STEM-aware chunking that preserves
                formulas and code blocks. Requires STEM modules.
        """
        self.max_chars = max_chars
        self.context_window = context_window
        self.stem_mode = stem_mode

        # Lazy import STEM modules only when needed
        self._formula_detector = None
        self._code_detector = None

    @property
    def formula_detector(self):
        """
        Lazy-load formula detector for STEM mode.

        Returns:
            FormulaDetector instance if stem_mode=True, else None.
        """
        if self._formula_detector is None and self.stem_mode:
            from .stem.formula_detector import FormulaDetector
            self._formula_detector = FormulaDetector()
        return self._formula_detector

    @property
    def code_detector(self):
        """
        Lazy-load code detector for STEM mode.

        Returns:
            CodeDetector instance if stem_mode=True, else None.
        """
        if self._code_detector is None and self.stem_mode:
            from .stem.code_detector import CodeDetector
            self._code_detector = CodeDetector()
        return self._code_detector

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences with multi-language support.

        Handles sentence boundaries for Latin scripts (., !, ?) and
        CJK punctuation (。, ！, ？). Merges very short sentences to
        avoid fragmentation.

        Args:
            text: Input text to split.

        Returns:
            List of sentences, with short ones merged (min 50 chars).
        """
        # Pattern cho multiple languages
        sentence_pattern = r'(?<=[.!?。！？])\s+(?=[A-Z\u4E00-\u9FFF])'
        sentences = re.split(sentence_pattern, text)

        # Merge câu quá ngắn
        merged = []
        buffer = ""
        for sent in sentences:
            if len(buffer) + len(sent) < 50:  # Min sentence length
                buffer += " " + sent if buffer else sent
            else:
                if buffer:
                    merged.append(buffer.strip())
                buffer = sent
        if buffer:
            merged.append(buffer.strip())

        return merged

    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Detects paragraph boundaries using double newlines or
        tab-indented lines.

        Args:
            text: Input text to split.

        Returns:
            List of non-empty paragraph strings.
        """
        # Multiple newlines hoặc indent = paragraph break
        paragraphs = re.split(r'\n\s*\n|\n\t+', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def create_chunks(self, text: str) -> List[TranslationChunk]:
        """
        Create translation chunks with context awareness.

        Main entry point for chunking. Routes to STEM-aware or standard
        chunking based on stem_mode setting.

        Standard chunking:
        - Splits on paragraph boundaries first
        - Falls back to sentence boundaries for long paragraphs
        - Preserves context between chunks

        STEM chunking (stem_mode=True):
        - Detects formulas and code blocks
        - Never splits protected STEM content
        - May exceed max_chars to preserve formulas

        Args:
            text: Full document text to chunk.

        Returns:
            List of TranslationChunk objects in document order.
        """
        if self.stem_mode:
            return self.create_stem_chunks(text)

        paragraphs = self.split_into_paragraphs(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_id = 1
        # FIX-001: Track overlap cho chunk tiếp theo
        pending_overlap_context = ""
        pending_overlap_char_count = 0

        for i, para in enumerate(paragraphs):
            para_length = len(para)

            # Nếu paragraph quá dài, cần split
            if para_length > self.max_chars:
                # Flush current chunk
                if current_chunk:
                    # FIX-001: Lưu overlap info trước khi flush
                    last_para_text = current_chunk[-1] if current_chunk else ""

                    chunks.append(self._build_chunk(
                        chunk_id, current_chunk, paragraphs, i-len(current_chunk), i,
                        overlap_char_count=pending_overlap_char_count
                    ))
                    chunk_id += 1

                    # FIX-001: Cập nhật overlap cho chunks tiếp theo
                    pending_overlap_context = last_para_text
                    pending_overlap_char_count = len(last_para_text)

                    current_chunk = []
                    current_length = 0

                # Split long paragraph
                sentences = self.split_into_sentences(para)
                for sent in sentences:
                    if len(sent) > self.max_chars:
                        # Ultra-long sentence - force split
                        chunks.append(TranslationChunk(
                            id=chunk_id,
                            text=sent[:self.max_chars],
                            context_before="",
                            context_after=sent[self.max_chars:self.max_chars+200]
                        ))
                        chunk_id += 1
                    else:
                        chunks.append(TranslationChunk(
                            id=chunk_id,
                            text=sent,
                            context_before=sentences[max(0, sentences.index(sent)-1)][:200] if sentences.index(sent) > 0 else "",
                            context_after=sentences[min(len(sentences)-1, sentences.index(sent)+1)][:200] if sentences.index(sent) < len(sentences)-1 else ""
                        ))
                        chunk_id += 1

            # Normal paragraph
            elif current_length + para_length > self.max_chars and current_chunk:
                # FIX-001: Lưu paragraph cuối làm context cho chunk tiếp theo
                last_para_text = current_chunk[-1] if current_chunk else ""

                # Save current chunk với pending overlap info
                chunks.append(self._build_chunk(
                    chunk_id, current_chunk, paragraphs, i-len(current_chunk), i,
                    overlap_char_count=pending_overlap_char_count
                ))
                chunk_id += 1

                # FIX-001: Cập nhật overlap cho chunk TIẾP THEO
                pending_overlap_context = last_para_text
                pending_overlap_char_count = len(last_para_text)

                # FIX-001: Start new chunk KHÔNG copy paragraph cũ
                # Chỉ paragraph mới, overlap được track riêng
                current_chunk = [para]
                current_length = len(para)
            else:
                current_chunk.append(para)
                current_length += para_length

        # Final chunk
        if current_chunk:
            chunks.append(self._build_chunk(
                chunk_id, current_chunk, paragraphs,
                len(paragraphs) - len(current_chunk), len(paragraphs),
                overlap_char_count=pending_overlap_char_count
            ))

        return chunks

    def create_stem_chunks(self, text: str) -> List[TranslationChunk]:
        """
        Create STEM-aware chunks that preserve formulas and code blocks.

        Analyzes the document for mathematical formulas and code blocks,
        then creates chunks that never split this protected content.

        Features:
        - Formulas are never split across chunks
        - Code blocks stay together
        - Chunks split at safe boundaries (paragraph/sentence)
        - May exceed max_chars if necessary to preserve STEM content
        - Metadata includes formula_count and code_count per chunk

        Args:
            text: Full document text containing STEM content.

        Returns:
            List of TranslationChunk objects with STEM metadata.

        Note:
            Falls back to standard create_chunks if STEM detectors
            are not available.
        """
        if not self.formula_detector or not self.code_detector:
            # Fallback to normal chunking if detectors not available
            return self.create_chunks(text)

        # Detect all STEM content
        formula_matches = self.formula_detector.detect_formulas(text)
        code_matches = self.code_detector.detect_code(text)

        # Create list of "protected regions" that cannot be split
        protected_regions = []
        for match in formula_matches:
            protected_regions.append((match.start, match.end, 'formula'))
        for match in code_matches:
            protected_regions.append((match.start, match.end, 'code'))

        # Sort by start position
        protected_regions.sort(key=lambda x: x[0])

        # Create chunks with awareness of protected regions
        chunks = []
        chunk_id = 1
        current_pos = 0
        current_chunk_text = ""

        while current_pos < len(text):
            # Find next safe split point
            chunk_end = min(current_pos + self.max_chars, len(text))

            # PHASE 1.7: Save original position to check for infinite loops
            chunk_start_pos = current_pos

            # Check if we're splitting inside a protected region
            split_point = self._find_safe_split_point(
                text, current_pos, chunk_end, protected_regions
            )

            # Extract chunk text
            chunk_text = text[current_pos:split_point].strip()

            if chunk_text:
                # Get context
                context_before = text[max(0, current_pos - self.context_window):current_pos] if current_pos > 0 else ""
                context_after = text[split_point:min(len(text), split_point + self.context_window)]

                # Count STEM content in this chunk
                chunk_formulas = [m for m in formula_matches if m.start >= current_pos and m.end <= split_point]
                chunk_code = [m for m in code_matches if m.start >= current_pos and m.end <= split_point]

                chunks.append(TranslationChunk(
                    id=chunk_id,
                    text=chunk_text,
                    context_before=context_before,
                    context_after=context_after,
                    metadata={
                        'stem_mode': True,
                        'formula_count': len(chunk_formulas),
                        'code_count': len(chunk_code)
                    }
                ))
                chunk_id += 1

            current_pos = split_point

            # PHASE 1.7: Fixed infinite loop check - compare against ORIGINAL position
            # Avoid infinite loop if split_point didn't advance from the original position
            if split_point == chunk_start_pos:
                current_pos += 1

        return chunks

    def _find_safe_split_point(
        self,
        text: str,
        start: int,
        proposed_end: int,
        protected_regions: List[tuple]
    ) -> int:
        """
        Find a safe split point that doesn't break STEM content.

        Ensures that formulas and code blocks are never split across
        chunks. If the proposed split falls inside a protected region,
        adjusts to either before or after the region.

        Args:
            text: Full document text.
            start: Chunk start position in text.
            proposed_end: Desired chunk end position.
            protected_regions: List of (start, end, type) tuples marking
                protected content that cannot be split.

        Returns:
            Safe split position. May be > proposed_end if necessary
            to preserve STEM content.

        Note:
            Priority order for split points:
            1. Before protected region (if possible)
            2. After protected region (may exceed max_chars)
            3. Paragraph boundary
            4. Sentence boundary
            5. Proposed end (fallback)
        """
        # PHASE 1.7: Enhanced protected region handling

        # Check for protected regions that interact with this chunk
        for region_start, region_end, region_type in protected_regions:
            region_len = region_end - region_start

            # Case 1: Proposed split is inside a protected region
            if region_start < proposed_end < region_end:
                # We're splitting inside a protected region - NEVER do this

                # Sub-case 1a: Region starts after chunk start - move split before region
                if region_start > start:
                    return region_start

                # Sub-case 1b: Region starts before chunk - include whole region
                # This may exceed max_chars, but preserving STEM content is priority
                return region_end

            # Case 2: Oversized region (longer than max_chars)
            if region_len > self.max_chars:
                # Check if this region overlaps with our chunk at all
                if not (region_end <= start or region_start >= proposed_end):
                    # Oversized region overlaps with chunk
                    # CRITICAL: Allow chunk to exceed max_chars to preserve formula
                    if region_start <= start < region_end:
                        # Chunk starts inside region - include whole region
                        return region_end
                    elif start < region_start < proposed_end:
                        # Region starts within chunk
                        # Include whole region (may exceed max_chars)
                        return region_end

        # Not in protected region, find paragraph/sentence boundary
        # Look backwards for a good split point
        search_text = text[start:proposed_end]

        # Try to split at paragraph boundary
        para_splits = [m.end() for m in re.finditer(r'\n\s*\n', search_text)]
        if para_splits:
            return start + para_splits[-1]

        # Try to split at sentence boundary
        sent_splits = [m.end() for m in re.finditer(r'[.!?]\s+', search_text)]
        if sent_splits:
            return start + sent_splits[-1]

        # No good split found, use proposed end
        return proposed_end

    def _build_chunk(self, chunk_id: int, chunk_paras: List[str],
                    all_paras: List[str], start_idx: int, end_idx: int,
                    overlap_char_count: int = 0) -> TranslationChunk:
        """
        Build a TranslationChunk from paragraphs with context.

        Args:
            chunk_id: Unique identifier for this chunk.
            chunk_paras: List of paragraphs to include in chunk.
            all_paras: Full list of all document paragraphs.
            start_idx: Index of first paragraph in chunk.
            end_idx: Index after last paragraph in chunk.
            overlap_char_count: FIX-001 - Số ký tự overlap từ chunk trước để merger biết cắt.

        Returns:
            TranslationChunk with text, context, overlap info, and paragraph boundaries.
        """
        # Get context before
        context_before = ""
        if start_idx > 0:
            prev_idx = max(0, start_idx - 1)
            context_before = all_paras[prev_idx][-self.context_window:]

        # Get context after
        context_after = ""
        if end_idx < len(all_paras):
            next_idx = min(len(all_paras) - 1, end_idx)
            context_after = all_paras[next_idx][:self.context_window]

        return TranslationChunk(
            id=chunk_id,
            text="\n\n".join(chunk_paras),
            context_before=context_before,
            context_after=context_after,
            overlap_char_count=overlap_char_count,  # FIX-001
            paragraph_boundaries=[i for i in range(len(chunk_paras))]
        )
