"""Strip running headers / footers ("page furniture") from extracted document text.

PDF (and some EPUB) sources repeat a running header and footer on every page —
typically the book title on one side and ``Author ◆ <page-number>`` on the other.
Text extraction (PyMuPDF ``get_text`` and, to a lesser extent, vision reading)
captures those repeats in reading order, so they end up:

* littered as standalone lines throughout the body (the title, dozens of times),
* glued to the start/middle of body paragraphs where a sentence spans a page
  break (``"12 ◆ THE SOURCE 3:25 AM..."`` / ``"Author ◆ 17 bones. The face..."``), and
* flooding any table of contents built from the document's headings.

This module removes that furniture **before** DNA extraction / chunking, so the
title only appears where the renderer intentionally places it (the cover).

The detector is data-driven, not hard-coded to any title:

1. **Frequency pass** — short lines whose digit-normalized form repeats at least
   ``floor`` times (and that don't look like real sentences) are "furniture
   tokens". A whole book's title/author reliably clears the floor; real chapter
   titles and prose lines do not.
2. **Inline pass** — a separator-anchored regex built from those tokens removes
   the header/footer *stamp* (``<page-num> ◆ TITLE`` or ``TITLE ◆ <page-num>``)
   wherever it is glued into body text.

Both passes require real evidence (high repetition, or the decorative separator
glyph that only appears in page furniture), so on a document without running
headers the function is a no-op and returns the text unchanged.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Unicode private-use area: books embed a decorative separator glyph (e.g. ◆, ❖)
# from their display font here. It appears ONLY in running head/foot furniture,
# never in body prose, so it is a near-perfect anchor.
_PUA = frozenset(chr(c) for c in range(0xE000, 0xF900))
_SEP_CHARS = "◆❖•·▪●■♦♢◇‹›|–—"  # visible separators sometimes used instead of a PUA glyph
_SEP_CLASS = "[" + re.escape(_SEP_CHARS) + "-]"

_SENT_END = re.compile(r"[.!?…”\"’)]\s*$")
_PAGENUM = r"\d{1,4}"

# A printed contents entry inside extracted text: a title, a long dot leader
# (3+ dots — never a chapter prefix like "01."), then a page number. Titles may
# contain single dots, so the leader is what delimits them.
_TOC_SEGMENT_RE = re.compile(r"(\S[^\n]*?)\s*\.{3,}\s*(\d{1,4})(?=\s|\n|$)")


def normalize_toc_lines(text: str) -> tuple[str, int]:
    """Split a source book's printed contents page into one clean line per entry.

    A printed TOC extracts as a single dense blob — dozens of titles glued
    together with 200-dot leaders and page numbers ("… 30. Khoanh vùng……249 …").
    Fed to the translator as one lump, the odd title slips through untranslated,
    and the dot runs read as non-translatable formatting. Rewriting each entry
    onto its own line with a short " . . . " leader turns every title into a
    clean, isolated translatable unit — and the render layer's parse_toc_line
    picks the same shape up to align it.

    Returns ``(text, n_entries_normalized)``; unchanged when no TOC blob is found.
    """
    if not text:
        return text, 0
    count = 0

    def _repl(m: "re.Match") -> str:
        nonlocal count
        title = m.group(1).strip()
        if not any(c.isalpha() for c in title):
            return m.group(0)  # pure numbers / separators — not a real entry
        count += 1
        return f"\n{title} . . . {m.group(2)}\n"

    out = _TOC_SEGMENT_RE.sub(_repl, text)
    if count:
        out = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", out)
    return (out, count) if count else (text, 0)


def _norm(s: str) -> str:
    """Digit-insensitive, punctuation-insensitive key for frequency counting."""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(" " if ch in _PUA else ch for ch in s)
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().lower()


def _core(raw: str) -> str:
    """The furniture's stable text: separators and page numbers removed.

    ``"Nguyen Canh Lam  ◆  43"`` -> ``"Nguyen Canh Lam"``; ``"KHỞI NGUỒN"`` stays.
    This is what actually repeats page to page (the page number is what varies),
    so it is the right thing to anchor the inline stamp regex on.
    """
    s = unicodedata.normalize("NFKC", raw)
    s = "".join(" " if ch in _PUA else ch for ch in s)
    s = re.sub(_SEP_CLASS + "+", " ", s)
    s = re.sub(r"\d+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class FurnitureReport:
    tokens: dict[str, str] = field(default_factory=dict)  # norm form -> most common raw
    standalone_removed: int = 0
    inline_stripped: int = 0

    @property
    def detected(self) -> bool:
        return bool(self.tokens)


def detect_furniture_tokens(
    lines: list[str], *, floor: int = 5, max_words: int = 8, max_chars: int = 70
) -> dict[str, str]:
    """Return {normalized_form: representative_raw} for repeated header/foot lines.

    A candidate must be short (a header/footer is), repeat at least ``floor``
    times, and not read like a real sentence (no terminal ``.?!`` etc.).
    """
    counts: Counter[str] = Counter()
    raw_variants: dict[str, Counter] = {}
    for ln in lines:
        t = ln.strip()
        if not t or len(t) > max_chars or len(t.split()) > max_words:
            continue
        form = _norm(t)
        if not form:
            continue
        counts[form] += 1
        raw_variants.setdefault(form, Counter())[t] += 1

    tokens: dict[str, str] = {}
    for form, c in counts.items():
        if c < floor:
            continue
        raw = raw_variants[form].most_common(1)[0][0]
        if _SENT_END.search(raw):
            continue  # a repeated real sentence is not furniture
        tokens[form] = raw
    return tokens



_HDR_SHAPE = re.compile(rf"{_PAGENUM}\s*{_SEP_CLASS}+\s*([^\n]{{1,80}})", re.UNICODE)
_FTR_SHAPE = re.compile(rf"([^\n]{{1,80}}?)\s*{_SEP_CLASS}+\s*{_PAGENUM}", re.UNICODE)
_WORD_RE = re.compile(r"[\w’'-]+", re.UNICODE)


def _isupper_word(w: str) -> bool:
    return any(ch.isalpha() for ch in w) and w == w.upper()


def _iscap_word(w: str) -> bool:
    letters = [ch for ch in w if ch.isalpha()]
    return bool(letters) and letters[0] == letters[0].upper()


def detect_inline_furniture_tokens(text: str, *, floor: int = 5) -> dict[str, str]:
    """Find furniture whose every occurrence is GLUED into body text.

    A PDF whose extraction merges paragraphs produces lines like
    ``"…từng\n\n10    <pua>    KHỌI NGUỄN lọn sóng…"`` (title interrupting a
    sentence mid-line) — the running header never stands alone, so the
    standalone-line frequency pass sees nothing. Here the *stamp shape itself*
    proposes candidates:

    * after ``<num> <sep>``: the leading run of ALL-CAPS words (running-header
      title) — prefixes counted, longest prefix at ~max family frequency wins;
    * before ``<sep> <num>``: the trailing run of Capitalized words (an
      ``Author <sep> page`` footer) — suffixes counted the same way.

    Only phrases repeating >= ``floor`` times qualify, so chapter headings and
    prose near a stray separator never make the cut.
    """
    raw_of: dict[str, str] = {}
    prefix_counts: Counter = Counter()
    for m in _HDR_SHAPE.finditer(text):
        words = _WORD_RE.findall(m.group(1))
        run = []
        for w in words:
            if not _isupper_word(w) or len(run) >= 6:
                break
            run.append(w)
        for k in range(1, len(run) + 1):
            phrase = " ".join(run[:k])
            form = _norm(phrase)
            if form:
                prefix_counts[form] += 1
                raw_of.setdefault(form, phrase)

    suffix_counts: Counter = Counter()
    for m in _FTR_SHAPE.finditer(text):
        words = _WORD_RE.findall(m.group(1))
        run = []
        for w in reversed(words):
            if not _iscap_word(w) or len(run) >= 6:
                break
            run.append(w)
        run.reverse()
        for k in range(1, len(run) + 1):
            phrase = " ".join(run[-k:])
            form = _norm(phrase)
            if form:
                suffix_counts[form] += 1
                raw_of.setdefault(form, phrase)

    def _pick(counts: Counter) -> dict[str, str]:
        # Longest phrase whose count is within 10% of the family maximum:
        # nested prefixes/suffixes of the true token share its count ("KHỌI"
        # and "KHỌI NGUỄN" both hit ~164) while accidental extensions ("Xe
        # Nguyễn …") appear a handful of times.
        picked: dict[str, str] = {}
        qualified = {f: c for f, c in counts.items() if c >= floor}
        if not qualified:
            return picked
        top = max(qualified.values())
        for form in sorted(qualified, key=lambda f: len(raw_of[f]), reverse=True):
            if qualified[form] < 0.9 * top:
                continue
            if any(form != other and form in other for other in picked):
                continue  # covered by a longer chosen phrase
            picked[form] = raw_of[form]
        return picked

    tokens = _pick(prefix_counts)
    tokens.update(_pick(suffix_counts))
    return tokens


def _build_stamp_re(raw_tokens: list[str]) -> re.Pattern:
    # Anchor on the token CORE (no page number, no separators) so a token whose
    # representative spelling happened to include a page number still matches
    # every page's variant, and match case-insensitively so an ALL-CAPS running
    # header matches a Title-Case token (and vice-versa).
    cores = {c for c in (_core(r) for r in raw_tokens) if c}
    alt = "|".join(sorted((re.escape(c) for c in cores), key=len, reverse=True))
    sep = _SEP_CLASS
    num = _PAGENUM
    pattern = (
        rf"{num}\s*{sep}+\s*(?:{alt})"      # 12 ◆ TITLE
        rf"|(?:{alt})\s*{sep}+\s*{num}"     # AUTHOR ◆ 12
        rf"|{num}\s*{sep}+\s*{num}"         # 12 ◆ 13
        rf"|(?:{alt})\s*{sep}+"             # TITLE ◆
        rf"|{sep}+\s*(?:{alt})"             # ◆ TITLE
        rf"|{num}\s*{sep}+|{sep}+\s*{num}"  # leftover  12 ◆  /  ◆ 12
    )
    return re.compile(pattern, re.UNICODE | re.IGNORECASE)


def strip_running_furniture(text: str, *, floor: int = 5) -> tuple[str, FurnitureReport]:
    """Remove running header/footer furniture from extracted document ``text``.

    Returns ``(cleaned_text, report)``. If no furniture is detected the original
    text is returned unchanged.
    """
    report = FurnitureReport()
    if not text or not text.strip():
        return text, report

    lines = text.split("\n")
    tokens = detect_furniture_tokens(lines, floor=floor)
    # Furniture glued into merged paragraph lines never stands alone — discover
    # those tokens from the "<num> <sep> TITLE" / "AUTHOR <sep> <num>" shapes.
    for form, raw in detect_inline_furniture_tokens(text, floor=floor).items():
        tokens.setdefault(form, raw)
    if not tokens:
        return text, report
    report.tokens = tokens

    stamp_re = _build_stamp_re(list(tokens.values()))
    token_forms = set(tokens)

    out: list[str] = []
    for ln in lines:
        s = ln
        stamped = stamp_re.sub(" ", s)
        if stamped != s:
            report.inline_stripped += 1
            s = stamped
        collapsed = re.sub(r"[ \t ]+", " ", s).strip()
        # Drop a line that is now (or was) pure furniture.
        if collapsed == "" and ln.strip() != "":
            report.standalone_removed += 1
            continue
        if _norm(collapsed) in token_forms and not _SENT_END.search(collapsed):
            report.standalone_removed += 1
            continue
        out.append(collapsed if stamped != ln else ln)

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", cleaned)
    # A stripped stamp often sat exactly on a page break that interrupted a
    # sentence ("…từng ⏎⏎ [stamp] lọn sóng…"). When the text before the break
    # has no terminal punctuation and the text after starts lowercase, the
    # break is an extraction artifact — rejoin the sentence.
    cleaned = re.sub(
        r"([^\s.!?…:;”\"'’)\]])[ \t]*\n[ \t]*\n+([a-zà-ỹ])",
        r"\1 \2",
        cleaned,
    )
    logger.info(
        "running-furniture strip: %d token(s) %s; removed %d standalone line(s), "
        "cleaned %d inline stamp(s)",
        len(tokens),
        [t[:24] for t in tokens.values()],
        report.standalone_removed,
        report.inline_stripped,
    )
    return cleaned, report
