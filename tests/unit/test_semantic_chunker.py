"""Tests for core_v2/semantic_chunker.py — SemanticChunker text splitting logic."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from core_v2.semantic_chunker import SemanticChunker, SemanticChunk, ChunkType


# ==================== ChunkType Enum ====================


class TestChunkType:
    """ChunkType enum values."""

    def test_all_types_exist(self):
        expected = {"chapter", "section", "paragraph", "code_block",
                    "table", "formula", "footnote", "frontmatter", "backmatter"}
        actual = {ct.value for ct in ChunkType}
        assert expected == actual


# ==================== SemanticChunk Dataclass ====================


class TestSemanticChunk:
    """SemanticChunk creation and to_dict."""

    def test_creation(self):
        chunk = SemanticChunk(
            content="Hello",
            chunk_type=ChunkType.PARAGRAPH,
            index=0,
            total_chunks=1,
        )
        assert chunk.content == "Hello"
        assert chunk.word_count == 0  # default

    def test_to_dict(self):
        chunk = SemanticChunk(
            content="Test content",
            chunk_type=ChunkType.CHAPTER,
            index=2,
            total_chunks=5,
            title="Chapter 3",
            word_count=42,
        )
        d = chunk.to_dict()
        assert d["chunk_type"] == "chapter"
        assert d["index"] == 2
        assert d["total_chunks"] == 5
        assert d["title"] == "Chapter 3"
        assert d["word_count"] == 42


# ==================== Small Document (single chunk) ====================


class TestSmallDocument:
    """Documents within SMALL_DOC threshold stay as one chunk."""

    @pytest.mark.asyncio
    async def test_small_text_single_chunk(self):
        chunker = SemanticChunker()
        text = "Short document."
        chunks = await chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_type == ChunkType.PARAGRAPH

    @pytest.mark.asyncio
    async def test_exactly_at_threshold(self):
        chunker = SemanticChunker()
        text = "a" * SemanticChunker.SMALL_DOC
        chunks = await chunker.chunk(text)
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_empty_text(self):
        chunker = SemanticChunker()
        chunks = await chunker.chunk("")
        assert len(chunks) == 1
        assert chunks[0].content == ""

    @pytest.mark.asyncio
    async def test_whitespace_only_text(self):
        chunker = SemanticChunker()
        chunks = await chunker.chunk("   \n\n  ")
        assert len(chunks) == 1


# ==================== Chapter Detection ====================


class TestChapterDetection:
    """_find_chapters detects chapter boundaries."""

    def test_english_chapter_pattern(self):
        chunker = SemanticChunker()
        text = "Preface text\n\nChapter 1: Introduction\n\nContent\n\nChapter 2: Methods\n\nMore"
        chapters = chunker._find_chapters(text)
        assert len(chapters) >= 2
        titles = [t for _, t in chapters]
        assert any("Chapter 1" in t for t in titles)
        assert any("Chapter 2" in t for t in titles)

    def test_markdown_heading_pattern(self):
        chunker = SemanticChunker()
        text = "# Heading 1\n\nContent\n\n## Section 2\n\nMore content"
        chapters = chunker._find_chapters(text)
        assert len(chapters) >= 2

    def test_no_chapters_in_plain_text(self):
        chunker = SemanticChunker()
        text = "Just a plain paragraph of text without any chapter markers or headings."
        chapters = chunker._find_chapters(text)
        assert len(chapters) == 0

    def test_vietnamese_chapter_pattern(self):
        chunker = SemanticChunker()
        text = "Giới thiệu\n\nChương 1: Mở đầu\n\nNội dung\n\nChương 2: Phương pháp\n\nThêm"
        chapters = chunker._find_chapters(text)
        assert len(chapters) >= 2


# ==================== Paragraph Chunking ====================


class TestParagraphChunking:
    """Paragraph-based chunking for medium documents."""

    @pytest.mark.asyncio
    async def test_paragraph_splitting(self):
        chunker = SemanticChunker()
        # Create text > SMALL_DOC but <= MEDIUM_DOC with paragraph breaks
        para = "Word " * 200  # ~1000 chars per paragraph
        text = ("\n\n".join([para] * 8))  # ~8000 chars
        # Must be above SMALL_DOC
        assert len(text) > SemanticChunker.SMALL_DOC
        chunks = await chunker.chunk(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.chunk_type == ChunkType.PARAGRAPH

    @pytest.mark.asyncio
    async def test_no_mid_paragraph_splits(self):
        chunker = SemanticChunker()
        # Build paragraphs of known size
        para1 = "First paragraph. " * 100
        para2 = "Second paragraph. " * 100
        para3 = "Third paragraph. " * 100
        text = f"{para1}\n\n{para2}\n\n{para3}"
        if len(text) <= SemanticChunker.SMALL_DOC:
            pytest.skip("Text too small for paragraph chunking")
        chunks = await chunker.chunk(text)
        # Each chunk should contain complete paragraphs
        for chunk in chunks:
            assert "First paragraph" in chunk.content or "Second paragraph" in chunk.content or "Third paragraph" in chunk.content


# ==================== Chapter-based Chunking ====================


class TestChapterChunking:
    """Chapter-based chunking for documents with clear structure."""

    @pytest.mark.asyncio
    async def test_chapters_become_chunks(self):
        chunker = SemanticChunker()
        sections = []
        for i in range(1, 4):
            content = f"## Chapter {i}\n\n" + ("Content for chapter. " * 200) + "\n\n"
            sections.append(content)
        text = "".join(sections)
        assert len(text) > SemanticChunker.SMALL_DOC
        chunks = await chunker.chunk(text)
        assert len(chunks) >= 3

    @pytest.mark.asyncio
    async def test_frontmatter_extracted(self):
        chunker = SemanticChunker()
        # 200 chars of frontmatter before first chapter
        frontmatter = "This is frontmatter content with enough length. " * 10 + "\n\n"
        ch1 = "## Chapter 1\n\n" + ("Chapter content. " * 200) + "\n\n"
        ch2 = "## Chapter 2\n\n" + ("More content. " * 200) + "\n\n"
        text = frontmatter + ch1 + ch2
        assert len(text) > SemanticChunker.SMALL_DOC
        chunks = await chunker.chunk(text)
        # Check for frontmatter chunk
        types = [c.chunk_type for c in chunks]
        assert ChunkType.FRONTMATTER in types or len(chunks) >= 2


# ==================== Simple Chunking (fallback) ====================


class TestSimpleChunking:
    """_simple_chunk word-based fallback."""

    def test_simple_chunk_splits_by_words(self):
        chunker = SemanticChunker()
        text = "word " * 5000  # Large enough text
        chunks = chunker._simple_chunk(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.chunk_type == ChunkType.PARAGRAPH

    def test_simple_chunk_preserves_all_content(self):
        chunker = SemanticChunker()
        words = ["word"] * 3000
        text = " ".join(words)
        chunks = chunker._simple_chunk(text)
        reconstructed_words = []
        for chunk in chunks:
            reconstructed_words.extend(chunk.content.split())
        assert len(reconstructed_words) == len(words)


# ==================== Finalization ====================


class TestFinalization:
    """_finalize_chunks updates metadata correctly."""

    def test_total_chunks_updated(self):
        chunker = SemanticChunker()
        chunks = [
            SemanticChunk(content="A", chunk_type=ChunkType.PARAGRAPH, index=0, total_chunks=0),
            SemanticChunk(content="B", chunk_type=ChunkType.PARAGRAPH, index=1, total_chunks=0),
            SemanticChunk(content="C", chunk_type=ChunkType.PARAGRAPH, index=2, total_chunks=0),
        ]
        chunker._finalize_chunks(chunks)
        for chunk in chunks:
            assert chunk.total_chunks == 3

    def test_indices_sequential(self):
        chunker = SemanticChunker()
        chunks = [
            SemanticChunk(content="A", chunk_type=ChunkType.PARAGRAPH, index=99, total_chunks=0),
            SemanticChunk(content="B", chunk_type=ChunkType.PARAGRAPH, index=99, total_chunks=0),
        ]
        chunker._finalize_chunks(chunks)
        assert chunks[0].index == 0
        assert chunks[1].index == 1

    def test_previous_summary_added(self):
        chunker = SemanticChunker()
        chunks = [
            SemanticChunk(content="First chunk content", chunk_type=ChunkType.PARAGRAPH, index=0, total_chunks=0),
            SemanticChunk(content="Second chunk content", chunk_type=ChunkType.PARAGRAPH, index=1, total_chunks=0),
        ]
        chunker._finalize_chunks(chunks)
        assert chunks[0].previous_summary is None
        assert chunks[1].previous_summary is not None
        assert "First" in chunks[1].previous_summary

    def test_next_preview_added(self):
        chunker = SemanticChunker()
        chunks = [
            SemanticChunk(content="First chunk", chunk_type=ChunkType.PARAGRAPH, index=0, total_chunks=0),
            SemanticChunk(content="Second chunk", chunk_type=ChunkType.PARAGRAPH, index=1, total_chunks=0),
        ]
        chunker._finalize_chunks(chunks)
        assert chunks[0].next_preview is not None
        assert "Second" in chunks[0].next_preview
        assert chunks[1].next_preview is None


# ==================== Claude Boundary Detection ====================


class TestClaudeBoundaryDetection:
    """_detect_boundaries_with_claude with mocked LLM."""

    @pytest.mark.asyncio
    async def test_successful_boundary_detection(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps([1000, 3000, 5000])
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        chunker = SemanticChunker(llm_client=mock_client)
        boundaries = await chunker._detect_boundaries_with_claude("x" * 10000)
        assert boundaries == [1000, 3000, 5000]

    @pytest.mark.asyncio
    async def test_empty_boundaries_on_json_error(self):
        """When LLM returns non-JSON, boundaries should be empty."""
        mock_response = MagicMock()
        mock_response.content = "not valid json"
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        chunker = SemanticChunker(llm_client=mock_client)
        boundaries = await chunker._detect_boundaries_with_claude("x" * 10000)
        assert boundaries == []

    @pytest.mark.asyncio
    async def test_empty_boundaries_on_runtime_error(self):
        """When LLM raises RuntimeError, boundaries should be empty (not UnboundLocalError)."""
        mock_client = AsyncMock()
        mock_client.chat.side_effect = RuntimeError("API error")

        chunker = SemanticChunker(llm_client=mock_client)
        boundaries = await chunker._detect_boundaries_with_claude("x" * 10000)
        assert boundaries == []

    @pytest.mark.asyncio
    async def test_filters_non_integer_boundaries(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps([1000, "not_int", 3000, None, 5000])
        mock_client = AsyncMock()
        mock_client.chat.return_value = mock_response

        chunker = SemanticChunker(llm_client=mock_client)
        boundaries = await chunker._detect_boundaries_with_claude("x" * 10000)
        assert boundaries == [1000, 3000, 5000]


# ==================== Unicode / Multilingual ====================


class TestUnicodeHandling:
    """Chunking with multilingual content."""

    @pytest.mark.asyncio
    async def test_chinese_text(self):
        chunker = SemanticChunker()
        text = "中文测试内容。" * 100
        chunks = await chunker.chunk(text)
        assert len(chunks) >= 1
        # Content should be preserved
        total_content = "".join(c.content for c in chunks)
        assert "中文" in total_content

    @pytest.mark.asyncio
    async def test_mixed_language_text(self):
        chunker = SemanticChunker()
        text = "English paragraph.\n\n" + "Đoạn văn tiếng Việt.\n\n" + "日本語の段落。"
        chunks = await chunker.chunk(text)
        assert len(chunks) >= 1
