#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for :mod:`core_v2.term_ledger`.

The async auto-extractor is exercised with a scripted fake client and plain
``asyncio.run`` (no pytest-asyncio dependency), so these tests run the real
logic without any network calls. Run with::

    python3 -m pytest tests/unit/test_term_ledger.py -o addopts="" -q
"""

import asyncio

from core_v2.term_ledger import (
    TermEntry,
    TermLedger,
    extract_terms,
    load_glossary_ledger,
)


# --------------------------------------------------------------------------- #
# add(): priority + empty handling
# --------------------------------------------------------------------------- #
def test_add_higher_priority_wins_on_conflict():
    ledger = TermLedger()
    ledger.add("AI", "AI-low", priority=3)
    ledger.add("AI", "AI-high", priority=8)  # higher wins
    entries = ledger.items()
    assert len(entries) == 1
    assert entries[0].target == "AI-high"
    assert entries[0].priority == 8


def test_add_tie_keeps_existing():
    ledger = TermLedger()
    ledger.add("AI", "first", priority=5)
    ledger.add("AI", "second", priority=5)  # tie -> keep existing
    assert len(ledger) == 1
    assert ledger.items()[0].target == "first"


def test_add_lower_priority_ignored():
    ledger = TermLedger()
    ledger.add("AI", "keep", priority=9)
    ledger.add("AI", "drop", priority=1)
    assert ledger.items()[0].target == "keep"


def test_add_empty_source_or_target_ignored():
    ledger = TermLedger()
    ledger.add("", "target")
    ledger.add("   ", "target")
    ledger.add("source", "")
    ledger.add("source", "   ")
    assert len(ledger) == 0
    assert bool(ledger) is False


# --------------------------------------------------------------------------- #
# merge(): glossary priority overrides auto, case-insensitive key
# --------------------------------------------------------------------------- #
def test_merge_glossary_overrides_auto():
    auto = TermLedger()
    auto.add("AI", "trí tuệ (auto)", priority=5, provenance="auto")

    glossary = TermLedger()
    # Different case on purpose: normalized key must collide with "AI".
    glossary.add("ai", "trí tuệ nhân tạo", priority=9, provenance="glossary")

    merged = auto.merge(glossary)
    assert merged is auto  # returns self for chaining
    assert len(merged) == 1
    entry = merged.items()[0]
    assert entry.target == "trí tuệ nhân tạo"
    assert entry.priority == 9
    assert entry.provenance == "glossary"


def test_merge_auto_does_not_override_glossary():
    glossary = TermLedger()
    glossary.add("API", "API", priority=9, provenance="glossary")

    auto = TermLedger()
    auto.add("api", "giao diện", priority=5, provenance="auto")

    glossary.merge(auto)  # auto must NOT win
    assert len(glossary) == 1
    assert glossary.items()[0].provenance == "glossary"
    assert glossary.items()[0].target == "API"


# --------------------------------------------------------------------------- #
# relevant_for(): diacritic/CJK-safe substring matching
# --------------------------------------------------------------------------- #
def test_relevant_for_vietnamese_multisyllable():
    ledger = TermLedger()
    ledger.add("học máy", "machine learning")
    ledger.add("mạng nơ-ron", "neural network")  # NOT in the text below

    result = ledger.relevant_for("Bài về học máy rất hay")
    sources = {e.source for e in result}
    assert "học máy" in sources
    assert "mạng nơ-ron" not in sources
    assert len(result) == 1


def test_relevant_for_cjk_term_regex_boundary_would_miss():
    # In "我在学习机器学习很有趣" every character is a word char, so a regex
    # \b机器学习\b would NOT match (no word boundary between CJK chars). A plain
    # substring test must still find it.
    ledger = TermLedger()
    ledger.add("机器学习", "machine learning")
    ledger.add("深度学习", "deep learning")  # absent from the sentence

    result = ledger.relevant_for("我在学习机器学习很有趣")
    sources = {e.source for e in result}
    assert "机器学习" in sources
    assert "深度学习" not in sources


def test_relevant_for_returns_new_ledger_and_empty_text():
    ledger = TermLedger()
    ledger.add("học máy", "machine learning")
    empty = ledger.relevant_for("")
    assert isinstance(empty, TermLedger)
    assert len(empty) == 0
    # Original is untouched.
    assert len(ledger) == 1


# --------------------------------------------------------------------------- #
# to_prompt_block(): format + cap
# --------------------------------------------------------------------------- #
def test_to_prompt_block_empty_is_empty_string():
    assert TermLedger().to_prompt_block() == ""


def test_to_prompt_block_format():
    ledger = TermLedger()
    ledger.add("machine learning", "học máy")
    block = ledger.to_prompt_block()
    assert "TERMINOLOGY" in block
    assert "machine learning → học máy" in block
    # Header + one bullet.
    assert block.splitlines()[0].startswith("TERMINOLOGY")
    assert block.count("\n- ") == 1


def test_to_prompt_block_respects_max_terms():
    ledger = TermLedger()
    # Distinct priorities so ordering is deterministic (highest first).
    ledger.add("t9", "v9", priority=9)
    ledger.add("t7", "v7", priority=7)
    ledger.add("t5", "v5", priority=5)

    block = ledger.to_prompt_block(max_terms=2)
    bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
    assert len(bullets) == 2
    # Top-priority terms are kept; the lowest is dropped.
    assert "t9 → v9" in block
    assert "t7 → v7" in block
    assert "t5" not in block


# --------------------------------------------------------------------------- #
# fingerprint(): stable / sensitive / empty
# --------------------------------------------------------------------------- #
def test_fingerprint_empty_constant():
    assert TermLedger().fingerprint() == "noterms"


def test_fingerprint_stable_for_same_content():
    a = TermLedger()
    a.add("machine learning", "học máy", priority=5)
    a.add("neural network", "mạng nơ-ron", priority=7)

    # Same content, inserted in a different order.
    b = TermLedger()
    b.add("neural network", "mạng nơ-ron", priority=7)
    b.add("machine learning", "học máy", priority=5)

    assert a.fingerprint() == b.fingerprint()
    assert len(a.fingerprint()) == 16


def test_fingerprint_changes_when_a_term_changes():
    a = TermLedger()
    a.add("machine learning", "học máy")

    b = TermLedger()
    b.add("machine learning", "máy học")  # different target

    assert a.fingerprint() != b.fingerprint()


# --------------------------------------------------------------------------- #
# Fakes for extract_terms
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeClient:
    """Returns a scripted ``content`` and records the call for assertions."""

    def __init__(self, content):
        self._content = content
        self.calls = []

    async def chat(self, messages, temperature=None, **kwargs):
        self.calls.append({"messages": messages, "temperature": temperature})
        return _FakeResp(self._content)


# --------------------------------------------------------------------------- #
# extract_terms(): valid / malformed / fenced
# --------------------------------------------------------------------------- #
def test_extract_terms_valid_json():
    content = (
        '[{"source": "machine learning", "target": "học máy"}, '
        '{"source": "neural network", "target": "mạng nơ-ron"}]'
    )
    client = _FakeClient(content)
    ledger = asyncio.run(extract_terms("some machine learning text", client, "en", "vi"))

    mapping = {e.source: e.target for e in ledger}
    assert mapping == {"machine learning": "học máy", "neural network": "mạng nơ-ron"}
    # Provenance/priority for auto-extracted terms.
    assert all(e.provenance == "auto" and e.priority == 5 for e in ledger)
    # temperature forwarded as 0.0
    assert client.calls[0]["temperature"] == 0.0
    assert client.calls[0]["messages"][0]["role"] == "user"


def test_extract_terms_malformed_returns_empty_no_raise():
    client = _FakeClient("Sorry, I cannot produce that output.")
    ledger = asyncio.run(extract_terms("text", client, "en", "vi"))
    assert len(ledger) == 0
    assert bool(ledger) is False


def test_extract_terms_strips_json_code_fences():
    content = '```json\n[{"source": "API", "target": "API"}]\n```'
    client = _FakeClient(content)
    ledger = asyncio.run(extract_terms("API docs", client, "en", "vi"))
    entries = ledger.items()
    assert len(entries) == 1
    assert entries[0].source == "API"
    assert entries[0].target == "API"


def test_extract_terms_skips_malformed_items():
    content = (
        '[{"source": "ok", "target": "tốt"}, '
        '{"source": "no-target"}, '
        '"not-an-object", '
        '{"source": 123, "target": "num"}]'
    )
    client = _FakeClient(content)
    ledger = asyncio.run(extract_terms("text", client, "en", "vi"))
    assert len(ledger) == 1
    assert ledger.items()[0].source == "ok"


# --------------------------------------------------------------------------- #
# load_glossary_ledger(): guarded degrade path
# --------------------------------------------------------------------------- #
def test_load_glossary_ledger_none_is_empty():
    ledger = load_glossary_ledger(None)
    assert isinstance(ledger, TermLedger)
    assert len(ledger) == 0


def test_load_glossary_ledger_empty_list_is_empty():
    assert len(load_glossary_ledger([])) == 0


def test_load_glossary_ledger_degrades_when_glossary_absent():
    # core.glossary requires SQLAlchemy, which is absent in this environment, so
    # the lazy import fails and both code paths must degrade to an empty ledger
    # without raising.
    with_sample = load_glossary_ledger(["x"], sample_text="anything about học máy")
    without_sample = load_glossary_ledger(["x"])
    assert isinstance(with_sample, TermLedger) and len(with_sample) == 0
    assert isinstance(without_sample, TermLedger) and len(without_sample) == 0


# --------------------------------------------------------------------------- #
# TermEntry dataclass defaults
# --------------------------------------------------------------------------- #
def test_term_entry_defaults():
    entry = TermEntry(source="s", target="t")
    assert entry.priority == 5
    assert entry.provenance == "auto"


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-o", "addopts=", "-q"]))
