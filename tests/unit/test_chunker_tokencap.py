"""Tests for TIP-06: token-cap enforcement + structure-preserving fixes.

Plain test functions (no pytest-asyncio dependency); async paths are driven with
``asyncio.run``. Run with:

    python3 -m pytest tests/unit/test_chunker_tokencap.py -o addopts="" -q
"""

import asyncio
import json

from core_v2.semantic_chunker import SemanticChunker, SemanticChunk, ChunkType
from core_v2.token_chunking import estimate_tokens


# --------------------------------------------------------------------------- #
# Minimal async LLM client stub (no unittest.mock needed).
# --------------------------------------------------------------------------- #


class _MockResponse:
    def __init__(self, content):
        self.content = content


class _MockClient:
    """Async client whose ``chat`` returns a fixed ``content`` payload."""

    def __init__(self, content):
        self._content = content

    async def chat(self, messages, response_format=None):
        return _MockResponse(self._content)


# --------------------------------------------------------------------------- #
# Mega-chunk fix: the trailing over-budget chunk must be split by _finalize.
# --------------------------------------------------------------------------- #


def test_chunk_no_mega_chunk_via_boundary_detection():
    """Boundary detection leaves a huge trailing chunk; token-cap must split it."""
    text = "A" * 1000 + "\n\n" + "B " * 20000
    chunker = SemanticChunker(llm_client=_MockClient(json.dumps([1000, 3000])))

    chunks = asyncio.run(chunker.chunk(text))

    assert len(chunks) >= 2
    for c in chunks:
        assert estimate_tokens(c.content) <= chunker.max_chunk_tokens


def test_chunk_by_boundaries_all_within_budget():
    """Direct _chunk_by_boundaries call: every chunk stays within budget."""
    text = "A" * 1000 + "\n\n" + "B " * 20000
    chunker = SemanticChunker()

    chunks = chunker._chunk_by_boundaries(text, [1000, 3000])

    assert len(chunks) >= 2
    for c in chunks:
        assert estimate_tokens(c.content) <= chunker.max_chunk_tokens


# --------------------------------------------------------------------------- #
# _enforce_token_cap direct behavior.
# --------------------------------------------------------------------------- #


def test_enforce_token_cap_splits_oversized_preserving_type():
    chunker = SemanticChunker()
    oversized = SemanticChunk(
        content="word " * 20000,
        chunk_type=ChunkType.SECTION,
        index=0,
        total_chunks=0,
        title="Big Section",
        parent_title="Parent",
    )

    result = chunker._enforce_token_cap([oversized])

    assert len(result) > 1
    for c in result:
        assert estimate_tokens(c.content) <= chunker.max_chunk_tokens
        assert c.chunk_type == ChunkType.SECTION  # metadata copied from parent
        assert c.title == "Big Section"
        assert c.parent_title == "Parent"
    # No content lost.
    assert sum(len(c.content.split()) for c in result) == 20000


def test_enforce_token_cap_keeps_under_budget_chunk_unchanged():
    chunker = SemanticChunker()
    small = SemanticChunk(
        content="A short chunk well under budget.",
        chunk_type=ChunkType.PARAGRAPH,
        index=0,
        total_chunks=0,
    )

    result = chunker._enforce_token_cap([small])

    assert len(result) == 1
    assert result[0] is small  # same object, returned unchanged


# --------------------------------------------------------------------------- #
# _simple_chunk structure preservation.
# --------------------------------------------------------------------------- #


def test_simple_chunk_preserves_newline_structure_and_words():
    chunker = SemanticChunker()
    text = "para\n\n" * 5000  # 5000 single-word paragraphs

    chunks = chunker._simple_chunk(text)

    assert len(chunks) >= 2
    # Structure preserved: at least one chunk still contains a newline
    # (not collapsed into a single space-joined blob).
    assert any("\n" in c.content for c in chunks)
    # Every word preserved.
    assert sum(len(c.content.split()) for c in chunks) == 5000
    for c in chunks:
        assert c.chunk_type == ChunkType.PARAGRAPH
        assert estimate_tokens(c.content) <= chunker.max_chunk_tokens


# --------------------------------------------------------------------------- #
# _find_chapters — REQ-35 Vietnamese lowercase numbered headings.
# --------------------------------------------------------------------------- #


def test_find_chapters_vietnamese_lowercase_numbered():
    chunker = SemanticChunker()
    text = "1. giới thiệu về máy học\n\nnội dung\n\n2. phương pháp nghiên cứu\n\nthêm"

    chapters = chunker._find_chapters(text)

    assert len(chapters) >= 2


def test_find_chapters_plain_prose_zero():
    chunker = SemanticChunker()
    chapters = chunker._find_chapters(
        "Just a plain paragraph of text without any chapter markers."
    )
    assert len(chapters) == 0


# --------------------------------------------------------------------------- #
# Regression guard: small documents stay a single chunk.
# --------------------------------------------------------------------------- #


def test_small_doc_single_chunk():
    chunker = SemanticChunker()
    chunks = asyncio.run(chunker.chunk("Short."))
    assert len(chunks) == 1
