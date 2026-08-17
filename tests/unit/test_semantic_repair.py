#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TIP-14: the OPTIONAL semantic faithfulness pass in the repair loop.

Covered behavior of ``UniversalPublisher._repair_suspect_chunks`` when
``translation_semantic_verify_enabled`` is set:

- A deterministically-clean chunk that the semantic check judges UNFAITHFUL is
  folded into the repair loop as a ``["semantic"]`` suspect, re-translated, and
  ADOPTED when the re-translation verifies faithful; a truly-clean chunk is left
  alone.
- All-faithful chunks produce zero semantic repairs (and, with no deterministic
  issues either, the original list is returned unchanged).
- DISABLED (the default) => the semantic path never runs: a chunk that WOULD be
  flagged is never verified (zero "FAITHFUL" prompts reach the client) and the
  method behaves exactly like the deterministic-only Phase-4 pass.
- The semantic pass is BOUNDED by ``translation_semantic_verify_max``.
- A semantic suspect whose repair is ALSO unfaithful is REJECTED (original kept).

Style mirrors ``test_repair_pass.py``: plain functions + ``asyncio.run`` with
lightweight fakes, so the real orchestrator logic runs without a network.
A single SCRIPTED client serves BOTH the semantic verifies and the
re-translations by inspecting ``messages[-1]["content"]`` for the verify prompt's
"FAITHFUL" marker.

    python3 -m pytest tests/unit/test_semantic_repair.py -o addopts="" -q
