#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TIP-12: the Translation-Memory READ/hints path wired into the
live translation prompt.

Covers:
- Populated TM whose segment source matches the chunk's sentence: the approved
  target rides in the DYNAMIC user message (as a "TRANSLATION MEMORY" hints
  block), NOT in the cached system prefix.
- No gateway (attribute absent, or explicitly ``None``): the user message carries
  no hints block (byte-for-byte back-compat) and translation still returns.
- Inactive gateway (TMGateway over an EMPTY temp TM): zero-cost no-op — no hints
  block is injected.

Plain functions + ``asyncio.run`` (no pytest-asyncio). The fakes mirror
``tests/unit/test_engine_quickwins.py`` so the real orchestrator logic runs
without any network calls. Every test drives a REAL temp-file
``TranslationMemory`` wrapped in a REAL ``TMGateway``; temp db files (and their
WAL sidecars) are cleaned up by the ``tm_factory`` fixture. Run with::

    python3 -m pytest tests/unit/test_tm_wiring.py -o addopts="" -q
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

import core_v2.orchestrator as orch
from core.translation_memory import TranslationMemory, TMSegment
from core_v2.tm_gateway import TMGateway


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
    """Build a UniversalPublisher without running the heavy __init__.

    Deliberately does NOT set ``tm_gateway`` — so a publisher fresh from this
    helper exercises the ``getattr(self, "tm_gateway", None)`` absent-attribute
    path (back-compat). Tests that want a gateway assign ``pub.tm_gateway``.
    """
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


def _user_msg(client):
    """The user message content from the first recorded chat() call."""
    return client.calls[0]["messages"][1]["content"]


def _system_msg(client):
    """The system message content from the first recorded chat() call."""
    return client.calls[0]["messages"][0]["content"]


# --------------------------------------------------------------------------- #
# Real temp-file TM factory with full cleanup (mirrors test_tm_gateway.py)
# --------------------------------------------------------------------------- #
@pytest.fixture
def tm_factory():
    """Yield a factory that makes real temp-file TMs and cleans them all up."""
    created = []  # list of (tm, base_path)

    def _make():
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        f.close()
        tm = TranslationMemory(Path(f.name))
        created.append((tm, f.name))
        return tm

    yield _make

    for tm, path in created:
        try:
            tm.close()
        except Exception:
            pass
        # WAL journal mode leaves -wal / -shm sidecar files behind.
        for p in (path, path + "-wal", path + "-shm"):
            try:
                os.unlink(p)
            except OSError:
                pass


# --------------------------------------------------------------------------- #
# AC1: a populated TM prepends approved hints to the DYNAMIC user message
# --------------------------------------------------------------------------- #
def test_populated_tm_prepends_hints_to_user_message(tm_factory):
    tm = tm_factory()
    tm.add_segment(
        TMSegment(
            source="Hello world.",
            target="Xin chào thế giới đã duyệt.",
            source_lang="en",
            target_lang="vi",
        )
    )
    gw = TMGateway(tm=tm)
    assert gw._active is True  # non-empty TM => active gateway

    client = FakeClient()
    pub = _make_publisher(client)
    pub.tm_gateway = gw

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello world. Something else here."), _DNA(), _Profile(),
        "en", "vi", profile_id="essay",
    ))

    assert out  # a translation is still returned

    user_msg = _user_msg(client)
    # The hints block AND the approved target text ride in the user message.
    assert "TRANSLATION MEMORY" in user_msg
    assert "Xin chào thế giới đã duyệt." in user_msg
    # The source text is still present (hints are PREPENDED, not replacing it).
    assert "Hello world. Something else here." in user_msg

    # Hints are dynamic per chunk => must NOT leak into the cached system prefix.
    system_msg = _system_msg(client)
    assert "TRANSLATION MEMORY" not in system_msg
    assert "Xin chào thế giới đã duyệt." not in system_msg


# --------------------------------------------------------------------------- #
# AC2: no gateway (attribute absent, or explicit None) => back-compat prompt
# --------------------------------------------------------------------------- #
def test_absent_gateway_is_backcompat():
    # _make_publisher does not set tm_gateway => getattr returns None.
    client = FakeClient()
    pub = _make_publisher(client)
    assert not hasattr(pub, "tm_gateway")

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello world. Something else here."), _DNA(), _Profile(),
        "en", "vi", profile_id="essay",
    ))

    assert out  # translation still returns
    assert "TRANSLATION MEMORY" not in _user_msg(client)
    # Source text unchanged in the user message (byte-for-byte prior prompt).
    assert "Hello world. Something else here." in _user_msg(client)


def test_none_gateway_is_backcompat():
    client = FakeClient()
    pub = _make_publisher(client)
    pub.tm_gateway = None  # explicit None => no TM reuse.

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello world. Something else here."), _DNA(), _Profile(),
        "en", "vi", profile_id="essay",
    ))

    assert out
    assert "TRANSLATION MEMORY" not in _user_msg(client)


# --------------------------------------------------------------------------- #
# AC3: an inactive gateway (EMPTY temp TM) is a zero-cost no-op
# --------------------------------------------------------------------------- #
def test_inactive_gateway_injects_nothing(tm_factory):
    tm = tm_factory()  # empty TM => gateway inactive.
    gw = TMGateway(tm=tm)
    assert gw._active is False

    client = FakeClient()
    pub = _make_publisher(client)
    pub.tm_gateway = gw

    out = asyncio.run(pub._translate_chunk(
        _Chunk("Hello world. Something else here."), _DNA(), _Profile(),
        "en", "vi", profile_id="essay",
    ))

    assert out  # translation still returns
    assert "TRANSLATION MEMORY" not in _user_msg(client)
    assert "TRANSLATION MEMORY" not in _system_msg(client)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-o", "addopts=", "-q"]))
