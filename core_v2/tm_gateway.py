"""
Guarded Translation-Memory gateway for the core_v2 translation pipeline.

The live translation path can lean on an existing Translation Memory (TM) two
ways: pull *approved prior translations* for the sentences in a chunk and render
them as prompt hints, and (optionally) write clean translations back for future
reuse. Doing that naively is dangerous — the TM may be empty, its database may be
missing, a lookup may raise — and any of those must never leak into, slow down,
or crash the translation of a live document.

This module is that safety layer. It is deliberately thin:

- ``TMHint`` — one approved (source → target) pair with a similarity and match
  type, ready to be rendered into a prompt.
- ``TMGateway`` — wraps a :class:`core.translation_memory.TranslationMemory` (or
  builds one lazily) behind three guarantees:

  * **No-op when idle.** If the TM is disabled, unavailable, or *empty* the
    gateway is inactive and every lookup returns ``[]`` with zero per-chunk cost
    (no sentence splitting, no database round-trips).
  * **Never raises into the caller.** Every method swallows its own errors,
    logs a warning, and degrades to an empty/False result.
  * **Cheap to import.** ``TranslationMemory``, ``config.settings`` and
    ``split_sentences`` are imported lazily inside methods, so importing this
    module never hard-requires them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TMHint:
    """One approved translation pair surfaced from the Translation Memory."""

    source: str
    target: str
    similarity: float
    match_type: str


class TMGateway:
    """Guarded bridge between the live translation path and a Translation Memory.

    The gateway is *active* only when it is enabled, has a usable TM, and that TM
    holds at least one segment. While inactive, :meth:`lookup_hints` short-circuits
    to ``[]`` before doing any work, so an empty or unavailable TM adds no
    per-chunk cost. No method raises into the caller.
    """

    def __init__(
        self,
        tm=None,
        *,
        enabled: bool = True,
        threshold: float = 0.85,
        max_hints: int = 5,
        max_sentences: int = 40,
        domain: str = "default",
    ):
        self.threshold = threshold
        self.max_hints = max_hints
        self.max_sentences = max_sentences
        self.domain = domain
        self.tm = tm
        self.enabled = bool(enabled)
        self._active = False

        # Lazily build a TM only when one is wanted but not supplied. Any failure
        # (missing settings, unreadable db, import error) disables the gateway
        # instead of propagating — a live translation must proceed without TM.
        if self.enabled and self.tm is None:
            try:
                from core.translation_memory import TranslationMemory
                from config.settings import settings

                db = settings.tm_dir / "tm.db"
                self.tm = TranslationMemory(db)
            except Exception as e:  # pragma: no cover - defensive, env-dependent
                logger.warning("TM unavailable, disabling TM gateway: %s", e)
                self.enabled = False
                self.tm = None

        # Without a TM there is nothing to be enabled about.
        if self.tm is None:
            self.enabled = False

        self._refresh_active()

    def _count(self) -> int:
        """Best-effort total segment count in the TM; ``0`` on any failure.

        Reads the ``total_segments`` key from the TM's ``get_statistics()``
        report. Never raises.
        """
        try:
            stats = self.tm.get_statistics()
            return int(stats.get("total_segments", 0) or 0)
        except Exception:
            return 0

    def _refresh_active(self) -> None:
        """Recompute :attr:`_active`.

        Active iff enabled, a TM is present, and it holds at least one segment.
        Called after construction and after a successful :meth:`store`, so the
        first insert flips an empty (inactive) gateway to active.
        """
        self._active = bool(self.enabled and self.tm is not None and self._count() > 0)

    def lookup_hints(self, text: str, source_lang: str, target_lang: str) -> List[TMHint]:
        """Return approved TM hints for the sentences in ``text``.

        Returns ``[]`` immediately (no cost) when the gateway is inactive or
        ``text`` is blank. Otherwise each sentence is looked up: an exact match
        wins (similarity ``1.0``, type ``"exact"``); failing that, the best fuzzy
        match at or above :attr:`threshold` is used (type ``"fuzzy"``). Hints are
        deduped by source (highest similarity kept), sorted by similarity
        descending, and capped to :attr:`max_hints`.

        The lookup loop is fully guarded: on any error it logs a warning and
        returns whatever was collected so far. Never raises.
        """
        if not self._active or not text or not text.strip():
            return []

        hints: List[TMHint] = []
        try:
            from core_v2.context_builder import split_sentences

            # Segment the chunk and dedupe sentences, preserving first-seen order,
            # then cap the number of DB lookups per chunk.
            seen: set = set()
            sentences: List[str] = []
            for sentence in split_sentences(text):
                if sentence not in seen:
                    seen.add(sentence)
                    sentences.append(sentence)
            sentences = sentences[: self.max_sentences]

            for sentence in sentences:
                match = self.tm.get_exact_match(sentence, source_lang, target_lang)
                if match is not None:
                    hints.append(TMHint(sentence, match.segment.target, 1.0, "exact"))
                    continue

                fuzzy = self.tm.get_fuzzy_matches(
                    sentence,
                    source_lang,
                    target_lang,
                    threshold=self.threshold,
                    max_results=1,
                    domain=self.domain,
                )
                if fuzzy and fuzzy[0].similarity >= self.threshold:
                    hints.append(
                        TMHint(sentence, fuzzy[0].segment.target, fuzzy[0].similarity, "fuzzy")
                    )
        except Exception as e:
            logger.warning("TM lookup failed, returning partial hints: %s", e)

        # Dedupe by source keeping the highest-similarity hint, then rank + cap.
        best: dict = {}
        for hint in hints:
            prev: Optional[TMHint] = best.get(hint.source)
            if prev is None or hint.similarity > prev.similarity:
                best[hint.source] = hint
        ranked = sorted(best.values(), key=lambda h: h.similarity, reverse=True)
        return ranked[: self.max_hints]

    def render_hints_block(self, hints: List[TMHint]) -> str:
        """Render ``hints`` as a prompt block, or ``""`` when there are none."""
        if not hints:
            return ""
        lines = [
            "TRANSLATION MEMORY — approved translations for matching segments "
            "(reuse VERBATIM when the segment matches):"
        ]
        for hint in hints:
            lines.append(f"- {hint.source} → {hint.target}")
        return "\n".join(lines)

    def store(
        self,
        source: str,
        target: str,
        source_lang: str,
        target_lang: str,
        *,
        quality_score: float = 1.0,
    ) -> bool:
        """Write a clean (source → target) pair back to the TM.

        Returns ``False`` (a no-op) when the gateway is disabled or either side is
        blank. On a successful insert, refreshes :attr:`_active` so a first insert
        flips an empty gateway to active, and returns ``True``. Any error logs a
        warning and returns ``False``. Never raises.
        """
        if not self.enabled:
            return False
        if not (source and source.strip() and target and target.strip()):
            return False
        try:
            from core.translation_memory import TMSegment

            seg = TMSegment(
                source=source,
                target=target,
                source_lang=source_lang,
                target_lang=target_lang,
                domain=self.domain,
                quality_score=quality_score,
            )
            self.tm.add_segment(seg)
            self._refresh_active()
            return True
        except Exception as e:
            logger.warning("TM store failed: %s", e)
            return False

    def close(self) -> None:
        """Best-effort close of the underlying TM. Never raises."""
        try:
            if self.tm is not None:
                self.tm.close()
        except Exception:
            pass
