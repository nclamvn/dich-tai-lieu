#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TIP-02: the terminology ledger wired into the live translation path.

Covers:
- REQ-04: the ledger is rendered into the CACHED system prompt (its own block).
- REQ-05: the ledger fingerprint discriminates the chunk cache key.
- REQ-06: the glossary loader degrades to empty (SQLAlchemy absent) and
          translation still runs.
- Back-compat: ``ledger=None`` reproduces the pre-ledger behavior exactly
  (no TERMINOLOGY block, cache-key fingerprint "noterms").

Plain functions + ``asyncio.run`` (no pytest-asyncio). The fakes mirror
``tests/unit/test_engine_quickwins.py`` so the real orchestrator logic runs
without any network calls. Run with::

    python3 -m pytest tests/unit/test_glossary_wiring.py -o addopts="" -q
"""

import asyncio

import core_v2.orchestrator as orch
from core_v2.orchestrator import TRANSLATION_SYSTEM
from core_v2.term_ledger import TermLedger, load_glossary_ledger


# --------------------------------------------------------------------------- #
# Minimal fakes (mirror tests/unit/test_engine_quickwins.py)
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, content, truncated=False):
        self.content = content
        self.truncated = truncated
        self.usage = None


class FakeClient:
    """Records calls; replies in Vietnamese so the language check passes."""

    def __init__(self, reply="Xin chào thế giới, đây là bản dịch tiếng Việt."):
        self.reply = reply
        self.calls = []

    async def chat(self, messages, temperature=None, cache_system=False, **kw):
        self.calls.append({"messages": messages, "temperature": temperature,
                           "cache_system": cache_system})
        return _Resp(self.reply)


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
    p.max_retries = 4
    p.backoff_base = 0.0  # no real sleeping in tests
    p.backoff_cap = 0.0
    p._provider_sig = "openai"
    p._model_sig = "gpt-4o-mini"
    p.glossary_max_terms = 80
    p._active_ledger = None
    return p


def _system_msg(client):
    """The system message content from the first recorded chat() call."""
    return client.calls[0]["messages"][0]["content"]


# --------------------------------------------------------------------------- #
# REQ-04a: TRANSLATION_SYSTEM accepts the {glossary} placeholder
# --------------------------------------------------------------------------- #
def test_translation_system_glossary_placeholder_empty():
    out = TRANSLATION_SYSTEM.format(dna_context="D", profile_prompt="P", glossary="")
    assert "{glossary}" not in out          # placeholder fully consumed
    assert "TERMINOLOGY" not in out         # nothing injected when empty
    assert "D" in out and "P" in out        # other fields still filled


def test_translation_system_glossary_placeholder_filled():
    block = (
        "TERMINOLOGY — use these EXACT target translations consistently:\n"
        "- Neural Network → Mạng nơ-ron"
    )
    out = TRANSLATION_SYSTEM.format(dna_context="D", profile_prompt="P", glossary=block)
    assert "TERMINOLOGY" in out
    assert "Mạng nơ-ron" in out
    # Injected between the profile and the math-rules section.
    assert (
        out.index("PROFILE")
        < out.index("TERMINOLOGY")
        < out.index("CRITICAL REQUIREMENTS FOR MATHEMATICAL")
    )


# --------------------------------------------------------------------------- #
# REQ-04b: _translate_chunk injects the ledger into the (cached) system prompt
# --------------------------------------------------------------------------- #
def test_translate_chunk_injects_ledger_terms():
    client = FakeClient()
    pub = _make_publisher(client)
    ledger = TermLedger()
    ledger.add("Neural Network", "Mạng nơ-ron", priority=9, provenance="glossary")

    out = asyncio.run(pub._translate_chunk(
        _Chunk("A Neural Network is here"), _DNA(), _Profile(),
        "en", "vi", profile_id="essay", ledger=ledger,
    ))

    assert out  # a translation is returned
    system_msg = _system_msg(client)
    assert "TERMINOLOGY" in system_msg
    assert "Mạng nơ-ron" in system_msg
    # The ledger rides in the SYSTEM (cacheable) message, not the user message.
    assert "TERMINOLOGY" not in client.calls[0]["messages"][1]["content"]


# --------------------------------------------------------------------------- #
# Back-compat: ledger=None reproduces the old behavior exactly
# --------------------------------------------------------------------------- #
def test_translate_chunk_no_ledger_is_backcompat():
    client = FakeClient()
    pub = _make_publisher(client)

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello"), _DNA(), _Profile(), "en", "vi", profile_id="essay",
    ))

    assert out  # still translates
    system_msg = _system_msg(client)
    assert "TERMINOLOGY" not in system_msg          # no glossary block
    assert "LaTeX" in system_msg                    # static rules preserved
    assert "Hello" in client.calls[0]["messages"][1]["content"]  # source in user msg


def test_translate_chunk_empty_ledger_injects_nothing():
    # An empty ledger is falsy => behaves exactly like ledger=None.
    client = FakeClient()
    pub = _make_publisher(client)

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello"), _DNA(), _Profile(), "en", "vi",
        profile_id="essay", ledger=TermLedger(),
    ))

    assert out
    assert "TERMINOLOGY" not in _system_msg(client)


# --------------------------------------------------------------------------- #
# REQ-05: the ledger fingerprint discriminates the chunk cache key
# --------------------------------------------------------------------------- #
def test_cache_key_differs_by_ledger_fingerprint():
    pub = _make_publisher(FakeClient())

    key_a = pub._chunk_cache_key("Hello", "en", "vi", "essay", ledger_fingerprint="aaaa")
    key_b = pub._chunk_cache_key("Hello", "en", "vi", "essay", ledger_fingerprint="bbbb")

    assert key_a is not None and key_b is not None
    assert key_a != key_b  # different terminology => different cache bucket

    # The default fingerprint reproduces the "noterms" key (pre-ledger behavior).
    assert (
        pub._chunk_cache_key("Hello", "en", "vi", "essay")
        == pub._chunk_cache_key("Hello", "en", "vi", "essay", ledger_fingerprint="noterms")
    )


def test_two_ledgers_produce_different_keys_same_chunk():
    pub = _make_publisher(FakeClient())

    led_a = TermLedger()
    led_a.add("AI", "trí tuệ nhân tạo", priority=9)
    led_b = TermLedger()
    led_b.add("AI", "AI", priority=9)  # different target => different fingerprint

    key_a = pub._chunk_cache_key("same chunk", "en", "vi", "essay",
                                 ledger_fingerprint=led_a.fingerprint())
    key_b = pub._chunk_cache_key("same chunk", "en", "vi", "essay",
                                 ledger_fingerprint=led_b.fingerprint())
    assert key_a != key_b


# --------------------------------------------------------------------------- #
# REQ-06: glossary loader degrades to empty and translation still runs
# --------------------------------------------------------------------------- #
def test_glossary_degrades_and_translation_still_runs():
    # core.glossary needs SQLAlchemy (absent here) => empty ledger, no raise.
    ledger = load_glossary_ledger(["x"], "anything about học máy")
    assert isinstance(ledger, TermLedger)
    assert len(ledger) == 0

    # Feeding that empty ledger to translation must behave like ledger=None.
    client = FakeClient()
    pub = _make_publisher(client)
    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello"), _DNA(), _Profile(), "en", "vi",
        profile_id="essay", ledger=ledger,
    ))
    assert out
    assert "TERMINOLOGY" not in _system_msg(client)


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-o", "addopts=", "-q"]))
