"""
Token-budgeted, structure-preserving chunking primitives for the core_v2
translation pipeline.

Dependency-free chunking sized by an *estimated* token budget rather than raw
character count, so the chunker can guarantee no chunk exceeds a model's budget
while never destroying paragraph / line / LaTeX structure. Vietnamese-first and
CJK aware.

- ``estimate_tokens`` — a tokenizer-free heuristic that counts CJK characters as
  one token each and the remaining characters at a slightly conservative
  characters-per-token ratio (Vietnamese diacritics inflate real token counts).
- ``split_into_blocks`` — split on blank-line boundaries, preserving each block's
  internal structure (single newlines, LaTeX, list items) verbatim.
- ``split_oversized_block`` — break a single over-budget block along the finest
  content-preserving boundary available (lines → sentences → words → hard
  character slices) so every piece fits the budget.
- ``pack_blocks`` — greedily pack consecutive blocks into budget-sized chunks,
  expanding any single over-budget block first.
- ``chunk_text_by_tokens`` — the top-level entry point tying the above together.

Only the standard library is imported at module load time, so this module can be
unit-tested in isolation without ``tiktoken`` or any network access.

Token-budget guarantee: every chunk returned by :func:`chunk_text_by_tokens`
satisfies ``estimate_tokens(chunk) <= max_tokens``. The single caveat is a source
that contains one indivisible token (an unbroken run of characters with no
whitespace) longer than the budget — the hard character-slice fallback splits
even that, so in practice the guarantee always holds for ``max_tokens >= 1``.
"""

from __future__ import annotations

import logging
import math
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Slightly conservative characters-per-token ratio for non-CJK text. A lower
# ratio yields a HIGHER estimate, which keeps us safely under real tokenizer
# counts for Vietnamese (diacritics push the true count up).
_CHARS_PER_TOKEN = 3.5

# Blank-line boundary: one or more lines that are empty or whitespace-only.
_BLANK_LINE_BOUNDARY = re.compile(r"\n\s*\n")

# Sentence boundary: whitespace that follows a sentence-final punctuation mark
# (Latin and full-width CJK variants).
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")

# Finest-to-coarsest split levels used by :func:`_split_level`.
_LEVEL_LINES = 0
_LEVEL_SENTENCES = 1
_LEVEL_WORDS = 2
_LEVEL_CHARS = 3


def _is_cjk_char(ch: str) -> bool:
    """Return True if ``ch`` is a CJK / Japanese / Korean character.

    Ranges: CJK Unified Ideographs (U+4E00–U+9FFF), Hiragana + Katakana
    (U+3040–U+30FF), Hangul syllables (U+AC00–U+D7A3), and CJK Extension A
    (U+3400–U+4DBF). These scripts tokenize at roughly one token per character.
    """
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF
        or 0x3040 <= o <= 0x30FF
        or 0xAC00 <= o <= 0xD7A3
        or 0x3400 <= o <= 0x4DBF
    )


def _char_counts(text: str) -> Tuple[int, int]:
    """Return ``(cjk_count, non_cjk_len)`` for ``text``."""
    cjk = 0
    non_cjk = 0
    for ch in text:
        if _is_cjk_char(ch):
            cjk += 1
        else:
            non_cjk += 1
    return cjk, non_cjk


def _ceil_tokens(non_cjk_len: int) -> int:
    """Estimated tokens for ``non_cjk_len`` non-CJK characters (``ceil``)."""
    if non_cjk_len <= 0:
        return 0
    return math.ceil(non_cjk_len / _CHARS_PER_TOKEN)


def estimate_tokens(text: str) -> int:
    """Heuristic token estimate for ``text`` — no tokenizer dependency.

    CJK characters count as one token each; the remaining characters are
    estimated at ``ceil(non_cjk_len / 3.5)``. The result is
    ``cjk_count + ceil(non_cjk_len / 3.5)``, and ``0`` for empty or
    whitespace-only input.

    The estimate is monotonic non-decreasing in length (for a fixed script mix),
    and for two strings of equal length an all-CJK string always estimates at
    least as many tokens as an all-ASCII one — strictly more once length ``>= 2``.
    """
    if not text or not text.strip():
        return 0
    cjk, non_cjk = _char_counts(text)
    return cjk + _ceil_tokens(non_cjk)


