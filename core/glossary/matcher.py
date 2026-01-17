"""
Term Matcher
Engine for finding glossary terms in text.
"""
import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from functools import lru_cache

from .models import GlossaryTerm
from .repository import get_repository

logger = logging.getLogger(__name__)


@dataclass
class TermMatch:
    """A matched term in text."""
    source_term: str
    target_term: str
    start: int
    end: int
    glossary_id: str
    priority: int
    term_id: str


class TermMatcher:
    """
    Engine for finding glossary terms in source text.

    Features:
    - Exact and case-insensitive matching
    - Longest match first (prevents partial matches)
    - Priority-based selection for overlapping matches
    - Caching for frequently used glossaries
    """

    def __init__(self):
        """Initialize matcher."""
        self.repository = get_repository()
        self._term_cache: Dict[str, List[GlossaryTerm]] = {}

    def load_glossary(self, glossary_id: str) -> List[GlossaryTerm]:
        """
        Load terms for a glossary.

        Uses cache for repeated calls.
        Supports prebuilt: prefix for prebuilt glossaries.
        """
        if glossary_id not in self._term_cache:
            # Check if it's a prebuilt glossary
            if glossary_id.startswith("prebuilt:"):
                terms = self._load_prebuilt_glossary(glossary_id[9:])  # Remove prefix
            else:
                terms = self.repository.get_all_terms(glossary_id)
            self._term_cache[glossary_id] = terms
            logger.debug(f"Loaded {len(terms)} terms for glossary {glossary_id}")
        return self._term_cache[glossary_id]

    def _load_prebuilt_glossary(self, prebuilt_id: str) -> List[GlossaryTerm]:
        """Load terms from a prebuilt glossary JSON file."""
        import json
        from pathlib import Path

        prebuilt_dir = Path(__file__).parent / "prebuilt"
        file_path = prebuilt_dir / f"{prebuilt_id}.json"

        if not file_path.exists():
            logger.warning(f"Prebuilt glossary not found: {prebuilt_id}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            terms = []
            for t in data.get("terms", []):
                term = GlossaryTerm(
                    id=f"prebuilt_{prebuilt_id}_{len(terms)}",
                    glossary_id=f"prebuilt:{prebuilt_id}",
                    source_term=t.get("source") or t.get("source_term", ""),
                    target_term=t.get("target") or t.get("target_term", ""),
                    context=t.get("context"),
                    part_of_speech=t.get("part_of_speech"),
                    priority=t.get("priority", 5),
                    case_sensitive=t.get("case_sensitive", False),
                )
                terms.append(term)

            logger.info(f"Loaded {len(terms)} terms from prebuilt glossary: {prebuilt_id}")
            return terms
        except Exception as e:
            logger.error(f"Error loading prebuilt glossary {prebuilt_id}: {e}")
            return []

    def clear_cache(self, glossary_id: Optional[str] = None):
        """Clear term cache."""
        if glossary_id:
            self._term_cache.pop(glossary_id, None)
        else:
            self._term_cache.clear()

    def find_matches(
        self,
        text: str,
        glossary_ids: List[str],
        case_insensitive: bool = True,
    ) -> List[TermMatch]:
        """
        Find all glossary terms in the text.

        Args:
            text: Source text to search
            glossary_ids: List of glossary IDs to search
            case_insensitive: Whether to ignore case (default True)

        Returns:
            List of TermMatch objects sorted by position
        """
        if not text or not glossary_ids:
            return []

        # Collect all terms from all glossaries
        all_terms: List[tuple] = []  # (term, glossary_id)
        for gid in glossary_ids:
            terms = self.load_glossary(gid)
            for term in terms:
                all_terms.append((term, gid))

        if not all_terms:
            return []

        # Sort by length descending (longest match first)
        all_terms.sort(key=lambda x: len(x[0].source_term), reverse=True)

        matches: List[TermMatch] = []
        matched_positions: Set[tuple] = set()  # (start, end) pairs

        for term, glossary_id in all_terms:
            # Build regex pattern
            escaped = re.escape(term.source_term)
            flags = re.IGNORECASE if (case_insensitive and not term.case_sensitive) else 0

            # Word boundary matching
            pattern = rf'\b{escaped}\b'

            try:
                for match in re.finditer(pattern, text, flags):
                    start, end = match.start(), match.end()

                    # Check for overlap with existing matches
                    is_overlapping = any(
                        self._ranges_overlap(start, end, s, e)
                        for s, e in matched_positions
                    )

                    if not is_overlapping:
                        matches.append(TermMatch(
                            source_term=term.source_term,
                            target_term=term.target_term,
                            start=start,
                            end=end,
                            glossary_id=glossary_id,
                            priority=term.priority,
                            term_id=term.id,
                        ))
                        matched_positions.add((start, end))

            except re.error as e:
                logger.warning(f"Regex error for term '{term.source_term}': {e}")
                continue

        # Sort by position
        matches.sort(key=lambda m: m.start)

        logger.debug(f"Found {len(matches)} matches in text")
        return matches

    def _ranges_overlap(self, s1: int, e1: int, s2: int, e2: int) -> bool:
        """Check if two ranges overlap."""
        return not (e1 <= s2 or e2 <= s1)

    def highlight_matches(
        self,
        text: str,
        matches: List[TermMatch],
        format: str = "markdown",
    ) -> str:
        """
        Highlight matched terms in text.

        Args:
            text: Original text
            matches: List of matches from find_matches()
            format: Highlight format (markdown, html, plain)

        Returns:
            Text with highlighted terms
        """
        if not matches:
            return text

        # Sort matches by position (reverse for safe replacement)
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

        result = text
        for match in sorted_matches:
            before = result[:match.start]
            term_text = result[match.start:match.end]
            after = result[match.end:]

            if format == "markdown":
                highlighted = f"**{term_text}**"
            elif format == "html":
                highlighted = f"<mark>{term_text}</mark>"
            else:
                highlighted = f"[{term_text}]"

            result = before + highlighted + after

        return result

    def get_unique_terms(self, matches: List[TermMatch]) -> Dict[str, str]:
        """
        Get unique term pairs from matches.

        Returns:
            Dict mapping source_term → target_term
        """
        unique = {}
        for match in sorted(matches, key=lambda m: -m.priority):
            if match.source_term not in unique:
                unique[match.source_term] = match.target_term
        return unique

    def update_usage_counts(self, matches: List[TermMatch]):
        """Update usage counts for matched terms."""
        if not matches:
            return

        term_ids = list(set(m.term_id for m in matches))
        self.repository.increment_usage_count(term_ids)


# Global instance
_matcher: Optional[TermMatcher] = None


def get_matcher() -> TermMatcher:
    """Get or create the global matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = TermMatcher()
    return _matcher
