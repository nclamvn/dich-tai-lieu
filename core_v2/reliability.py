"""
Reliability helpers for the core_v2 translation pipeline.

Small, dependency-free utilities so they can be unit-tested in isolation and
reused by the orchestrator:

- ``ChunkTranslationError`` — raised when a chunk permanently fails, so the job
  fails loudly instead of silently shipping a ``[TRANSLATION ERROR]`` hole.
- ``backoff_delay`` — exponential backoff with full jitter.
- ``is_transient_error`` — classify an exception as worth retrying (rate limit,
  timeout, connection reset, 5xx) vs. permanent (auth, billing, bad request).
"""

from __future__ import annotations

import random


class ChunkTranslationError(RuntimeError):
    """A single chunk could not be translated after exhausting retries."""

    def __init__(self, chunk_index: int, reason: str):
        self.chunk_index = chunk_index
        self.reason = reason
        super().__init__(f"Chunk {chunk_index} failed to translate: {reason}")


# Substrings (lowercased) that indicate a transient, retry-worthy failure.
_TRANSIENT_MARKERS = (
    "rate limit",
    "rate_limit",
    "429",
    "too many requests",
    "timeout",
    "timed out",
    "connection",
    "reset by peer",
    "temporarily unavailable",
    "overloaded",
    "503",
    "502",
    "500",
    "504",
    "internal server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
)

# Substrings that indicate a permanent failure — do NOT retry these.
_PERMANENT_MARKERS = (
    "invalid api key",
    "invalid_api_key",
    "authentication",
    "unauthorized",
    "permission",
    "billing",
    "insufficient_quota",
    "credit balance is too low",
    "not found",
    "does not support",
)


def is_transient_error(exc: BaseException) -> bool:
    """Return True if ``exc`` looks transient and is worth retrying.

    Permanent markers win over transient ones (e.g. a 400 with an auth message
    should not be retried). Unknown errors default to transient=True so a flaky
    provider gets a couple of retries rather than instantly corrupting output.
    """
    msg = str(exc).lower()
    if any(m in msg for m in _PERMANENT_MARKERS):
        return False
    if any(m in msg for m in _TRANSIENT_MARKERS):
        return True
    # Default: treat unknown errors as transient (bounded retries upstream).
    return True


def backoff_delay(attempt: int, base: float = 2.0, cap: float = 60.0) -> float:
    """Exponential backoff with full jitter, in seconds.

    ``attempt`` is 0-indexed. Returns a value in ``[0, min(cap, base*2**attempt)]``.
    Full jitter spreads concurrent retries out to avoid thundering-herd storms.
    """
    ceiling = min(cap, base * (2 ** max(0, attempt)))
    return round(random.uniform(0, ceiling), 3)
