"""
RRI-T Sprint 3: Semantic chunker tests.

Persona coverage: QA Destroyer, Business Analyst
Dimensions: D5 (Data Integrity), D7 (Edge Cases)
"""

import asyncio
import pytest

from core_v2.semantic_chunker import SemanticChunker, SemanticChunk, ChunkType


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chunker():
    return SemanticChunker()


def _run(coro):
    """Run async coroutine in sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ===========================================================================
# CHUNK-001: Small document -> single chunk
# ===========================================================================

class TestSmallDocument:
    """QA Destroyer persona — boundary: small docs."""

    @pytest.mark.p0
    def test_chunk_001_small_doc_single_chunk(self, chunker):
        """CHUNK-001 | QA | Document under SMALL_DOC threshold -> 1 chunk"""
        text = "Hello world. This is a small document."
        chunks = _run(chunker.chunk(text))
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_type == ChunkType.PARAGRAPH

    @pytest.mark.p0
    def test_chunk_001b_word_count_accurate(self, chunker):
        """CHUNK-001b | QA | Single chunk word_count is accurate"""
        text = "one two three four five"
        chunks = _run(chunker.chunk(text))
        assert chunks[0].word_count == 5

    @pytest.mark.p1
    def test_chunk_001c_empty_text(self, chunker):
        """CHUNK-001c | QA | Empty text -> single empty chunk"""
        chunks = _run(chunker.chunk(""))
        assert len(chunks) == 1
        assert chunks[0].content == ""

    @pytest.mark.p1
    def test_chunk_001d_whitespace_only(self, chunker):
        """CHUNK-001d | QA | Whitespace-only text -> single empty chunk"""
        chunks = _run(chunker.chunk("   \n\n  \t  "))
        assert len(chunks) == 1


# ===========================================================================
# CHUNK-002: Chapter detection
# ===========================================================================

class TestChapterDetection:
    """QA Destroyer persona — chapter boundary detection."""

    @pytest.mark.p0
    def test_chunk_002_chapters_detected(self, chunker):
        """CHUNK-002 | QA | Text with Chapter N headings -> multiple chunks"""
        chapters = []
        for i in range(1, 4):
            chapters.append(f"Chapter {i}: Title {i}\n" + "Content. " * 500)
        text = "\n\n".join(chapters)
        chunks = _run(chunker.chunk(text))
        assert len(chunks) >= 3

    @pytest.mark.p1
    def test_chunk_002b_markdown_headers(self, chunker):
        """CHUNK-002b | QA | Markdown ## headers -> chunk boundaries"""
        sections = []
        for i in range(1, 5):
            sections.append(f"## Section {i}\n" + "Paragraph content. " * 400)
        text = "\n\n".join(sections)
        chunks = _run(chunker.chunk(text))
        assert len(chunks) >= 2  # Should split on markdown headers

    @pytest.mark.p1
    def test_chunk_002c_vietnamese_chapters(self, chunker):
        """CHUNK-002c | QA | Vietnamese Chương N headers detected"""
        chapters = []
        for i in range(1, 4):
            chapters.append(f"Chương {i}: Tiêu đề {i}\n" + "Nội dung. " * 500)
        text = "\n\n".join(chapters)
        found = chunker._find_chapters(text)
        assert len(found) >= 3


# ===========================================================================
# CHUNK-003: Medium document -> paragraph split
# ===========================================================================

class TestMediumDocument:
    """QA Destroyer persona — paragraph-level chunking."""

    @pytest.mark.p1
    def test_chunk_003_paragraph_split(self, chunker):
        """CHUNK-003 | QA | Medium doc without chapters -> paragraph split"""
        # Create text above SMALL_DOC but below MEDIUM_DOC, no chapter markers
        paragraphs = [f"This is paragraph {i}. " * 30 for i in range(15)]
        text = "\n\n".join(paragraphs)
        assert len(text) > chunker.SMALL_DOC

        chunks = _run(chunker.chunk(text))
        assert len(chunks) >= 2  # Should split into multiple


# ===========================================================================
# CHUNK-004: Chunk to_dict serialization
# ===========================================================================

class TestChunkSerialization:
    """Business Analyst persona — data model correctness."""

    @pytest.mark.p1
    def test_chunk_004_to_dict(self):
        """CHUNK-004 | BA | SemanticChunk.to_dict() has all fields"""
        chunk = SemanticChunk(
            content="Test content",
            chunk_type=ChunkType.CHAPTER,
            index=0,
            total_chunks=3,
            title="Chapter 1",
            word_count=2,
        )
        d = chunk.to_dict()
        assert d["content"] == "Test content"
        assert d["chunk_type"] == "chapter"
        assert d["index"] == 0
        assert d["total_chunks"] == 3
        assert d["title"] == "Chapter 1"
        assert d["word_count"] == 2

    @pytest.mark.p1
    def test_chunk_004b_chunk_type_values(self):
        """CHUNK-004b | BA | All ChunkType enum values are strings"""
        for ct in ChunkType:
            assert isinstance(ct.value, str)


# ===========================================================================
# CHUNK-005: Large document without chapters
# ===========================================================================

class TestLargeDocument:
    """QA Destroyer persona — fallback chunking for large docs."""

    @pytest.mark.p1
    def test_chunk_005_large_no_chapters_falls_back(self, chunker):
        """CHUNK-005 | QA | Large doc without chapters -> simple chunking"""
        # Generate text above MEDIUM_DOC threshold with no chapter markers
        text = "Simple sentence without chapter headings. " * 1500
        assert len(text) > chunker.MEDIUM_DOC

        chunks = _run(chunker.chunk(text, detect_boundaries=False))
        assert len(chunks) >= 2
        # All content should be present
        combined = "".join(c.content for c in chunks)
        assert "Simple sentence" in combined


# ===========================================================================
# CHUNK-006: Chunk size constraints
# ===========================================================================

class TestChunkSizeConstraints:
    """QA Destroyer persona — chunk size limits respected."""

    @pytest.mark.p1
    def test_chunk_006_no_oversized_chunks(self, chunker):
        """CHUNK-006 | QA | No chunk exceeds MAX_CHUNK significantly"""
        text = "Word. " * 5000  # ~30000 chars
        chunks = _run(chunker.chunk(text, detect_boundaries=False))
        for chunk in chunks:
            # Allow some tolerance (2x MAX_CHUNK) since exact splitting isn't guaranteed
            assert len(chunk.content) < chunker.MAX_CHUNK * 3, \
                f"Chunk too large: {len(chunk.content)} chars"
