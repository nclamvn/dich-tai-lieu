#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TIP-08: the bounded repair pass for suspect chunks.

Covered behavior:
- ``_translate_chunk(force_refresh=True)`` bypasses the cache GET (always
  re-translates) and skips the auto-store, while the default path is unchanged.
- ``_repair_suspect_chunks`` re-translates only quality-gate-flagged chunks,
  adopts a retry only when it is strictly better, leaves clean chunks alone,
  is bounded by ``translation_repair_max_chunks``, and best-effort overwrites
  the chunk cache with an adopted repair.

Style mirrors ``test_engine_quickwins.py``: plain functions + ``asyncio.run``
with lightweight fakes, so the real orchestrator logic runs without a network.
"""

import asyncio

import pytest

import core_v2.orchestrator as orch


# --------------------------------------------------------------------------- #
# Fakes (mirrors test_engine_quickwins.py)
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, content, truncated=False):
        self.content = content
        self.truncated = truncated
        self.usage = None


class FakeClient:
    """Records calls; returns a fixed reply (default: good Vietnamese text)."""
    def __init__(self, reply="Đây là bản dịch tiếng Việt hoàn chỉnh và rõ ràng."):
        self.reply = reply
        self.calls = []

    async def chat(self, messages, temperature=None, cache_system=False, **kw):
        self.calls.append({"messages": messages, "temperature": temperature,
                           "cache_system": cache_system})
        return _Resp(self.reply)


class FakeCache:
    def __init__(self):
        self.store = {}
        self.sets = 0
    def get(self, key):
        return self.store.get(key)
    def set(self, key, value, source_lang="", target_lang="", mode=""):
        self.store[key] = value
        self.sets += 1


class _DNA:
    has_formulas = False
    def to_context_prompt(self):
        return "DNA-CONTEXT"


class _Profile:
    def to_prompt(self):
        return "PROFILE-PROMPT"


class _Chunk:
    def __init__(self, content, index=0):
        self.content = content
        self.index = index
        self.total_chunks = 1
        self.previous_summary = ""
        self.next_preview = ""


def _make_publisher(client, cache=None):
    """Build a UniversalPublisher without running the heavy __init__."""
    p = object.__new__(orch.UniversalPublisher)
    p.llm_client = client
    p.chunk_cache = cache
    p.translation_temperature = 0.3
    p.prompt_cache_enabled = True
    p.prompt_version = "v2"
    p.max_retries = 2
    p.backoff_base = 0.0  # no real sleeping in tests
    p.backoff_cap = 0.0
    p._provider_sig = "openai"
    p._model_sig = "gpt-4o-mini"
    p._active_ledger = None
    p.glossary_max_terms = 80
    p._semaphore = asyncio.Semaphore(4)
    return p


# A clearly-Vietnamese sentence (>20 chars, has diacritics) — detected as 'vi',
# so it passes the quality gate and counts as a "clean" chunk.
_CLEAN_VI = "Đây là bản dịch tiếng Việt số {} rất tự nhiên."


# --------------------------------------------------------------------------- #
# force_refresh bypasses the cache GET and skips the auto-store
# --------------------------------------------------------------------------- #
def test_force_refresh_bypasses_cache_get_and_store():
    client = FakeClient()
    cache = FakeCache()
    pub = _make_publisher(client, cache=cache)

    key = pub._chunk_cache_key("Hello", "en", "vi", "essay")
    cache.store[key] = "CACHED-RESULT"

    # Default path: cache hit short-circuits the LLM (behavior unchanged).
    out = asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                           "en", "vi", profile_id="essay"))
    assert out == "CACHED-RESULT"
    assert len(client.calls) == 0, "default path must serve the cached value"

    # Forced refresh: GET is skipped -> the LLM IS called and returns fresh text.
    sets_before = cache.sets
    out2 = asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                            "en", "vi", profile_id="essay",
                                            force_refresh=True))
    assert out2 == client.reply
    assert len(client.calls) == 1, "force_refresh must bypass the cache GET"
    # Auto-store is skipped, so the pre-seeded value is untouched.
    assert cache.sets == sets_before, "force_refresh must skip the auto-store"
    assert cache.store[key] == "CACHED-RESULT"


# --------------------------------------------------------------------------- #
# _repair_suspect_chunks: replaces a suspect chunk, leaves clean ones alone
# --------------------------------------------------------------------------- #
def test_repair_replaces_only_suspect_chunk():
    client = FakeClient(reply="Đây là bản dịch tiếng Việt đã được sửa lại.")
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0), _Chunk("B", 1), _Chunk("C", 2)]
    translated = [_CLEAN_VI.format("một"), "", _CLEAN_VI.format("ba")]  # chunk[1] empty

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 1
    assert repaired[1] == client.reply, "suspect (empty) chunk must be repaired"
    assert repaired[0] == translated[0], "clean chunk[0] must be unchanged"
    assert repaired[2] == translated[2], "clean chunk[2] must be unchanged"
    assert len(client.calls) == 1, "only the single suspect chunk is re-translated"


# --------------------------------------------------------------------------- #
# No suspects -> same list, zero repairs, zero LLM calls
# --------------------------------------------------------------------------- #
def test_no_suspects_returns_same_list_and_no_calls():
    client = FakeClient()
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0), _Chunk("B", 1)]
    translated = [_CLEAN_VI.format("một"), _CLEAN_VI.format("hai")]

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0
    assert repaired is translated, "no suspects must return the same list object"
    assert len(client.calls) == 0, "no suspects must not call the LLM"


# --------------------------------------------------------------------------- #
# Bounded: never repairs more than translation_repair_max_chunks
# --------------------------------------------------------------------------- #
def test_repair_is_bounded_by_max_chunks(monkeypatch):
    client = FakeClient(reply="Đây là bản dịch tiếng Việt hoàn chỉnh nhé bạn.")
    pub = _make_publisher(client, cache=None)

    # Force the cap to 2 regardless of settings.
    monkeypatch.setattr(
        orch, "_cfg",
        lambda name, default: 2 if name == "translation_repair_max_chunks" else default,
    )

    chunks = [_Chunk("A", 0), _Chunk("B", 1), _Chunk("C", 2)]
    translated = ["", "", ""]  # 3 suspects, cap is 2

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 2, "must repair at most translation_repair_max_chunks"
    assert count <= len([t for t in translated if not t]), "count bounded by #suspects"
    assert repaired[0] == client.reply and repaired[1] == client.reply
    assert repaired[2] == "", "the chunk beyond the cap is left untouched"
    assert len(client.calls) == 2, "only capped-many chunks are re-translated"


# --------------------------------------------------------------------------- #
# Adopt only if strictly better: a still-suspect repair keeps the original
# --------------------------------------------------------------------------- #
def test_repair_kept_only_if_strictly_better():
    client = FakeClient(reply="")  # repair is ALSO empty -> still suspect
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0), _Chunk("B", 1)]
    translated = [_CLEAN_VI.format("một"), ""]  # chunk[1] suspect

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0, "a repair that is not strictly better must be rejected"
    assert repaired[1] == "", "the original suspect value is kept"
    assert repaired == translated
    assert len(client.calls) == 1, "the repair was still attempted once"


# --------------------------------------------------------------------------- #
# An adopted repair best-effort overwrites the chunk cache with the good result
# --------------------------------------------------------------------------- #
def test_adopted_repair_overwrites_cache():
    client = FakeClient(reply="Đây là bản dịch tiếng Việt đã sửa chữa xong.")
    cache = FakeCache()
    pub = _make_publisher(client, cache=cache)

    chunks = [_Chunk("Bello", 0)]
    translated = [""]  # suspect

    # Pre-seed the cache key with a bad value the repair should replace.
    key = pub._chunk_cache_key("Bello", "en", "vi", "essay")
    cache.store[key] = "BAD-CACHED"

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 1
    assert repaired[0] == client.reply
    assert cache.store[key] == client.reply, "cache must be overwritten with the repair"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
