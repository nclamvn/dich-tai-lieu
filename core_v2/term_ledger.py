"""
Term ledger for the core_v2 translation pipeline.

A small, dependency-free "term ledger" that maps source terms to agreed target
translations so proper nouns and key terminology stay consistent across every
chunk of a document:

- ``TermEntry`` — one ``source → target`` pair with a priority and provenance.
- ``TermLedger`` — a priority-merging collection with helpers to select the
  entries relevant to a piece of text, render a prompt instruction block, and
  fingerprint its contents so caches can be invalidated when terminology
  changes.
- ``extract_terms`` — an async LLM auto-extractor that never raises.
- ``load_glossary_ledger`` — a guarded loader that pulls user glossary terms via
  ``core.glossary`` when that (SQLAlchemy-backed) package is importable, and
  degrades to an empty ledger when it is not.

Only the standard library is imported at module load time, so this module can be
unit-tested in isolation without SQLAlchemy, Anthropic, or OpenAI installed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TermEntry:
    """A single ``source → target`` term pair with priority and provenance."""

    source: str
    target: str
    priority: int = 5
    provenance: str = "auto"


def _norm_key(source: str) -> str:
    """Normalized dict key for a source term (trimmed and case-folded).

    ``casefold`` (rather than ``lower``) so case-insensitive matching stays
    correct for non-ASCII scripts as well.
    """
    return source.strip().casefold()


class TermLedger:
    """A priority-merging map of source terms to agreed target translations."""

    def __init__(self) -> None:
        self._entries: Dict[str, TermEntry] = {}

    def add(
        self,
        source: str,
        target: str,
        priority: int = 5,
        provenance: str = "auto",
    ) -> None:
        """Insert a term.

        On a key conflict, keep the entry with the HIGHER priority; ties keep the
        existing entry. Entries whose source or target is empty/whitespace are
        ignored.
        """
        if not source or not source.strip():
            return
        if not target or not target.strip():
            return

        key = _norm_key(source)
        existing = self._entries.get(key)
        if existing is not None and existing.priority >= priority:
            # Incumbent already outranks (or ties) the newcomer — keep it.
            return

        self._entries[key] = TermEntry(
            source=source.strip(),
            target=target.strip(),
            priority=priority,
            provenance=provenance,
        )

    def merge(self, other: "TermLedger") -> "TermLedger":
        """Fold every entry of ``other`` into self via :meth:`add`.

        Priority rules from :meth:`add` are respected. Returns self so calls can
        be chained (e.g. ``ledger.merge(a).merge(b)``).
        """
        for entry in other:
            self.add(entry.source, entry.target, entry.priority, entry.provenance)
        return self

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __iter__(self) -> Iterator[TermEntry]:
        return iter(self._entries.values())

    def items(self) -> List[TermEntry]:
        """All entries sorted by descending priority, then source (case-folded)."""
        return sorted(
            self._entries.values(),
            key=lambda e: (-e.priority, e.source.casefold()),
        )

    def relevant_for(self, text: str) -> "TermLedger":
        """Return a NEW ledger with only entries whose source occurs in ``text``.

        Matching is a plain case-insensitive substring test so it stays
        diacritic/CJK-safe. Regex word boundaries (``\\b``) are deliberately NOT
        used: they break for Vietnamese multi-syllable terms and for scripts
        (such as CJK) that have no word boundaries.
        """
        out = TermLedger()
        if not text:
            return out
        haystack = text.casefold()
        for entry in self.items():
            if entry.source.casefold() in haystack:
                out.add(entry.source, entry.target, entry.priority, entry.provenance)
        return out

    def to_prompt_block(self, max_terms: int = 80) -> str:
        """Render the top ``max_terms`` entries as a terminology instruction block.

        Entries are taken in :meth:`items` order (already sorted by priority), so
        capping silently drops the lowest-priority terms. Returns ``""`` when the
        ledger is empty.
        """
        entries = self.items()[:max_terms]
        if not entries:
            return ""
        lines = ["TERMINOLOGY — use these EXACT target translations consistently:"]
        for entry in entries:
            lines.append(f"- {entry.source} → {entry.target}")
        return "\n".join(lines)

    def fingerprint(self) -> str:
        """Stable short hex over the sorted ``(source, target, priority)`` tuples.

        Used to invalidate caches when the terminology changes. An empty ledger
        returns the fixed constant ``"noterms"``.
        """
        if not self._entries:
            return "noterms"
        tuples = sorted(
            (e.source, e.target, e.priority) for e in self._entries.values()
        )
        payload = json.dumps(tuples, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return digest[:16]


def _strip_code_fences(text: str) -> str:
    """Remove a leading ```/```json fence and its trailing ``` if present."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    newline = text.find("\n")
    text = text[newline + 1:] if newline != -1 else ""
    fence = text.rfind("```")
    if fence != -1:
        text = text[:fence]
    return text