def split_into_blocks(text: str) -> List[str]:
    """Split ``text`` on blank-line boundaries into structure-preserving blocks.

    Blocks are separated by one or more blank/whitespace-only lines
    (regex ``\\n\\s*\\n``). Each block is stripped of leading/trailing whitespace
    but is otherwise preserved EXACTLY — internal single newlines, spaces, list
    markers and multi-line LaTeX are kept as-is. Blocks that are empty after
    stripping are dropped. Empty or whitespace-only input yields ``[]``.
    """
    if not text or not text.strip():
        return []
    blocks: List[str] = []
    for raw in _BLANK_LINE_BOUNDARY.split(text):
        stripped = raw.strip()
        if stripped:
            blocks.append(stripped)
    return blocks


def _split_by_chars(text: str, max_tokens: int) -> List[str]:
    """Last-resort hard character slicing that never exceeds ``max_tokens``.

    Greedily accumulates characters while the running estimate stays within
    budget. Because a single character is worth at most one token, each emitted
    slice satisfies ``estimate_tokens(slice) <= max_tokens`` for any
    ``max_tokens >= 1``. Content is preserved exactly (no separators inserted).
    """
    budget = max_tokens if max_tokens >= 1 else 1
    pieces: List[str] = []
    cur: List[str] = []
    cur_cjk = 0
    cur_non = 0
    for ch in text:
        is_cjk = _is_cjk_char(ch)
        nxt_cjk = cur_cjk + (1 if is_cjk else 0)
        nxt_non = cur_non + (0 if is_cjk else 1)
        if cur and nxt_cjk + _ceil_tokens(nxt_non) > budget:
            pieces.append("".join(cur))
            cur = [ch]
            cur_cjk = 1 if is_cjk else 0
            cur_non = 0 if is_cjk else 1
        else:
            cur.append(ch)
            cur_cjk, cur_non = nxt_cjk, nxt_non
    if cur:
        pieces.append("".join(cur))
    return pieces


def _pack_units(
    units: List[str],
    max_tokens: int,
    joiner: str,
    next_level: int,
) -> List[str]:
    """Greedily pack ``units`` into pieces ``<= max_tokens``, joined by ``joiner``.

    A single unit that alone exceeds the budget is flushed on its own and then
    split with the next-finer strategy via :func:`_split_level`, so every
    returned piece fits the budget. Token counts are tracked incrementally to
    avoid re-estimating the growing piece on each step.
    """
    joiner_cjk, joiner_non = _char_counts(joiner)
    pieces: List[str] = []
    cur: List[str] = []
    cur_cjk = 0
    cur_non = 0
    for unit in units:
        # Empty fragments only carry meaning for line splitting (they preserve a
        # newline); for sentence/word splitting they are noise from ``re.split``.
        if unit == "" and joiner != "\n":
            continue
        u_cjk, u_non = _char_counts(unit)
        if u_cjk + _ceil_tokens(u_non) > max_tokens:
            if cur:
                pieces.append(joiner.join(cur))
                cur, cur_cjk, cur_non = [], 0, 0
            pieces.extend(_split_level(unit, max_tokens, next_level))
            continue
        if cur:
            new_cjk = cur_cjk + joiner_cjk + u_cjk
            new_non = cur_non + joiner_non + u_non
            if new_cjk + _ceil_tokens(new_non) <= max_tokens:
                cur.append(unit)
                cur_cjk, cur_non = new_cjk, new_non
                continue
            pieces.append(joiner.join(cur))
        cur = [unit]
        cur_cjk, cur_non = u_cjk, u_non
    if cur:
        pieces.append(joiner.join(cur))
    return pieces


def _split_level(text: str, max_tokens: int, level: int) -> List[str]:
    """Split ``text`` into budget-sized pieces starting at split ``level``.

    Levels, finest boundary that still preserves content first:
    lines (``\\n``) → sentences → words → hard character slices. Each level
    recurses into the next when the current boundary is unavailable, and
    :func:`_pack_units` recurses when a single unit is itself over budget.
    """
    if estimate_tokens(text) <= max_tokens:
        return [text] if text else []

    if level <= _LEVEL_LINES:
        if "\n" in text:
            return _pack_units(text.split("\n"), max_tokens, "\n", _LEVEL_SENTENCES)
        return _split_level(text, max_tokens, _LEVEL_SENTENCES)

    if level == _LEVEL_SENTENCES:
        parts = _SENTENCE_BOUNDARY.split(text)
        if len(parts) > 1:
            return _pack_units(parts, max_tokens, " ", _LEVEL_WORDS)
        return _split_level(text, max_tokens, _LEVEL_WORDS)

    if level == _LEVEL_WORDS:
        words = text.split()
        if len(words) > 1:
            return _pack_units(words, max_tokens, " ", _LEVEL_CHARS)
        return _split_level(text, max_tokens, _LEVEL_CHARS)

    return _split_by_chars(text, max_tokens)


