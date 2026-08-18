#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the engine quick-win upgrades:

QW1  temperature + env-overridable model registry
QW2  robust retry/backoff + fail-loud on permanent error
QW3  static/dynamic prompt split (prompt caching)
QW4  chunk-cache wiring with a collision-safe key

These tests use plain ``asyncio.run`` (no pytest-asyncio dependency) and a
fake LLM client, so they exercise the real orchestrator logic without any
network calls.
"""

import asyncio
import os

import pytest

from core.cache.chunk_cache import compute_chunk_key
from core_v2 import reliability
from core_v2.reliability import ChunkTranslationError, backoff_delay, is_transient_error
from ai_providers.unified_client import UnifiedLLMClient
import core_v2.orchestrator as orch


# --------------------------------------------------------------------------- #
# QW2: reliability helpers
# --------------------------------------------------------------------------- #
class TestReliability:
    def test_backoff_within_bounds(self):
        for attempt in range(6):
            d = backoff_delay(attempt, base=2.0, cap=60.0)
            assert 0.0 <= d <= min(60.0, 2.0 * (2 ** attempt))

    def test_backoff_capped(self):
        # Large attempt must never exceed the cap.
        assert backoff_delay(20, base=2.0, cap=30.0) <= 30.0

    def test_backoff_zero_base_is_zero(self):
        assert backoff_delay(5, base=0.0, cap=60.0) == 0.0

    def test_transient_rate_limit(self):
        assert is_transient_error(Exception("Error code 429: rate limit")) is True
        assert is_transient_error(Exception("Connection reset by peer")) is True
        assert is_transient_error(Exception("503 Service Unavailable")) is True

    def test_permanent_not_transient(self):
        assert is_transient_error(Exception("Invalid API key")) is False
        assert is_transient_error(Exception("credit balance is too low")) is False
        assert is_transient_error(Exception("model does not support vision")) is False

    def test_permanent_wins_over_transient(self):
        # A message with both markers must be treated as permanent.
        assert is_transient_error(Exception("401 unauthorized (invalid api key)")) is False

    def test_unknown_defaults_transient(self):
        assert is_transient_error(Exception("something weird happened")) is True

    def test_chunk_error_carries_index(self):
        err = ChunkTranslationError(7, "boom")
        assert err.chunk_index == 7 and "7" in str(err)


# --------------------------------------------------------------------------- #
# QW4: cache key is collision-safe
# --------------------------------------------------------------------------- #
class TestCacheKey:
    def test_model_discriminates(self):
        assert compute_chunk_key("t", "en", "vi", "essay", model="a") != \
               compute_chunk_key("t", "en", "vi", "essay", model="b")

    def test_profile_discriminates(self):
        assert compute_chunk_key("t", "en", "vi", "essay", profile_id="novel") != \
               compute_chunk_key("t", "en", "vi", "essay", profile_id="academic")

    def test_temperature_discriminates(self):
        assert compute_chunk_key("t", "en", "vi", "essay", temperature="0.3") != \
               compute_chunk_key("t", "en", "vi", "essay", temperature="0.9")

    def test_prompt_version_discriminates(self):
        assert compute_chunk_key("t", "en", "vi", "essay", prompt_version="v1") != \
               compute_chunk_key("t", "en", "vi", "essay", prompt_version="v2")

    def test_backward_compatible(self):
        # Existing callers that pass none of the new flags are unchanged.
        assert compute_chunk_key("t", "en", "vi", "simple") == \
               compute_chunk_key("t", "en", "vi", "simple")

    def test_stable_with_same_flags(self):
        a = compute_chunk_key("t", "en", "vi", "essay", model="m", profile_id="p",
                              temperature="0.3", prompt_version="v2")
        b = compute_chunk_key("t", "en", "vi", "essay", model="m", profile_id="p",
                              temperature="0.3", prompt_version="v2")
        assert a == b


# --------------------------------------------------------------------------- #
# QW1: unified client model registry + health TTL + rate-limit policy
# --------------------------------------------------------------------------- #
class TestUnifiedClient:
    def test_default_models_refreshed(self):
        c = UnifiedLLMClient()
        assert c.PROVIDER_CONFIG["anthropic"]["text_model"] == "claude-sonnet-4-5-20250929"
        assert c.PROVIDER_CONFIG["gemini"]["text_model"] == "gemini-2.0-flash"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_TEXT_MODEL", "claude-opus-4-8")
        monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-5")
        c = UnifiedLLMClient()
        assert c.PROVIDER_CONFIG["anthropic"]["text_model"] == "claude-opus-4-8"
        assert c.PROVIDER_CONFIG["openai"]["text_model"] == "gpt-5"

    def test_health_ttl(self, monkeypatch):
        monkeypatch.setenv("PROVIDER_HEALTH_TTL_SECONDS", "1000")
        c = UnifiedLLMClient()
        c._bench_provider("openai")
        assert c._is_benched("openai") is True
        assert "openai" in c.get_failed_providers()
        # Force expiry.
        c._benched_until["openai"] = 0.0
        assert c._is_benched("openai") is False

    def test_rate_limit_excluded_from_failover_classifier(self):
        from ai_providers.unified_client import ProviderStatus
        c = UnifiedLLMClient()
        # RATE_LIMITED is handled by in-place backoff, not the failover path.
        assert c._is_retryable_error(ProviderStatus.RATE_LIMITED) is False
        assert c._is_retryable_error(ProviderStatus.ERROR) is True


# --------------------------------------------------------------------------- #
# Fakes for orchestrator-level tests
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, content, truncated=False):
        self.content = content
        self.truncated = truncated
        self.usage = None


class FakeClient:
    """Records calls and can be scripted to fail a number of times first."""
    def __init__(self, reply="Xin chào thế giới, đây là bản dịch tiếng Việt.",
                 fail_times=0, fail_exc=None, truncated=False):
        self.reply = reply
        self.fail_times = fail_times
        self.fail_exc = fail_exc or Exception("HTTP 429 rate limit")
        self.truncated = truncated
        self.calls = []

    async def chat(self, messages, temperature=None, cache_system=False, **kw):
        self.calls.append({"messages": messages, "temperature": temperature,
                           "cache_system": cache_system})
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.fail_exc
        return _Resp(self.reply, truncated=self.truncated)


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
    p.max_retries = 4
    p.backoff_base = 0.0  # no real sleeping in tests
    p.backoff_cap = 0.0
    p._provider_sig = "openai"
    p._model_sig = "gpt-4o-mini"
    return p


# --------------------------------------------------------------------------- #
# QW1/QW3: translation forwards temperature + cache_system, split prompt
# --------------------------------------------------------------------------- #
class TestTranslateChunk:
    def test_forwards_temperature_and_cache_flag(self):
        client = FakeClient()
        pub = _make_publisher(client)
        out = asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                               "en", "vi", profile_id="essay"))
        assert "dịch" in out
        call = client.calls[0]
        assert call["temperature"] == 0.3
        assert call["cache_system"] is True
        roles = [m["role"] for m in call["messages"]]
        assert roles == ["system", "user"], "prompt must be split into system+user"
        assert "LaTeX" in call["messages"][0]["content"]      # static rules in system
        assert "Hello" in call["messages"][1]["content"]      # source text in user

    def test_permanent_error_raises_not_placeholder(self):
        client = FakeClient(fail_times=99, fail_exc=Exception("Invalid API key"))
        pub = _make_publisher(client)
        with pytest.raises(ChunkTranslationError):
            asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                             "en", "vi", profile_id="essay"))
        # Permanent error should not be retried.
        assert len(client.calls) == 1

    def test_transient_error_retries_then_succeeds(self):
        client = FakeClient(fail_times=2, fail_exc=Exception("429 too many requests"))
        pub = _make_publisher(client)
        out = asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                               "en", "vi", profile_id="essay"))
        assert "dịch" in out
        assert len(client.calls) == 3  # 2 failures + 1 success


# --------------------------------------------------------------------------- #
# QW4: chunk cache is actually used
# --------------------------------------------------------------------------- #
class TestCacheWiring:
    def test_miss_then_store(self):
        client = FakeClient()
        cache = FakeCache()
        pub = _make_publisher(client, cache=cache)
        asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                         "en", "vi", profile_id="essay"))
        assert cache.sets == 1 and len(client.calls) == 1

    def test_hit_skips_llm(self):
        client = FakeClient()
        cache = FakeCache()
        pub = _make_publisher(client, cache=cache)
        key = pub._chunk_cache_key("Hello", "en", "vi", "essay")
        cache.store[key] = "CACHED-RESULT"
        out = asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                               "en", "vi", profile_id="essay"))
        assert out == "CACHED-RESULT"
        assert len(client.calls) == 0, "cache hit must not call the LLM"

    def test_truncated_output_not_cached(self):
        client = FakeClient(truncated=True)
        cache = FakeCache()
        pub = _make_publisher(client, cache=cache)
        asyncio.run(pub._translate_chunk(_Chunk("Hello"), _DNA(), _Profile(),
                                         "en", "vi", profile_id="essay"))
        assert cache.sets == 0, "a truncated chunk must never be memoized"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
