"""
Translation Memory Service — Lightweight TM with fuzzy matching.

Features:
- Exact and fuzzy match via difflib.SequenceMatcher
- Domain-aware matching (medical, legal, general, ...)
- Usage counting and quality scoring
- JSON file persistence
- No external dependencies (uses stdlib only)

Standalone module — no core/ imports.

Usage::

    tm = TranslationMemoryService(storage_path="data/tm_service.json")

    # Add segment
    tm.add_segment("en", "vi", "heart", "tim", domain="medical")

    # Exact match
    match = tm.find_exact("en", "vi", "heart")

    # Fuzzy match
    matches = tm.find_fuzzy("en", "vi", "the heart", threshold=0.6)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class TMSegment:
    """A translation memory segment (source → target pair)."""

    source: str
    target: str
    source_lang: str = "en"
    target_lang: str = "vi"
    domain: str = "general"
    quality_score: float = 1.0  # 0.0 - 1.0
    use_count: int = 0
    context: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.updated_at == 0.0:
            self.updated_at = now

    @property
    def lang_pair(self) -> str:
        return f"{self.source_lang}→{self.target_lang}"


@dataclass
class TMMatch:
    """A translation memory match result."""

    segment: TMSegment
    similarity: float  # 0.0 - 1.0
    match_type: str  # "exact", "fuzzy"

    @property
    def is_exact(self) -> bool:
        return self.match_type == "exact"


# ---------------------------------------------------------------------------
# TranslationMemoryService
# ---------------------------------------------------------------------------

class TranslationMemoryService:
    """Lightweight Translation Memory with fuzzy matching.

    Uses difflib.SequenceMatcher for similarity scoring.
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._segments: List[TMSegment] = []
        self._storage_path = Path(storage_path) if storage_path else None
        if self._storage_path:
            self._load()

    # --- Add/Update ---

    def add_segment(
        self,
        source_lang: str,
        target_lang: str,
        source: str,
        target: str,
        domain: str = "general",
        quality_score: float = 1.0,
        context: str = "",
    ) -> TMSegment:
        """Add or update a translation segment.

        If an exact source match exists for the same lang pair + domain,
        update the target instead of creating a duplicate.
        """
        source_lower = source.strip().lower()

        for seg in self._segments:
            if (
                seg.source.strip().lower() == source_lower
                and seg.source_lang == source_lang
                and seg.target_lang == target_lang
                and seg.domain == domain
            ):
                seg.target = target
                seg.quality_score = quality_score
                seg.context = context
                seg.updated_at = time.time()
                seg.use_count += 1
                self._persist()
                return seg

        segment = TMSegment(
            source=source.strip(),
            target=target.strip(),
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain,
            quality_score=quality_score,
            context=context,
        )
        self._segments.append(segment)
        self._persist()
        return segment

    def add_batch(
        self,
        source_lang: str,
        target_lang: str,
        pairs: List[Tuple[str, str]],
        domain: str = "general",
    ) -> int:
        """Add multiple translation pairs. Returns count added."""
        count = 0
        for source, target in pairs:
            if source.strip() and target.strip():
                self.add_segment(source_lang, target_lang, source, target, domain=domain)
                count += 1
        self._persist()
        return count

    # --- Lookup ---

    def find_exact(
        self,
        source_lang: str,
        target_lang: str,
        source: str,
        domain: Optional[str] = None,
    ) -> Optional[TMMatch]:
        """Find exact match for source text."""
        source_lower = source.strip().lower()

        for seg in self._segments:
            if (
                seg.source.strip().lower() == source_lower
                and seg.source_lang == source_lang
                and seg.target_lang == target_lang
                and (domain is None or seg.domain == domain)
            ):
                seg.use_count += 1
                return TMMatch(segment=seg, similarity=1.0, match_type="exact")

        return None

    def find_fuzzy(
        self,
        source_lang: str,
        target_lang: str,
        source: str,
        threshold: float = 0.7,
        max_results: int = 5,
        domain: Optional[str] = None,
    ) -> List[TMMatch]:
        """Find fuzzy matches above threshold.

        Uses difflib.SequenceMatcher for similarity.
        """
        source_lower = source.strip().lower()
        matches: List[TMMatch] = []

        for seg in self._segments:
            if (
                seg.source_lang != source_lang
                or seg.target_lang != target_lang
            ):
                continue

            if domain is not None and seg.domain != domain:
                continue

            similarity = self._similarity(source_lower, seg.source.strip().lower())

            if similarity >= threshold:
                match_type = "exact" if similarity >= 0.999 else "fuzzy"
                matches.append(TMMatch(
                    segment=seg,
                    similarity=round(similarity, 4),
                    match_type=match_type,
                ))

        # Sort by similarity descending
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:max_results]

    # --- Statistics ---

    def get_statistics(self) -> dict:
        """Get TM statistics."""
        if not self._segments:
            return {
                "total_segments": 0,
                "language_pairs": [],
                "domains": [],
                "avg_quality": 0.0,
            }

        lang_pairs = set()
        domains = set()
        total_quality = 0.0

        for seg in self._segments:
            lang_pairs.add(seg.lang_pair)
            domains.add(seg.domain)
            total_quality += seg.quality_score

        return {
            "total_segments": len(self._segments),
            "language_pairs": sorted(lang_pairs),
            "domains": sorted(domains),
            "avg_quality": round(total_quality / len(self._segments), 4),
        }

    def clear(self) -> None:
        """Clear all segments."""
        self._segments.clear()
        self._persist()

    # --- Similarity ---

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Compute similarity between two strings using SequenceMatcher."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    # --- Persistence ---

    def _persist(self) -> None:
        if not self._storage_path:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(s) for s in self._segments]
            self._storage_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to persist TM: %s", exc)

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
            for item in raw:
                self._segments.append(TMSegment(**item))
            logger.info("Loaded %d TM segments from %s", len(self._segments), self._storage_path)
        except Exception as exc:
            logger.warning("Failed to load TM: %s", exc)

    @property
    def segment_count(self) -> int:
        return len(self._segments)