def _parse_terms_json(content: str) -> List:
    """Extract a JSON array of term objects from a raw LLM response.

    Strips markdown code fences, then slices from the first ``[`` to the last
    ``]`` and ``json.loads`` that. Raises on malformed input; callers are
    expected to treat any exception as "no terms".
    """
    text = _strip_code_fences(content)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON array found in response")
    return json.loads(text[start:end + 1])


async def extract_terms(
    source_text: str,
    llm_client,
    source_lang: str,
    target_lang: str,
    max_terms: int = 40,
    sample_chars: int = 6000,
) -> TermLedger:
    """Ask an LLM to extract key terms/proper nouns and their target translations.

    Reads the first ``sample_chars`` characters of ``source_text``, asks the
    model for up to ``max_terms`` terms as STRICT JSON, and folds the parsed
    pairs into a ledger with ``provenance="auto"`` and ``priority=5``.

    Never raises: on any failure (bad response, malformed JSON, client error) an
    EMPTY :class:`TermLedger` is returned and a warning is logged.
    """
    sample = (source_text or "")[:sample_chars]
    if not sample.strip():
        return TermLedger()

    prompt = (
        f"You are a terminology extractor. From the {source_lang} source text "
        f"below, extract up to {max_terms} key terms and proper nouns (names, "
        f"technical terms, recurring key phrases) that must be translated "
        f"consistently throughout a document. Give each a single, consistent "
        f"{target_lang} translation.\n\n"
        f"Return STRICT JSON and NOTHING else: a JSON array of objects, each "
        f'shaped exactly as {{"source": "...", "target": "..."}}. No markdown, '
        f"no code fences, no commentary.\n\n"
        f"SOURCE TEXT:\n{sample}"
    )

    ledger = TermLedger()
    try:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = getattr(response, "content", "") or ""
        pairs = _parse_terms_json(content)
        for item in pairs:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            target = item.get("target")
            if not isinstance(source, str) or not isinstance(target, str):
                continue
            ledger.add(source, target, priority=5, provenance="auto")
    except Exception as exc:  # noqa: BLE001 — must never raise to the caller
        logger.warning("extract_terms failed, returning empty ledger: %s", exc)
        return TermLedger()

    return ledger


def load_glossary_ledger(
    glossary_ids: Optional[List[str]],
    sample_text: str = "",
) -> TermLedger:
    """Pull user glossary terms into a ledger, degrading to empty on any failure.

    The ``core.glossary`` package is imported lazily because it depends on
    SQLAlchemy, which may be absent; any import or runtime failure yields an
    empty ledger. Glossary terms are added with ``provenance="glossary"`` and
    ``priority=9`` so they outrank auto-extracted terms.

    - If ``glossary_ids`` is falsy, an empty ledger is returned.
    - If ``sample_text`` is non-empty, only terms found in it are added.
    - Otherwise every term of each glossary is loaded.

    This function never raises.
    """
    ledger = TermLedger()
    if not glossary_ids:
        return ledger

    try:
        from core.glossary.matcher import get_matcher
    except Exception as exc:  # noqa: BLE001 — ImportError or anything import triggers
        logger.warning("glossary unavailable, skipping glossary ledger: %s", exc)
        return ledger

    try:
        matcher = get_matcher()
        if sample_text:
            matches = matcher.find_matches(sample_text, glossary_ids)
            unique = matcher.get_unique_terms(matches)
            for source, target in unique.items():
                ledger.add(source, target, priority=9, provenance="glossary")
        else:
            for gid in glossary_ids:
                try:
                    terms = matcher.load_glossary(gid)
                except Exception as exc:  # noqa: BLE001 — skip a bad glossary
                    logger.warning("failed to load glossary %s: %s", gid, exc)
                    continue
                for term in terms:
                    ledger.add(
                        term.source_term,
                        term.target_term,
                        priority=9,
                        provenance="glossary",
                    )
    except Exception as exc:  # noqa: BLE001 — must never raise to the caller
        logger.warning("building glossary ledger failed: %s", exc)
        return ledger

    return ledger