"""

import asyncio

import pytest

import core_v2.orchestrator as orch


# --------------------------------------------------------------------------- #
# Fakes (mirrors test_repair_pass.py)
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, content, truncated=False):
        self.content = content
        self.truncated = truncated
        self.usage = None


class ScriptedClient:
    """One client serving BOTH semantic verifies and re-translations.

    ``chat`` inspects ``messages[-1]["content"]``:

    - If it contains ``"FAITHFUL"`` it is the ``verify_chunk`` prompt: return a
      verdict JSON. The verdict is unfaithful (major) when the prompt embeds any
      of ``unfaithful_markers`` (the marker travels inside the TRANSLATION text
      that ``verify_chunk`` interpolates), else faithful. This lets the fake
      "flip": the drifty ORIGINAL carries a marker, the repaired text does not.
    - Otherwise it is a translation request: return ``retranslation``.
    """

    def __init__(
        self,
        retranslation="Đây là bản dịch tiếng Việt đã sửa lại cho trung thành.",
        unfaithful_markers=(),
    ):
        self.retranslation = retranslation
        self.unfaithful_markers = tuple(unfaithful_markers)
        self.verify_calls = []      # prompt strings sent to the semantic check
        self.translate_calls = []   # message lists sent to re-translation

    async def chat(self, messages, temperature=None, cache_system=False, **kw):
        content = messages[-1]["content"]
        if "FAITHFUL" in content:
            self.verify_calls.append(content)
            unfaithful = any(m in content for m in self.unfaithful_markers)
            if unfaithful:
                return _Resp('{"faithful": false, "severity": "major", "issue": "drift"}')
            return _Resp('{"faithful": true, "severity": "none", "issue": ""}')
        self.translate_calls.append(messages)
        return _Resp(self.retranslation)


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


def _patch_cfg(monkeypatch, *, enabled=True, semantic_max=30, repair_max=20):
    """Force the semantic/repair knobs regardless of the real settings.

    Every other setting name falls through to its caller-supplied default, so the
    rest of the orchestrator behaves exactly as in production.
    """
    def fake_cfg(name, default):
        if name == "translation_semantic_verify_enabled":
            return enabled
        if name == "translation_semantic_verify_max":
            return semantic_max
        if name == "translation_repair_max_chunks":
            return repair_max
        return default
    monkeypatch.setattr(orch, "_cfg", fake_cfg)


# Clearly-Vietnamese sentences (>20 chars, diacritics) => detected 'vi', so they
# pass the deterministic quality gate and count as "clean" chunks. Short sources
# (< 200 chars) keep the length-ratio rule from ever firing.
_DRIFTY = "Đây là bản dịch tiếng Việt bị trôi nghĩa DRIFTORIG rõ ràng."
_FAITHFUL = "Đây là bản dịch tiếng Việt hoàn toàn trung thành nhé."


# --------------------------------------------------------------------------- #
# ENABLED: a drifty clean chunk is repaired; a faithful clean chunk is not
# --------------------------------------------------------------------------- #
def test_semantic_enabled_repairs_drifty_clean_chunk(monkeypatch):
    _patch_cfg(monkeypatch, enabled=True)
    client = ScriptedClient(
        retranslation="Đây là bản dịch tiếng Việt đã sửa lại cho trung thành.",
        unfaithful_markers=("DRIFTORIG",),
    )
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("Source A", 0), _Chunk("Source B", 1)]
    translated = [_DRIFTY, _FAITHFUL]  # both deterministically clean

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 1, "only the semantically-unfaithful chunk is repaired"
    assert repaired[0] == client.retranslation, "drifty chunk adopts the faithful repair"
    assert repaired[1] == translated[1], "the truly-faithful chunk is untouched"
    # 2 verifies on the originals + 1 verify on the adopted repair.
    assert len(client.verify_calls) == 3
    assert len(client.translate_calls) == 1, "only the one suspect chunk is re-translated"


# --------------------------------------------------------------------------- #
# ENABLED but everything is faithful -> no semantic repairs, list unchanged
# --------------------------------------------------------------------------- #
def test_semantic_enabled_all_faithful_no_repairs(monkeypatch):
    _patch_cfg(monkeypatch, enabled=True)
    client = ScriptedClient(unfaithful_markers=())  # nothing is ever unfaithful
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0), _Chunk("B", 1)]
    translated = [
        "Đây là bản dịch tiếng Việt số một rất tốt và trôi chảy.",
        "Đây là bản dịch tiếng Việt số hai rất tốt và trôi chảy.",
    ]

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0, "faithful chunks produce no semantic repairs"
    assert repaired is translated, "no suspects => the same list object is returned"
    assert len(client.verify_calls) == 2, "both clean chunks were semantically checked"
    assert len(client.translate_calls) == 0, "nothing is re-translated"


# --------------------------------------------------------------------------- #
# DISABLED (default): semantic path is skipped entirely -> Phase-4 behavior
# --------------------------------------------------------------------------- #
def test_semantic_disabled_skips_semantic_path(monkeypatch):
    _patch_cfg(monkeypatch, enabled=False)
    # This chunk WOULD be flagged if the semantic pass ran.
    client = ScriptedClient(unfaithful_markers=("DRIFTORIG",))
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0), _Chunk("B", 1)]
    translated = [_DRIFTY, _FAITHFUL]  # both deterministically clean

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0, "disabled => no repairs (matches deterministic-only Phase 4)"
    assert repaired is translated, "both det-clean => same list object, as in Phase 4"
    assert len(client.verify_calls) == 0, "the client receives ZERO 'FAITHFUL' prompts"
    assert len(client.translate_calls) == 0, "no re-translation happens"


# --------------------------------------------------------------------------- #
# BOUNDED: with a small cap, at most semantic_max verify calls happen
# --------------------------------------------------------------------------- #
def test_semantic_pass_is_bounded_by_max(monkeypatch):
    _patch_cfg(monkeypatch, enabled=True, semantic_max=2)
    client = ScriptedClient(unfaithful_markers=())  # all faithful -> no repairs
    pub = _make_publisher(client, cache=None)

    n = 5
    chunks = [_Chunk(f"S{i}", i) for i in range(n)]
    translated = [
        f"Đây là bản dịch tiếng Việt sạch sẽ và trôi chảy số {i} nhé."
        for i in range(n)
    ]

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0
    assert repaired is translated
    assert len(client.verify_calls) == 2, "semantic checks capped by semantic_verify_max"
    assert len(client.translate_calls) == 0


# --------------------------------------------------------------------------- #
# ADOPT RULE: a semantic repair that is STILL unfaithful is rejected
# --------------------------------------------------------------------------- #
def test_semantic_repair_rejected_when_still_unfaithful(monkeypatch):
    _patch_cfg(monkeypatch, enabled=True)
    # The re-translation ALSO carries a marker -> the repair verifies unfaithful,
    # so new_issues == ["semantic"] (1) is NOT < orig ["semantic"] (1) -> reject.
    client = ScriptedClient(
        retranslation="Đây là bản dịch tiếng Việt vẫn còn trôi nghĩa DRIFTFIX.",
        unfaithful_markers=("DRIFTORIG", "DRIFTFIX"),
    )
    pub = _make_publisher(client, cache=None)

    chunks = [_Chunk("A", 0)]
    translated = [_DRIFTY]  # deterministically clean, but semantically drifty

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 0, "a repair that is still unfaithful must be rejected"
    assert repaired[0] == translated[0], "the original suspect value is kept"
    assert repaired == translated
    # verify original (1) + verify the still-bad repair (1); translate attempted once.
    assert len(client.verify_calls) == 2
    assert len(client.translate_calls) == 1


# --------------------------------------------------------------------------- #
# ENABLED + a deterministic suspect coexisting with a semantic suspect: both
# repaired, merged in stable index order.
# --------------------------------------------------------------------------- #
def test_semantic_and_deterministic_suspects_merge_in_order(monkeypatch):
    _patch_cfg(monkeypatch, enabled=True)
    client = ScriptedClient(
        retranslation="Đây là bản dịch tiếng Việt đã được sửa hoàn chỉnh rồi.",
        unfaithful_markers=("DRIFTORIG",),
    )
    pub = _make_publisher(client, cache=None)

    # chunk 0: deterministic suspect (empty). chunk 1: semantic suspect (drifty).
    # chunk 2: truly clean + faithful.
    chunks = [_Chunk("A", 0), _Chunk("B", 1), _Chunk("C", 2)]
    translated = ["", _DRIFTY, _FAITHFUL]

    repaired, count = asyncio.run(pub._repair_suspect_chunks(
        chunks, translated, _DNA(), "essay", "en", "vi"))

    assert count == 2, "both the empty and the drifty chunk are repaired"
    assert repaired[0] == client.retranslation, "deterministic (empty) suspect repaired"
    assert repaired[1] == client.retranslation, "semantic (drifty) suspect repaired"
    assert repaired[2] == translated[2], "clean+faithful chunk untouched"
    # Semantic verifies: chunk 1 and chunk 2 are det-clean -> 2 origin verifies;
    # the empty chunk 0 is NOT semantically checked. Plus 1 verify on the drifty
    # chunk's adopted repair = 3 verify calls total.
    assert len(client.verify_calls) == 3
    assert len(client.translate_calls) == 2, "two suspects re-translated"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-o", "addopts=", "-q"]))
