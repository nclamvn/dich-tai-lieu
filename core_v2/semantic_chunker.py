"""
Semantic Chunker - Claude-Aware Document Splitting

Instead of splitting at arbitrary character boundaries, we split at semantic
boundaries: chapters, sections, paragraphs. Claude helps identify boundaries
for complex documents.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any
from enum import Enum


class ChunkType(Enum):
    """Type of semantic chunk."""
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    FORMULA = "formula"
    FOOTNOTE = "footnote"
    FRONTMATTER = "frontmatter"
    BACKMATTER = "backmatter"


@dataclass
class SemanticChunk:
    """A semantically meaningful chunk of text."""

    content: str
    chunk_type: ChunkType
    index: int
    total_chunks: int

    # Metadata
    title: Optional[str] = None  # Chapter/section title if applicable
    parent_title: Optional[str] = None  # Parent chapter if this is a section

    # Position info
    char_start: int = 0
    char_end: int = 0
    word_count: int = 0

    # Context
    previous_summary: Optional[str] = None  # Summary of what came before
    next_preview: Optional[str] = None  # Preview of what comes next

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "index": self.index,
            "total_chunks": self.total_chunks,
            "title": self.title,
            "parent_title": self.parent_title,
            "word_count": self.word_count,
        }


class SemanticChunker:
    """
    Chunks documents at semantic boundaries.

    Strategy:
    1. For small documents: Keep as one chunk
    2. For medium documents: Split at paragraphs
    3. For large documents: Split at chapters/sections
    4. For complex documents: Use Claude to identify boundaries
    """

    # Thresholds (in characters)
    SMALL_DOC = 4000        # ~1000 words - keep as one
    MEDIUM_DOC = 20000      # ~5000 words - paragraph split
    LARGE_DOC = 100000      # ~25000 words - chapter split

    # Chunk size targets
    MIN_CHUNK = 1000        # Minimum chunk size
    TARGET_CHUNK = 4000     # Target chunk size
    MAX_CHUNK = 8000        # Maximum chunk size

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    async def chunk(self, text: str, detect_boundaries: bool = True) -> List[SemanticChunk]:
        """
        Chunk text into semantic units.

        Args:
            text: Full document text
            detect_boundaries: Use Claude to detect boundaries for large docs

        Returns:
            List of SemanticChunk objects
        """
        text = text.strip()
        length = len(text)

        # Small document - keep as one
        if length <= self.SMALL_DOC:
            return self._single_chunk(text)

        # Try to find chapter/section boundaries
        chapters = self._find_chapters(text)
        if chapters and len(chapters) >= 2:
            return self._chunk_by_chapters(text, chapters)

        # Try paragraph-based chunking
        if length <= self.MEDIUM_DOC:
            return self._paragraph_chunk(text)

        # Large document without clear chapters
        if detect_boundaries and self.llm_client:
            boundaries = await self._detect_boundaries_with_claude(text)
            if boundaries:
                return self._chunk_by_boundaries(text, boundaries)

        # Fallback to simple chunking
        return self._simple_chunk(text)

    def _single_chunk(self, text: str) -> List[SemanticChunk]:
        """Create a single chunk for small documents."""
        return [SemanticChunk(
            content=text,
            chunk_type=ChunkType.PARAGRAPH,
            index=0,
            total_chunks=1,
            word_count=len(text.split()),
            char_start=0,
            char_end=len(text),
        )]

    def _find_chapters(self, text: str) -> List[Tuple[int, str]]:
        """Find chapter boundaries in text."""
        patterns = [
            # English
            r'^(Chapter\s+\d+[.:]\s*.*)$',
            r'^(CHAPTER\s+\d+[.:]\s*.*)$',
            r'^(Part\s+\d+[.:]\s*.*)$',

            # Vietnamese
            r'^(Chương\s+\d+[.:]\s*.*)$',
            r'^(CHƯƠNG\s+\d+[.:]\s*.*)$',
            r'^(Phần\s+\d+[.:]\s*.*)$',

            # Numbered sections
            r'^(\d+\.\s+[A-Z].{5,50})$',

            # Markdown headers
            r'^(#{1,2}\s+.+)$',
        ]

        chapters = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                chapters.append((match.start(), match.group(1).strip()))

        # Sort by position and deduplicate
        chapters.sort(key=lambda x: x[0])
        return chapters

    def _chunk_by_chapters(self, text: str, chapters: List[Tuple[int, str]]) -> List[SemanticChunk]:
        """Chunk document by chapter boundaries."""
        chunks = []

        # Add frontmatter if there's content before first chapter
        if chapters[0][0] > 100:
            frontmatter = text[:chapters[0][0]].strip()
            if frontmatter:
                chunks.append(SemanticChunk(
                    content=frontmatter,
                    chunk_type=ChunkType.FRONTMATTER,
                    index=len(chunks),
                    total_chunks=0,  # Will update later
                    title="Frontmatter",
                    word_count=len(frontmatter.split()),
                    char_start=0,
                    char_end=chapters[0][0],
                ))

        # Process each chapter
        for i, (start, title) in enumerate(chapters):
            # Find end of this chapter
            if i + 1 < len(chapters):
                end = chapters[i + 1][0]
            else:
                end = len(text)

            content = text[start:end].strip()

            # If chapter is too large, split it further
            if len(content) > self.MAX_CHUNK:
                sub_chunks = self._split_large_section(content, title)
                for j, sub_content in enumerate(sub_chunks):
                    chunks.append(SemanticChunk(
                        content=sub_content,
                        chunk_type=ChunkType.SECTION,
                        index=len(chunks),
                        total_chunks=0,
                        title=f"{title} (part {j+1})" if len(sub_chunks) > 1 else title,
                        parent_title=title if j > 0 else None,
                        word_count=len(sub_content.split()),
                        char_start=start,
                        char_end=end,
                    ))
            else:
                chunks.append(SemanticChunk(
                    content=content,
                    chunk_type=ChunkType.CHAPTER,
                    index=len(chunks),
                    total_chunks=0,
                    title=title,
                    word_count=len(content.split()),
                    char_start=start,
                    char_end=end,
                ))

        # Update total counts and add context
        self._finalize_chunks(chunks)
        return chunks

    def _split_large_section(self, content: str, title: str) -> List[str]:
        """Split a large section into smaller parts at paragraph boundaries."""
        paragraphs = re.split(r'\n\s*\n', content)
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_size = len(para)

            # If adding this paragraph would exceed target, start new chunk
            if current_size + para_size > self.TARGET_CHUNK and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # Add remaining
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _paragraph_chunk(self, text: str) -> List[SemanticChunk]:
        """Chunk by paragraphs, combining small ones."""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_size = len(para)

            if current_size + para_size > self.TARGET_CHUNK and current_chunk:
                chunks.append(SemanticChunk(
                    content='\n\n'.join(current_chunk),
                    chunk_type=ChunkType.PARAGRAPH,
                    index=len(chunks),
                    total_chunks=0,
                    word_count=len('\n\n'.join(current_chunk).split()),
                ))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        if current_chunk:
            chunks.append(SemanticChunk(
                content='\n\n'.join(current_chunk),
                chunk_type=ChunkType.PARAGRAPH,
                index=len(chunks),
                total_chunks=0,
                word_count=len('\n\n'.join(current_chunk).split()),
            ))

        self._finalize_chunks(chunks)
        return chunks

    def _simple_chunk(self, text: str) -> List[SemanticChunk]:
        """Simple chunking when no semantic boundaries found."""
        chunks = []
        words = text.split()
        target_words = self.TARGET_CHUNK // 5  # Approximate words per chunk

        for i in range(0, len(words), target_words):
            chunk_words = words[i:i + target_words]
            content = ' '.join(chunk_words)

            chunks.append(SemanticChunk(
                content=content,
                chunk_type=ChunkType.PARAGRAPH,
                index=len(chunks),
                total_chunks=0,
                word_count=len(chunk_words),
            ))

        self._finalize_chunks(chunks)
        return chunks

    async def _detect_boundaries_with_claude(self, text: str) -> List[int]:
        """Use Claude to detect semantic boundaries in text."""
        # Sample the text
        sample_size = 10000
        if len(text) > sample_size:
            sample = text[:sample_size]
        else:
            sample = text

        prompt = f"""Analyze this document and identify the character positions where major semantic boundaries occur (chapter breaks, section breaks, topic changes).

