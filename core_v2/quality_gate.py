"""
Deterministic, dependency-free quality checks for translated chunks.

The orchestrator ships one chunk at a time; a chunk can come back *silently*
broken — empty, truncated mid-sentence, in the wrong language, or with its LaTeX
formulas dropped — without the provider ever raising. This module turns those
silent failures into explicit, actionable signals so the orchestrator can
re-translate just the suspect chunks instead of shipping a bad document.

Everything here is pure string / heuristic work:

- ``count_inline_math`` — count ``$$...$$`` display and ``$...$`` inline math
  spans without double-counting a display span as two inline ones.
- ``count_latex_commands`` — count occurrences of common LaTeX command tokens.
- ``check_chunk`` — run the ordered heuristic rules and return a list of
  issue-reason strings (empty list == the chunk looks fine).
- ``is_suspect`` — boolean convenience wrapper over :func:`check_chunk`.

No LLM calls, no network, no global state. Only the standard library is
imported, so this module can be unit-tested in isolation. Every function is
deterministic and never raises on ordinary string input.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# Default floor for the translated/source length ratio below which a
# *substantial* source is treated as suffering dropped content.
DEFAULT_MIN_LENGTH_RATIO = 0.30

# LaTeX command tokens that commonly carry mathematical meaning. Their
# disappearance from a translation is a strong signal that a formula was lost.
LATEX_COMMANDS = [
    "\\sum",
    "\\frac",
    "\\int",
    "\\nabla",
    "\\partial",
    "\\begin",
    "\\end",
    "\\alpha",
    "\\beta",
    "\\gamma",
    "\\theta",
    "\\mathbb",
    "\\mathcal",
]

# ``$$...$$`` display math must be matched (and removed) before ``$...$`` inline
# math, otherwise ``$$x$$`` is miscounted as two inline spans.
_DISPLAY_MATH = re.compile(r"\$\$[^$]+\$\$")
_INLINE_MATH = re.compile(r"\$[^$]+\$")

# Marker the pipeline injects when a chunk permanently fails to translate.
_ERROR_MARKER = "[TRANSLATION ERROR"

# Source shorter than this (stripped) is too small for the length-ratio check to
# be meaningful — a legitimately terse translation would trip false positives.
_MIN_SOURCE_FOR_RATIO = 200

# A translation retaining fewer than this fraction of the source's math/commands
# is treated as having lost formulas.
_LATEX_RETENTION_FLOOR = 0.6


def count_inline_math(text: str) -> int:
    """Count LaTeX math delimiters in ``text``.

    Returns the number of ``$$...$$`` display-math spans plus the number of
    ``$...$`` inline-math spans. Display spans are matched and removed first so a
    single ``$$x$$`` counts once (as display) rather than twice (as inline).
    Never raises; empty or ``None`` input yields ``0``.
    """
    if not text:
        return 0
    display = _DISPLAY_MATH.findall(text)
    remainder = _DISPLAY_MATH.sub("", text)
    inline = _INLINE_MATH.findall(remainder)
    return len(display) + len(inline)


def count_latex_commands(text: str) -> int:
    """Return the summed occurrences of each :data:`LATEX_COMMANDS` token.

    Uses non-overlapping substring counting per command. No command in the list
    is a substring of another, so a single token is never counted twice. Never
    raises; empty or ``None`` input yields ``0``.
    """
    if not text:
        return 0
    return sum(text.count(cmd) for cmd in LATEX_COMMANDS)


def check_chunk(
    source: str,
    translated: str,
    target_lang: str,
    *,
    detected_lang: Optional[str] = None,
    was_truncated: bool = False,
    has_formulas: bool = False,
    min_length_ratio: float = DEFAULT_MIN_LENGTH_RATIO,
) -> List[str]:
    """Return issue-reason strings for a translated chunk (``[]`` == looks fine).

    Rules are applied in a fixed order so the result is deterministic:

    1. **empty** — if ``translated`` is empty/whitespace, return ``["empty"]``
       immediately; this is terminal and no other checks run.
    2. **error_marker** — ``translated`` contains the pipeline's translation-error
       marker.
    3. **truncated** — ``was_truncated`` is set by the caller.
    4. **too_short** — only for a substantial source
       (``len(source.strip()) >= 200``): the stripped length ratio dropped below
       ``min_length_ratio``, i.e. content was lost.
    5. **wrong_language** — ``detected_lang`` is provided and is neither the
       target language nor ``"unknown"``/``""``.
    6. **latex_lost** — with ``has_formulas`` set, the translation retained fewer
       than 60% of the source's inline-math spans, or (added once) fewer than 60%
       of its LaTeX commands.

    Never raises and holds no global state.
    """
    # 1. Terminal empty check — nothing else is meaningful for an empty result.
    if not translated or not translated.strip():
        return ["empty"]

    # Normalize source defensively so length/count helpers never raise.
    source = source or ""
    issues: List[str] = []

    # 2. Explicit error marker injected by the pipeline.
    if _ERROR_MARKER in translated:
        issues.append("error_marker")

    # 3. Caller-signalled truncation.
    if was_truncated:
        issues.append("truncated")

    # 4. Dropped-content heuristic — only trustworthy on a substantial source.
    src_stripped = source.strip()
    if len(src_stripped) >= _MIN_SOURCE_FOR_RATIO:
        ratio = len(translated.strip()) / max(1, len(src_stripped))
        if ratio < min_length_ratio:
            issues.append("too_short")

    # 5. Wrong-language: only when the caller actually detected a language.
    if detected_lang is not None and detected_lang not in (target_lang, "unknown", ""):
        issues.append("wrong_language")

    # 6. LaTeX / formula loss — inline-math spans first, then command tokens.
    if has_formulas:
        src_math = count_inline_math(source)
        tr_math = count_inline_math(translated)
        if src_math > 0 and tr_math < src_math * _LATEX_RETENTION_FLOOR:
            issues.append("latex_lost")

        src_cmd = count_latex_commands(source)
        tr_cmd = count_latex_commands(translated)
        if (
            src_cmd > 0
            and tr_cmd < src_cmd * _LATEX_RETENTION_FLOOR
            and "latex_lost" not in issues
        ):
            issues.append("latex_lost")

    if issues:
        logger.debug("quality_gate flagged chunk: %s", issues)
    return issues


def is_suspect(source: str, translated: str, target_lang: str, **kwargs) -> bool:
    """Return ``True`` if :func:`check_chunk` flagged any issue for the chunk."""
    return bool(check_chunk(source, translated, target_lang, **kwargs))
