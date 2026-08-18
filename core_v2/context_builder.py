"""
Deterministic rolling cross-chunk context for the core_v2 translation pipeline.

The translation prompt hands every chunk a "Previous content" and "Next content"
string so a translation stays continuous across chunk boundaries. Building that
context naively (the first N characters of the neighbouring chunk) is wrong on
two counts: the *previous* window should be the END of the previous chunk, not
its start, and both windows should respect sentence boundaries instead of
slicing mid-word.

This module builds proper rolling context WITHOUT any LLM call, so it stays
cheap and deterministic and never serializes the pipeline's concurrency:

- ``split_sentences`` — split text on Latin + full-width CJK sentence-final
  punctuation, preserving each sentence verbatim.
- ``last_sentences`` — the trailing sentences of a chunk (its most recent tail),
  char-capped to the most recent characters.
- ``first_sentences`` — the leading sentences of a chunk (its topic opening),
  char-capped to the first characters.
- ``build_running_gist`` — collapse a chronological list of earlier-chunk topics
  into a single rolling gist, keeping the most recent content when over budget.
- ``build_chunk_contexts`` — for each chunk, produce a ``(preceding, following)``
  pair: an older-context gist plus the exact tail of the immediately-preceding
  chunk (no duplication), and the head of the next chunk.

Only the standard library is imported, so this module can be unit-tested in
isolation. Every function is pure, deterministic, holds no global state, and
never raises on ordinary input.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Sentence boundary: whitespace that follows a sentence-final punctuation mark
# (Latin ``. ! ?`` and their full-width CJK variants ``。！？``). Matches the
# boundary used by :mod:`core_v2.token_chunking` so both modules segment
# identically.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")


def split_sentences(text: str) -> list[str]:
    """Split ``text`` into sentences on sentence-final punctuation boundaries.

    Splits on :data:`_SENTENCE_BOUNDARY` (whitespace after ``. ! ? 。 ！ ？``).
    Each resulting sentence is stripped of surrounding whitespace and empty
    pieces are dropped; internal spacing is preserved verbatim (nothing is
    collapsed). When ``text`` contains no such boundary the whole thing is
    returned as a single sentence (``[text.strip()]``). Empty or whitespace-only
    input yields ``[]``. Never raises.
    """
    if not text or not text.strip():
        return []
    parts = _SENTENCE_BOUNDARY.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def last_sentences(text: str, max_sentences: int = 2, max_chars: int = 400) -> str:
    """Return the LAST ``max_sentences`` sentences of ``text`` (its recent tail).

    The selected sentences are joined with a single space. If the joined result
    exceeds ``max_chars`` only the last ``max_chars`` characters are kept (the
    most recent tail), so the window always ends flush with the chunk's end.
    Empty input yields ``""``. Result is stripped. Never raises.
    """
    sentences = split_sentences(text)
    if not sentences:
        return ""
    n = max(0, max_sentences)
    tail = sentences[-n:] if n else []
    result = " ".join(tail)
    if len(result) > max_chars:
        result = result[-max_chars:]
    return result.strip()


def first_sentences(text: str, max_sentences: int = 1, max_chars: int = 400) -> str:
    """Return the FIRST ``max_sentences`` sentences of ``text`` (its opening).

    The selected sentences are joined with a single space and capped to the
    first ``max_chars`` characters. Empty input yields ``""``. Result is
    stripped. Never raises.
    """
    sentences = split_sentences(text)
    if not sentences:
        return ""
    n = max(0, max_sentences)
    head = sentences[:n]
    result = " ".join(head)
    if len(result) > max_chars:
        result = result[:max_chars]
    return result.strip()


def build_running_gist(topics: list[str], max_chars: int = 500) -> str:
    """Collapse chronological ``topics`` into a single rolling gist string.

    ``topics`` is a chronological list of short strings (topic sentences or
    summaries of earlier chunks, oldest first). Non-empty topics are joined with
    a single space. If the joined result exceeds ``max_chars`` only the last
    ``max_chars`` characters are kept, so the gist always favours the most recent
    context. Empty (or all-empty) input yields ``""``. Result is stripped. Never
    raises.
    """
    if not topics:
        return ""
    parts = [t.strip() for t in topics if t and t.strip()]
    if not parts:
        return ""
    joined = " ".join(parts)
    if len(joined) > max_chars:
        joined = joined[-max_chars:]
    return joined.strip()


def build_chunk_contexts(
    contents: list[str],
    summaries: list[str] | None = None,
    *,
    window: int = 3,
    tail_sentences: int = 2,
    head_sentences: int = 1,
    gist_max_chars: int = 500,
) -> list[tuple[str, str]]:
    """Build a ``(preceding, following)`` context pair for every chunk.

    For each chunk ``i`` in ``contents``:

    - **following** is the head of the next chunk
      (``first_sentences(contents[i + 1], head_sentences)``), or ``""`` for the
      last chunk.
    - **preceding** combines an older-context *gist* with the exact *tail* of the
      immediately-preceding chunk, with no duplication:

      * The gist is built from chunks ``[max(0, i - window), i - 1)`` — the
        window of older chunks EXCLUDING the immediate predecessor. Each topic is
        ``summaries[j]`` when a non-empty summary is supplied for ``j``, else the
        chunk's own topic sentence (``first_sentences(contents[j], 1)``).
      * The immediate tail is ``last_sentences(contents[i - 1], tail_sentences)``
        (``""`` for the first chunk).
      * The two are joined with a newline when both are non-empty; otherwise
        whichever is non-empty is used; otherwise ``""``.

    Because the gist window excludes ``i - 1``, the immediate tail is never
    duplicated inside the gist. ``summaries``, when provided, is assumed to be
    the same length as ``contents``; a shorter or ``None``-holding list simply
    falls back to the topic sentence for the missing positions. Pure,
    deterministic, and never raises on ordinary input.
    """
    n = len(contents)
    contexts: list[tuple[str, str]] = []

    for i in range(n):
        # following: head of the next chunk (empty for the last chunk).
        if i < n - 1:
            following = first_sentences(contents[i + 1], head_sentences)
        else:
            following = ""

        # gist: older context, chunks [max(0, i - window), i - 1) — the window
        # EXCLUDES the immediate predecessor (i - 1) so it is never duplicated.
        gist_topics: list[str] = []
        for j in range(max(0, i - window), i - 1):
            summary = _summary_at(summaries, j)
            topic = summary if summary else first_sentences(contents[j], 1)
            if topic:
                gist_topics.append(topic)
        gist = build_running_gist(gist_topics, gist_max_chars)

        # immediate: exact tail of the immediately-preceding chunk.
        immediate = last_sentences(contents[i - 1], tail_sentences) if i > 0 else ""

        if gist and immediate:
            preceding = gist + "\n" + immediate
        elif gist:
            preceding = gist
        elif immediate:
            preceding = immediate
        else:
            preceding = ""

        contexts.append((preceding, following))

    return contexts


def _summary_at(summaries: list[str] | None, index: int) -> str:
    """Return the stripped summary at ``index`` or ``""`` if unavailable.

    Guards against ``None``, a short list, and ``None``/empty entries so
    :func:`build_chunk_contexts` can fall back to a chunk's topic sentence
    without ever raising.
    """
    if not summaries or index < 0 or index >= len(summaries):
        return ""
    value = summaries[index]
    if not value:
        return ""
    return value.strip()
