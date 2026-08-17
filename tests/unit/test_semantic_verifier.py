#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for :mod:`core_v2.semantic_verifier`.

The async faithfulness check is exercised with scripted fake clients and plain
``asyncio.run`` (no pytest-asyncio dependency), so these tests run the real
logic without any network calls. Run with::

    python3 -m pytest tests/unit/test_semantic_verifier.py -o addopts="" -q
"""

import asyncio

from core_v2.semantic_verifier import (
    SemanticVerdict,
    _parse_verdict,
    is_unfaithful,
    verify_chunk,
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeClient:
    """Returns a scripted ``content`` and records every call for assertions."""

    def __init__(self, content):
        self._content = content
        self.calls = []

    async def chat(self, messages, temperature=None, **kwargs):
        self.calls.append(
            {"messages": messages, "temperature": temperature, "kwargs": kwargs}
        )
        return _FakeResp(self._content)


class _RaisingClient:
    """Raises on ``chat`` to exercise the fail-open path."""

    def __init__(self):
        self.calls = 0

    async def chat(self, messages, temperature=None, **kwargs):
        self.calls += 1
        raise RuntimeError("provider exploded")


# --------------------------------------------------------------------------- #
# verify_chunk(): faithful / unfaithful happy paths
# --------------------------------------------------------------------------- #
def test_verify_chunk_faithful_true():
    client = _FakeClient('{"faithful": true, "severity": "none", "issue": ""}')
    verdict = asyncio.run(
        verify_chunk("hello world", "xin chào thế giới", "en", "vi", client)
    )
    assert verdict.faithful is True
    assert verdict.severity == "none"
    assert verdict.issue == ""
    # The client was actually consulted.
    assert len(client.calls) == 1


def test_verify_chunk_unfaithful_major_sets_issue_and_is_unfaithful():
    client = _FakeClient(
        '{"faithful": false, "severity": "major", "issue": "dropped a sentence"}'
    )
    verdict = asyncio.run(
        verify_chunk("a b c d e", "a b c", "en", "vi", client)
    )
    assert verdict.faithful is False
    assert verdict.severity == "major"
    assert verdict.issue == "dropped a sentence"
    assert is_unfaithful(verdict) is True


# --------------------------------------------------------------------------- #
# verify_chunk() + is_unfaithful(): minor severity is ignored by default
# --------------------------------------------------------------------------- #
def test_verify_chunk_unfaithful_minor_gated_by_min_severity():
    client = _FakeClient(
        '{"faithful": false, "severity": "minor", "issue": "small nuance lost"}'
    )
    verdict = asyncio.run(
        verify_chunk("a b c d e", "a b c d", "en", "vi", client)
    )
    assert verdict.faithful is False
    assert verdict.severity == "minor"
    # Default floor is "major": a minor issue must NOT trigger.
    assert is_unfaithful(verdict) is False
    # Lowering the floor to "minor" makes it fire.
    assert is_unfaithful(verdict, min_severity="minor") is True


# --------------------------------------------------------------------------- #
# verify_chunk(): fail-open paths (never raise, default to faithful)
# --------------------------------------------------------------------------- #
def test_verify_chunk_malformed_content_fails_open():
    client = _FakeClient("not json at all, sorry")
    verdict = asyncio.run(verify_chunk("source", "bản dịch", "en", "vi", client))
    assert verdict.faithful is True
    assert verdict.severity == "none"
    assert verdict.issue == ""


def test_verify_chunk_client_raises_fails_open():
    client = _RaisingClient()
    # Must NOT propagate the RuntimeError.
    verdict = asyncio.run(verify_chunk("source", "bản dịch", "en", "vi", client))
    assert verdict.faithful is True
    assert verdict.severity == "none"
    assert client.calls == 1  # the call was attempted


# --------------------------------------------------------------------------- #
# verify_chunk(): JSON wrapped in code fences is parsed
# --------------------------------------------------------------------------- #
def test_verify_chunk_parses_json_code_fences():
    content = (
        "```json\n"
        '{"faithful": false, "severity": "major", "issue": "mistranslated term"}\n'
        "```"
    )
    client = _FakeClient(content)
    verdict = asyncio.run(verify_chunk("source", "bản dịch", "en", "vi", client))
    assert verdict.faithful is False
    assert verdict.severity == "major"
    assert verdict.issue == "mistranslated term"


# --------------------------------------------------------------------------- #
# verify_chunk(): empty input short-circuits without calling the client
# --------------------------------------------------------------------------- #
def test_verify_chunk_empty_source_skips_client():
    client = _FakeClient('{"faithful": false, "severity": "major", "issue": "x"}')
    verdict = asyncio.run(verify_chunk("", "bản dịch", "en", "vi", client))
    assert verdict.faithful is True
    assert verdict.severity == "none"
    # Nothing to verify -> the client must not be called.
    assert len(client.calls) == 0


def test_verify_chunk_whitespace_translated_skips_client():
    client = _FakeClient('{"faithful": false, "severity": "major", "issue": "x"}')
    verdict = asyncio.run(verify_chunk("real source", "   \n\t ", "en", "vi", client))
    assert verdict.faithful is True
    assert len(client.calls) == 0


# --------------------------------------------------------------------------- #
# verify_chunk(): temperature=0.0 is forwarded
# --------------------------------------------------------------------------- #
def test_verify_chunk_forwards_temperature_zero():
    client = _FakeClient('{"faithful": true, "severity": "none", "issue": ""}')
    asyncio.run(verify_chunk("source text", "văn bản", "en", "vi", client))
    assert client.calls[0]["temperature"] == 0.0
    # Message shape mirrors the rest of the pipeline: single user turn.
    assert client.calls[0]["messages"][0]["role"] == "user"
    assert len(client.calls[0]["messages"]) == 1


# --------------------------------------------------------------------------- #
# _parse_verdict(): bool coercion + severity clamping + defaults
# --------------------------------------------------------------------------- #
def test_parse_verdict_coerces_string_booleans():
    assert _parse_verdict('{"faithful": "no", "severity": "major"}').faithful is False
    assert _parse_verdict('{"faithful": "false", "severity": "minor"}').faithful is False
    assert _parse_verdict('{"faithful": "yes", "severity": "none"}').faithful is True
    assert _parse_verdict('{"faithful": "true", "severity": "none"}').faithful is True


def test_parse_verdict_missing_faithful_defaults_true():
    # No 'faithful' key -> fail open to faithful=True.
    verdict = _parse_verdict('{"severity": "major", "issue": "x"}')
    assert verdict.faithful is True


def test_parse_verdict_unknown_severity_clamped_to_minor():
    verdict = _parse_verdict('{"faithful": false, "severity": "catastrophic"}')
    assert verdict.severity == "minor"


def test_parse_verdict_missing_severity_defaults_none():
    verdict = _parse_verdict('{"faithful": true}')
    assert verdict.severity == "none"
    assert verdict.issue == ""


def test_parse_verdict_non_string_issue_becomes_empty():
    verdict = _parse_verdict('{"faithful": false, "severity": "major", "issue": 123}')
    assert verdict.issue == ""


def test_parse_verdict_malformed_fails_open():
    for bad in ("", "not json", "[1, 2, 3]", "{oops", "null"):
        verdict = _parse_verdict(bad)
        assert verdict.faithful is True
        assert verdict.severity == "none"
        assert verdict.issue == ""


def test_parse_verdict_slices_object_from_surrounding_prose():
    content = 'Here is my verdict: {"faithful": false, "severity": "major"} thanks!'
    verdict = _parse_verdict(content)
    assert verdict.faithful is False
    assert verdict.severity == "major"


# --------------------------------------------------------------------------- #
# is_unfaithful(): threshold logic
# --------------------------------------------------------------------------- #
def test_is_unfaithful_faithful_verdict_is_never_unfaithful():
    v = SemanticVerdict(faithful=True, severity="major", issue="ignored")
    assert is_unfaithful(v) is False
    assert is_unfaithful(v, min_severity="minor") is False


def test_is_unfaithful_severity_threshold_scale():
    major = SemanticVerdict(faithful=False, severity="major", issue="")
    minor = SemanticVerdict(faithful=False, severity="minor", issue="")
    none = SemanticVerdict(faithful=False, severity="none", issue="")

    # Default floor "major".
    assert is_unfaithful(major) is True
    assert is_unfaithful(minor) is False
    assert is_unfaithful(none) is False

    # Floor "minor".
    assert is_unfaithful(major, min_severity="minor") is True
    assert is_unfaithful(minor, min_severity="minor") is True
    assert is_unfaithful(none, min_severity="minor") is False


def test_is_unfaithful_unknown_min_severity_is_conservative():
    # Garbage floor -> treated as "major", so a minor issue does not fire.
    minor = SemanticVerdict(faithful=False, severity="minor", issue="")
    major = SemanticVerdict(faithful=False, severity="major", issue="")
    assert is_unfaithful(minor, min_severity="bogus") is False
    assert is_unfaithful(major, min_severity="bogus") is True


# --------------------------------------------------------------------------- #
# SemanticVerdict dataclass defaults
# --------------------------------------------------------------------------- #
def test_semantic_verdict_defaults():
    v = SemanticVerdict()
    assert v.faithful is True
    assert v.severity == "none"
    assert v.issue == ""


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-o", "addopts=", "-q"]))