Document sample:
{sample}

Return ONLY a JSON array of character positions where splits should occur, e.g.:
[1500, 3200, 5800]

If no clear boundaries, return empty array: []
"""

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            import json
            boundaries = json.loads(response.content)
            if isinstance(boundaries, list):
                return [b for b in boundaries if isinstance(b, int)]
        except:
            pass

        return []

    def _chunk_by_boundaries(self, text: str, boundaries: List[int]) -> List[SemanticChunk]:
        """Chunk by detected boundaries."""
        chunks = []
        boundaries = [0] + sorted(boundaries) + [len(text)]

        for i in range(len(boundaries) - 1):
            start, end = boundaries[i], boundaries[i + 1]
            content = text[start:end].strip()

            if content:
                chunks.append(SemanticChunk(
                    content=content,
                    chunk_type=ChunkType.SECTION,
                    index=len(chunks),
                    total_chunks=0,
                    word_count=len(content.split()),
                    char_start=start,
                    char_end=end,
                ))

        self._finalize_chunks(chunks)
        return chunks

    def _finalize_chunks(self, chunks: List[SemanticChunk]):
        """Update total counts and add context to chunks."""
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.total_chunks = total
            chunk.index = i

            # Add previous summary (first 100 chars of previous chunk)
            if i > 0:
                prev = chunks[i - 1].content
                chunk.previous_summary = prev[:100] + "..." if len(prev) > 100 else prev

            # Add next preview (first 100 chars of next chunk)
            if i < total - 1:
                next_chunk = chunks[i + 1].content
                chunk.next_preview = next_chunk[:100] + "..." if len(next_chunk) > 100 else next_chunk
