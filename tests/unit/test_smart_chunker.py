"""
Unit tests for api/services/smart_chunker.py — SmartChunker.

Target: 90%+ coverage of SmartChunker, SmartChunk, ChunkContext.
"""

import pytest

from api.services.smart_chunker import (
    SmartChunker,
    SmartChunk,
    ChunkContext,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    SENTENCE_END,
    PARAGRAPH_BREAK,
    SECTION_HEADING,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text(n_chars: int, word: str = "word") -> str:
    """Generate text of roughly n_chars with sentence boundaries."""
    sentence = f"This is a {word} sentence. "
    repeats = max(1, n_chars // len(sentence))
    return sentence * repeats


def _make_paragraphs(n: int, para_size: int = 200) -> str:
    """Generate text with n paragraph breaks."""
    para = "This is a paragraph with enough content to be meaningful. " * (para_size // 60)
    return ("\n\n".join([para] * n))


# ---------------------------------------------------------------------------
# SmartChunker — basic
# ---------------------------------------------------------------------------

class TestSmartChunkerBasic:
    def test_empty_text(self):
        chunker = SmartChunker()
        assert chunker.chunk("") == []

    def test_whitespace_only(self):
        chunker = SmartChunker()
        assert chunker.chunk("   \n\t  ") == []

    def test_none_text(self):
        chunker = SmartChunker()
        assert chunker.chunk(None) == []

    def test_short_text_single_chunk(self):
        chunker = SmartChunker(chunk_size=3000)
        chunks = chunker.chunk("Hello world. This is short text.")
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world. This is short text."

    def test_long_text_multiple_chunks(self):
        chunker = SmartChunker(chunk_size=200)
        text = _make_text(1000)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 3

    def test_chunk_count_reasonable(self):
        chunker = SmartChunker(chunk_size=3000)
        text = _make_text(10000)
        chunks = chunker.chunk(text)
        # 10000 / 3000 ≈ 3-4 chunks
        assert 2 <= len(chunks) <= 6

    def test_all_text_covered(self):
        """Total chunk text should cover all original text."""
        chunker = SmartChunker(chunk_size=200, overlap=0)
        text = _make_text(1000)
        chunks = chunker.chunk(text)
        reassembled = "".join(c.text for c in chunks)
        assert reassembled == text

    def test_custom_chunk_size(self):
        chunker = SmartChunker(chunk_size=500, overlap=0)
        text = _make_text(2000)
        chunks = chunker.chunk(text)
        # Each chunk should be <= chunk_size (approximately, due to boundary respect)
        for c in chunks:
            assert len(c.text) <= 700  # Allow some slack for boundary respect

    def test_minimum_chunk_size_enforced(self):
        chunker = SmartChunker(chunk_size=10)
        assert chunker.chunk_size == 100  # Enforced minimum


# ---------------------------------------------------------------------------
# Boundary respect
# ---------------------------------------------------------------------------

class TestBoundaryRespect:
    def test_split_at_paragraph(self):
        chunker = SmartChunker(chunk_size=300, overlap=0)
        text = _make_paragraphs(5, para_size=200)
        chunks = chunker.chunk(text)
        # Chunks should generally end at paragraph breaks
        for c in chunks[:-1]:  # All but last
            # Text should end near a paragraph break (whitespace)
            assert c.text.rstrip().endswith(".")

    def test_split_at_sentence(self):
        chunker = SmartChunker(chunk_size=100, overlap=0)
        text = "First sentence here. Second sentence follows. Third is longer one. Fourth comes next. Fifth ends it."
        chunks = chunker.chunk(text)
        # Should not split mid-sentence when possible
        for c in chunks:
            stripped = c.text.strip()
            if stripped:
                assert stripped[-1] in ".!?", f"Chunk doesn't end at sentence: '{stripped[-20:]}'"

    def test_section_heading_boundary(self):
        chunker = SmartChunker(chunk_size=300, overlap=0)
        text = (
            "Introduction paragraph with enough text. " * 5
            + "\n\n# Methods\n\n"
            + "Methods paragraph with enough text. " * 5
            + "\n\n# Results\n\n"
            + "Results paragraph with enough text. " * 5
        )
        chunks = chunker.chunk(text)
        # At least one chunk should start with or contain "# Methods"
        method_chunks = [c for c in chunks if "# Methods" in c.text]
        assert len(method_chunks) >= 1

    def test_force_split_no_boundaries(self):
        """Very long text without any boundaries → force split by size."""
        chunker = SmartChunker(chunk_size=200, overlap=0, respect_boundaries=False)
        text = "a" * 1000
        chunks = chunker.chunk(text)
        assert len(chunks) == 5  # 1000/200 = 5

    def test_respect_boundaries_false(self):
        chunker = SmartChunker(chunk_size=100, overlap=0, respect_boundaries=False)
        text = "x" * 350
        chunks = chunker.chunk(text)
        assert len(chunks) == 4  # 350/100 = 3.5 → 4 chunks


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------

class TestOverlap:
    def test_overlap_present(self):
        chunker = SmartChunker(chunk_size=200, overlap=50)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        # Second chunk should have overlap_before from first chunk
        assert chunks[1].context.overlap_before != ""

    def test_first_chunk_no_overlap_before(self):
        chunker = SmartChunker(chunk_size=200, overlap=50)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        assert chunks[0].context.overlap_before == ""

    def test_last_chunk_no_overlap_after(self):
        chunker = SmartChunker(chunk_size=200, overlap=50)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        assert chunks[-1].context.overlap_after == ""

    def test_overlap_size(self):
        chunker = SmartChunker(chunk_size=200, overlap=50)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        for c in chunks:
            assert len(c.context.overlap_before) <= 50
            assert len(c.context.overlap_after) <= 50

    def test_zero_overlap(self):
        chunker = SmartChunker(chunk_size=200, overlap=0)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        for c in chunks:
            assert c.context.overlap_before == ""
            assert c.context.overlap_after == ""

    def test_overlap_content_matches(self):
        """Overlap text should match end/start of adjacent chunks."""
        chunker = SmartChunker(chunk_size=200, overlap=30)
        text = _make_text(800)
        chunks = chunker.chunk(text)
        if len(chunks) >= 2:
            # overlap_before of chunk[1] = end of chunk[0]
            assert chunks[1].context.overlap_before == chunks[0].text[-30:]


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class TestContext:
    def test_chunk_index_sequential(self):
        chunker = SmartChunker(chunk_size=200)
        text = _make_text(1000)
        chunks = chunker.chunk(text)
        for i, c in enumerate(chunks):
            assert c.context.chunk_index == i

    def test_total_chunks_correct(self):
        chunker = SmartChunker(chunk_size=200)
        text = _make_text(1000)
        chunks = chunker.chunk(text)
        total = len(chunks)
        for c in chunks:
            assert c.context.total_chunks == total

    def test_position_description(self):
        chunker = SmartChunker(chunk_size=200)
        text = _make_text(1000)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 3
        assert chunks[0].context.position_description == "beginning"
        assert chunks[-1].context.position_description == "end"
        for c in chunks[1:-1]:
            assert c.context.position_description == "middle"

    def test_single_chunk_position(self):
        chunker = SmartChunker(chunk_size=5000)
        chunks = chunker.chunk("Short text.")
        assert len(chunks) == 1
        # Single chunk is both beginning and end → position_description = "beginning"
        assert chunks[0].context.position_description == "beginning"

    def test_two_chunks_position(self):
        chunker = SmartChunker(chunk_size=100, overlap=0)
        text = _make_text(300)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        assert chunks[0].context.position_description == "beginning"
        assert chunks[-1].context.position_description == "end"

    def test_section_title_detected(self):
        chunker = SmartChunker(chunk_size=200, overlap=0)
        text = "# Introduction\n\n" + _make_text(500) + "\n\n# Methods\n\n" + _make_text(500)
        chunks = chunker.chunk(text)
        # Some chunks should have section titles
        titles = [c.context.section_title for c in chunks if c.context.section_title]
        assert len(titles) >= 1

    def test_key_terms_tracked(self):
        chunker = SmartChunker(chunk_size=200)
        text = "Machine Learning is great. " * 20 + "Neural Network is also great. " * 20
        chunks = chunker.chunk(text, glossary_terms=["Machine Learning", "Neural Network"])
        # Last chunk should have accumulated terms
        last = chunks[-1]
        assert "Machine Learning" in last.context.key_terms

    def test_key_terms_no_duplicates(self):
        chunker = SmartChunker(chunk_size=200)
        text = "Machine Learning appears here. " * 30
        chunks = chunker.chunk(text, glossary_terms=["Machine Learning"])
        # Term should appear only once in key_terms
        for c in chunks:
            assert c.context.key_terms.count("Machine Learning") <= 1

    def test_no_glossary_terms(self):
        chunker = SmartChunker(chunk_size=200)
        text = _make_text(500)
        chunks = chunker.chunk(text)
        for c in chunks:
            assert c.context.key_terms == []


# ---------------------------------------------------------------------------
# ChunkContext.to_prompt_prefix
# ---------------------------------------------------------------------------

class TestPromptPrefix:
    def test_format(self):
        ctx = ChunkContext(
            chunk_index=2,
            total_chunks=5,
            overlap_before="...previous text",
            overlap_after="next text...",
            section_title="Methods",
            key_terms=["Machine Learning", "AI"],
            position_description="middle",
        )
        prefix = ctx.to_prompt_prefix()
        assert "[Translating section 3/5 (middle)]" in prefix
        assert "[Current section: Methods]" in prefix
        assert "Machine Learning" in prefix
        assert "previous text" in prefix

    def test_no_section_no_terms(self):
        ctx = ChunkContext(
            chunk_index=0, total_chunks=1,
            overlap_before="", overlap_after="",
            section_title="", key_terms=[],
            position_description="beginning",
        )
        prefix = ctx.to_prompt_prefix()
        assert "[Translating section 1/1 (beginning)]" in prefix
        assert "section:" not in prefix.lower() or "Current section" not in prefix

    def test_terms_limited_to_10(self):
        ctx = ChunkContext(
            chunk_index=0, total_chunks=1,
            overlap_before="", overlap_after="",
            section_title="", key_terms=[f"term{i}" for i in range(20)],
            position_description="beginning",
        )
        prefix = ctx.to_prompt_prefix()
        # Should only include first 10 terms
        assert "term9" in prefix
        assert "term10" not in prefix


# ---------------------------------------------------------------------------
# SmartChunk
# ---------------------------------------------------------------------------

class TestSmartChunk:
    def _make_chunk(self, text="Hello world", index=0, total=1):
        ctx = ChunkContext(
            chunk_index=index, total_chunks=total,
            overlap_before="", overlap_after="",
            section_title="", key_terms=[],
            position_description="beginning",
        )
        return SmartChunk(text=text, context=ctx)

    def test_str_returns_text(self):
        chunk = self._make_chunk("Hello world")
        assert str(chunk) == "Hello world"

    def test_len_returns_text_length(self):
        chunk = self._make_chunk("Hello world")
        assert len(chunk) == 11

    def test_text_with_context(self):
        ctx = ChunkContext(
            chunk_index=0, total_chunks=3,
            overlap_before="...prev", overlap_after="",
            section_title="Intro", key_terms=["AI"],
            position_description="beginning",
        )
        chunk = SmartChunk(text="Main content here.", context=ctx)
        twc = chunk.text_with_context
        assert "---" in twc
        assert "Main content here." in twc
        assert "Translating section" in twc

    def test_text_with_context_no_prefix(self):
        """When context produces empty prefix, just return text."""
        ctx = ChunkContext(
            chunk_index=0, total_chunks=1,
            overlap_before="", overlap_after="",
            section_title="", key_terms=[],
            position_description="beginning",
        )
        chunk = SmartChunk(text="Just text.", context=ctx)
        # Even with minimal context, there's still position info
        assert "Just text." in chunk.text_with_context

    def test_translation_instruction(self):
        chunk = self._make_chunk()
        assert "Only translate" in chunk.translation_instruction
        assert "---" in chunk.translation_instruction

    def test_original_offsets(self):
        ctx = ChunkContext(
            chunk_index=0, total_chunks=1,
            overlap_before="", overlap_after="",
            section_title="", key_terms=[],
            position_description="beginning",
        )
        chunk = SmartChunk(text="test", context=ctx, original_start=10, original_end=14)
        assert chunk.original_start == 10
        assert chunk.original_end == 14


# ---------------------------------------------------------------------------
# CJK support
# ---------------------------------------------------------------------------

class TestCJK:
    def test_japanese_sentence_boundaries(self):
        chunker = SmartChunker(chunk_size=100, overlap=0)
        text = "これは日本語のテストです。次の文も日本語です。さらに続きます。" * 5
        chunks = chunker.chunk(text)
        # Should split at 。boundaries
        assert len(chunks) >= 1

    def test_chinese_chapter_headings(self):
        chunker = SmartChunker(chunk_size=200, overlap=0)
        text = "第一章\n\n" + "中文内容。" * 30 + "\n\n第二章\n\n" + "更多内容。" * 30
        chunks = chunker.chunk(text)
        # Should detect 第一章 as section heading
        titles = [c.context.section_title for c in chunks if c.context.section_title]
        assert any("第一章" in t for t in titles)

    def test_vietnamese_chapter_headings(self):
        chunker = SmartChunker(chunk_size=200, overlap=0)
        text = "Chương 1\n\n" + "Nội dung tiếng Việt. " * 20 + "\n\nChương 2\n\n" + "Thêm nội dung. " * 20
        chunks = chunker.chunk(text)
        titles = [c.context.section_title for c in chunks if c.context.section_title]
        assert any("Chương" in t for t in titles)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestPatterns:
    def test_sentence_end_pattern(self):
        text = "First sentence. Second sentence! Third? "
        matches = list(SENTENCE_END.finditer(text))
        assert len(matches) >= 2

    def test_paragraph_break_pattern(self):
        text = "Paragraph one.\n\nParagraph two.\n\n\nParagraph three."
        matches = list(PARAGRAPH_BREAK.finditer(text))
        assert len(matches) >= 2

    def test_section_heading_markdown(self):
        text = "# Title\n## Subtitle\n### Sub-sub"
        matches = list(SECTION_HEADING.finditer(text))
        assert len(matches) >= 2

    def test_section_heading_numbered(self):
        text = "1. Introduction\n2. Methods"
        matches = list(SECTION_HEADING.finditer(text))
        assert len(matches) >= 1