def split_oversized_block(block: str, max_tokens: int) -> List[str]:
    """Split a single ``block`` exceeding ``max_tokens`` into budget-sized pieces.

    The finest content-preserving boundary is chosen first: by lines if the
    block is multi-line, else by sentences, else by words, else by hard
    character slices as a last resort. Concatenating the pieces back (modulo the
    join separators used — ``\\n`` between lines, a single space between
    sentences/words) loses no words or characters of the original tokens.

    Never raises. If the block already fits
    (``estimate_tokens(block) <= max_tokens``) it is returned unchanged as
    ``[block]``.
    """
    budget = max_tokens if max_tokens >= 1 else 1
    if estimate_tokens(block) <= budget:
        return [block]
    return _split_level(block, budget, _LEVEL_LINES)


def pack_blocks(blocks: List[str], max_tokens: int) -> List[str]:
    """Greedily pack ``blocks`` into chunks whose estimate is ``<= max_tokens``.

    Consecutive blocks are joined with ``"\\n\\n"`` while they fit. Any single
    block that alone exceeds the budget is first expanded via
    :func:`split_oversized_block`, and the resulting pieces are packed too.
    Empty or whitespace-only blocks are skipped, and no empty chunk is emitted.
    """
    budget = max_tokens if max_tokens >= 1 else 1

    # Expand oversized blocks so every unit to pack already fits the budget.
    units: List[str] = []
    for block in blocks:
        if not block or not block.strip():
            continue
        if estimate_tokens(block) > budget:
            units.extend(split_oversized_block(block, budget))
        else:
            units.append(block)

    sep_cjk, sep_non = _char_counts("\n\n")
    chunks: List[str] = []
    cur: List[str] = []
    cur_cjk = 0
    cur_non = 0
    for unit in units:
        if not unit:
            continue
        u_cjk, u_non = _char_counts(unit)
        if cur:
            new_cjk = cur_cjk + sep_cjk + u_cjk
            new_non = cur_non + sep_non + u_non
            if new_cjk + _ceil_tokens(new_non) <= budget:
                cur.append(unit)
                cur_cjk, cur_non = new_cjk, new_non
                continue
            chunks.append("\n\n".join(cur))
        cur = [unit]
        cur_cjk, cur_non = u_cjk, u_non
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def chunk_text_by_tokens(
    text: str,
    max_tokens: int,
    min_tokens: int = 0,
) -> List[str]:
    """Chunk ``text`` into structure-preserving pieces sized by token budget.

    Splits ``text`` into blocks on blank-line boundaries; if it has no blank
    lines (one blob) the whole stripped text is treated as a single block. The
    blocks are then greedily packed via :func:`pack_blocks`.

    Every returned chunk satisfies ``estimate_tokens(chunk) <= max_tokens``,
    with the single caveat that a source containing one indivisible token (an
    unbroken run of characters with no whitespace) longer than the budget cannot
    be split below it — the hard character-slice fallback makes this effectively
    never happen for ``max_tokens >= 1``.

    ``min_tokens`` is an advisory floor: when positive, a trailing chunk smaller
    than it is merged into its predecessor if (and only if) the merged result
    still fits ``max_tokens``, so the budget guarantee is never violated. It
    defaults to ``0`` (no merging). Empty or whitespace-only input returns ``[]``.
    """
    if not text or not text.strip():
        return []

    budget = max_tokens if max_tokens >= 1 else 1
    blocks = split_into_blocks(text)
    if not blocks:
        blocks = [text.strip()]

    chunks = pack_blocks(blocks, budget)

    if min_tokens > 0 and len(chunks) >= 2:
        last = chunks[-1]
        if estimate_tokens(last) < min_tokens:
            merged = chunks[-2] + "\n\n" + last
            if estimate_tokens(merged) <= budget:
                chunks = chunks[:-2] + [merged]

    return chunks
