#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TIP-10 (Vibecode Phase 5) — wiring tests for rolling cross-chunk context.

Covers the deterministic context set by SemanticChunker._finalize_chunks and the
optional LLM summary pre-pass helper on the orchestrator. Plain functions +
asyncio.run (no pytest-asyncio); run with `-o addopts=""`.
"""

import asyncio

from core_v2.semantic_chunker import SemanticChunker, SemanticChunk, ChunkType
from core_v2.context_builder import build_chunk_contexts
import core_v2.orchestrator as orch


def _chunk(content, index=0):
    return SemanticChunk(content=content, chunk_type=ChunkType.PARAGRAPH,
                         index=index, total_chunks=0)


# ------------------------------------------------------------------ #
# Deterministic context via _finalize_chunks
# ------------------------------------------------------------------ #
class TestDeterministicContextWiring:
    def test_previous_is_tail_not_head(self):
        ch = SemanticChunker()
        chunks = [_chunk("Aaa one. Aaa two."), _chunk("Bbb one. Bbb two."),
                  _chunk("Ccc one. Ccc two.")]
        ch._finalize_chunks(chunks)
        # First chunk: nothing precedes.
        assert chunks[0].previous_summary is None
        # Second chunk's "previous" is the TAIL of chunk0 (Aaa two.), not its head.
        assert "Aaa two." in chunks[1].previous_summary
        # Next-preview is the HEAD of the following chunk.
        assert "Bbb" in chunks[0].next_preview
        # Last chunk: nothing follows.
        assert chunks[2].next_preview is None

    def test_gist_covers_older_chunks(self):
        ch = SemanticChunker()
        chunks = [_chunk("Aaa one. Aaa two."), _chunk("Bbb one. Bbb two."),
                  _chunk("Ccc one. Ccc two.")]
        ch._finalize_chunks(chunks)
        # Chunk 2's preceding carries the immediate tail (Bbb two.) AND an older
        # gist mentioning chunk 0 (Aaa), without duplicating the immediate tail.
        prec = chunks[2].previous_summary
        assert "Bbb two." in prec and "Aaa" in prec
        assert prec.count("Bbb two.") == 1

    def test_edge_none_semantics_two_tiny_chunks(self):
        # Mirrors the existing semantic_chunker finalize-test expectations.
        ch = SemanticChunker()
        chunks = [_chunk("First chunk content"), _chunk("Second chunk content")]
        ch._finalize_chunks(chunks)
        assert chunks[0].previous_summary is None
        assert chunks[1].previous_summary is not None and "First" in chunks[1].previous_summary
        assert chunks[0].next_preview is not None and "Second" in chunks[0].next_preview
        assert chunks[1].next_preview is None

    def test_indices_and_totals_still_set(self):
        ch = SemanticChunker()
        chunks = [_chunk("A. B."), _chunk("C. D."), _chunk("E. F.")]
        ch._finalize_chunks(chunks)
        assert [c.index for c in chunks] == [0, 1, 2]
        assert all(c.total_chunks == 3 for c in chunks)


# ------------------------------------------------------------------ #
# Optional LLM summary pre-pass helper
# ------------------------------------------------------------------ #
class _Resp:
    def __init__(self, content):
        self.content = content


class _FakeClient:
    def __init__(self, reply="SUMMARY_X"):
        self.reply = reply
        self.calls = 0

    async def chat(self, messages, temperature=None, **kw):
        self.calls += 1
        return _Resp(self.reply)


class _RaisingClient:
    async def chat(self, messages, temperature=None, **kw):
        raise RuntimeError("boom")


def _make_publisher(client):
    p = object.__new__(orch.UniversalPublisher)
    p.llm_client = client
    p._semaphore = asyncio.Semaphore(4)
    return p


class TestSummaryPrepass:
    def test_summarize_chunks_returns_one_per_chunk(self):
        client = _FakeClient("SUMMARY_X")
        pub = _make_publisher(client)
        out = asyncio.run(pub._summarize_chunks([_chunk("alpha"), _chunk("beta")]))
        assert out == ["SUMMARY_X", "SUMMARY_X"]
        assert client.calls == 2

    def test_summaries_feed_the_gist(self):
        contents = ["Alpha one. Alpha two.", "Beta one. Beta two.", "Gamma one."]
        ctx = build_chunk_contexts(contents, summaries=["S0", "S1", "S2"], window=3)
        # Chunk 2's older-context gist uses the SUMMARY of chunk 0 (S0), not its
        # topic sentence (Alpha ...).
        assert "S0" in ctx[2][0] and "Alpha" not in ctx[2][0]

    def test_summarize_guarded_on_error(self):
        pub = _make_publisher(_RaisingClient())
        out = asyncio.run(pub._summarize_chunks([_chunk("x"), _chunk("y")]))
        assert out == ["", ""]


if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main([__file__, "-v", "-o", "addopts="]))
