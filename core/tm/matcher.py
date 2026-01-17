"""
TM Matcher
Find similar segments using exact and fuzzy matching.
"""
import logging
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import TMSegment, compute_hash, normalize_text
from .schemas import MatchType

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a TM match."""
    segment: TMSegment
    similarity: float
    match_type: MatchType

    def __repr__(self):
        return f"<Match {self.similarity:.1%} ({self.match_type.value})>"


class TMMatcher:
    """
    Translation Memory Matcher.

    Finds exact and fuzzy matches for source text.
    Uses hash-based O(1) lookup for exact matches,
    Levenshtein distance for fuzzy matches.
    """

    # Similarity thresholds
    EXACT_THRESHOLD = 1.0
    NEAR_EXACT_THRESHOLD = 0.95
    FUZZY_THRESHOLD = 0.75

    def __init__(
        self,
        exact_threshold: float = 1.0,
        near_exact_threshold: float = 0.95,
        fuzzy_threshold: float = 0.75,
    ):
        """
        Initialize matcher.

        Args:
            exact_threshold: Similarity for exact match
            near_exact_threshold: Similarity for near-exact match
            fuzzy_threshold: Minimum similarity for fuzzy match
        """
        self.exact_threshold = exact_threshold
        self.near_exact_threshold = near_exact_threshold
        self.fuzzy_threshold = fuzzy_threshold

        # Cache for normalized text
        self._norm_cache: Dict[str, str] = {}

    def find_exact(
        self,
        source_text: str,
        segments: List[TMSegment],
        source_lang: str = "en",
        target_lang: str = "vi",
    ) -> Optional[MatchResult]:
        """
        Find exact match using hash lookup.

        O(n) where n = number of segments, but very fast due to hash comparison.
        """
        source_hash = compute_hash(source_text, source_lang, target_lang)

        for segment in segments:
            if segment.source_hash == source_hash:
                return MatchResult(
                    segment=segment,
                    similarity=1.0,
                    match_type=MatchType.EXACT,
                )

        return None

    def find_fuzzy(
        self,
        source_text: str,
        segments: List[TMSegment],
        min_similarity: float = None,
        max_results: int = 5,
    ) -> List[MatchResult]:
        """
        Find fuzzy matches using Levenshtein similarity.

        Args:
            source_text: Text to match
            segments: Segments to search
            min_similarity: Minimum similarity threshold
            max_results: Maximum matches to return

        Returns:
            List of matches sorted by similarity (descending)
        """
        min_similarity = min_similarity or self.fuzzy_threshold

        source_norm = self._normalize(source_text)
        source_words = len(source_text.split())

        matches = []

        for segment in segments:
            # Quick length filter (segments too different in length won't match)
            seg_words = segment.source_length
            if abs(seg_words - source_words) / max(seg_words, source_words) > 0.5:
                continue

            # Compute similarity
            seg_norm = self._normalize(segment.source_text)
            similarity = self._compute_similarity(source_norm, seg_norm)

            if similarity >= min_similarity:
                match_type = self._get_match_type(similarity)
                matches.append(MatchResult(
                    segment=segment,
                    similarity=similarity,
                    match_type=match_type,
                ))

        # Sort by similarity descending, then by quality score
        matches.sort(key=lambda m: (m.similarity, m.segment.quality_score), reverse=True)

        return matches[:max_results]

    def find_best(
        self,
        source_text: str,
        segments: List[TMSegment],
        source_lang: str = "en",
        target_lang: str = "vi",
        min_similarity: float = None,
    ) -> Optional[MatchResult]:
        """
        Find best match (exact first, then fuzzy).

        Args:
            source_text: Text to match
            segments: Segments to search
            source_lang: Source language
            target_lang: Target language
            min_similarity: Minimum similarity

        Returns:
            Best match or None
        """
        # Try exact match first (fast)
        exact = self.find_exact(source_text, segments, source_lang, target_lang)
        if exact:
            return exact

        # Fall back to fuzzy
        fuzzy = self.find_fuzzy(source_text, segments, min_similarity, max_results=1)
        return fuzzy[0] if fuzzy else None

    def batch_match(
        self,
        source_texts: List[str],
        segments: List[TMSegment],
        source_lang: str = "en",
        target_lang: str = "vi",
        min_similarity: float = None,
    ) -> List[Optional[MatchResult]]:
        """
        Find matches for multiple source texts.

        Args:
            source_texts: List of texts to match
            segments: Segments to search
            source_lang: Source language
            target_lang: Target language
            min_similarity: Minimum similarity

        Returns:
            List of best matches (None for no match)
        """
        # Build hash index for O(1) exact lookup
        hash_index: Dict[str, TMSegment] = {}
        for seg in segments:
            hash_index[seg.source_hash] = seg

        results = []

        for source_text in source_texts:
            # Try exact match first
            source_hash = compute_hash(source_text, source_lang, target_lang)
            if source_hash in hash_index:
                segment = hash_index[source_hash]
                results.append(MatchResult(
                    segment=segment,
                    similarity=1.0,
                    match_type=MatchType.EXACT,
                ))
                continue

            # Fall back to fuzzy
            fuzzy = self.find_fuzzy(source_text, segments, min_similarity, max_results=1)
            results.append(fuzzy[0] if fuzzy else None)

        return results

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        if text in self._norm_cache:
            return self._norm_cache[text]

        normalized = normalize_text(text)
        self._norm_cache[text] = normalized

        # Keep cache size bounded
        if len(self._norm_cache) > 10000:
            self._norm_cache.clear()

        return normalized

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two normalized texts.

        Uses SequenceMatcher which is based on Ratcliff/Obershelp algorithm.
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def _get_match_type(self, similarity: float) -> MatchType:
        """Determine match type from similarity score."""
        if similarity >= self.exact_threshold:
            return MatchType.EXACT
        elif similarity >= self.near_exact_threshold:
            return MatchType.NEAR_EXACT
        elif similarity >= self.fuzzy_threshold:
            return MatchType.FUZZY
        else:
            return MatchType.NO_MATCH

    def estimate_cost_factor(self, match: Optional[MatchResult]) -> float:
        """
        Estimate translation cost factor.

        Returns:
            0.0 for exact match (free)
            0.2 for near-exact (20% cost)
            0.5 for fuzzy (50% cost)
            1.0 for no match (full cost)
        """
        if match is None:
            return 1.0

        if match.match_type == MatchType.EXACT:
            return 0.0
        elif match.match_type == MatchType.NEAR_EXACT:
            return 0.2
        elif match.match_type == MatchType.FUZZY:
            return 0.5
        else:
            return 1.0


# Global instance
_matcher: Optional[TMMatcher] = None


def get_matcher() -> TMMatcher:
    """Get matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = TMMatcher()
    return _matcher
