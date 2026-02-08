"""
Post-Translation Consistency Checker.

Checks consistency BETWEEN translated chunks:
1. TERMINOLOGY: Same source term must be translated the same way
2. NAMES: Proper names must be consistent (not translated, or translated the same)
3. STYLE: Tone/register should not jump around
4. NUMBERS: Numbers/dates in source must appear in translation

No LLM calls — pure text analysis (fast + free).
Output: report + list of inconsistencies for optional LLM fix later.

Standalone module — no extraction or translation imports.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class InconsistencyType(str, Enum):
    TERMINOLOGY = "terminology"
    PROPER_NAME = "proper_name"
    STYLE = "style"
    NUMBERING = "numbering"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Inconsistency:
    """One detected inconsistency."""

    type: InconsistencyType
    severity: Severity
    description: str
    locations: List[int]  # chunk indices
    source_term: Optional[str] = None
    variants: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "description": self.description,
            "locations": self.locations,
            "source_term": self.source_term,
            "variants": self.variants,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ConsistencyReport:
    """Full consistency check report."""

    total_chunks: int
    issues_found: int
    high_severity: int
    medium_severity: int
    low_severity: int
    inconsistencies: List[Inconsistency]
    score: float  # 0.0 (terrible) - 1.0 (perfect)
    checked_at: float = 0.0

    @property
    def passed(self) -> bool:
        """No high severity issues."""
        return self.high_severity == 0

    def to_dict(self) -> dict:
        return {
            "total_chunks": self.total_chunks,
            "issues_found": self.issues_found,
            "high": self.high_severity,
            "medium": self.medium_severity,
            "low": self.low_severity,
            "score": round(self.score, 4),
            "passed": self.passed,
            "inconsistencies": [i.to_dict() for i in self.inconsistencies],
        }


# ---------------------------------------------------------------------------
# Common false positive proper names to ignore
# ---------------------------------------------------------------------------

_COMMON_FALSE_POSITIVES = {
    "The", "This", "That", "These", "Those",
    "However", "Therefore", "Moreover", "Furthermore",
    "In", "On", "At", "For", "With", "From", "Into",
    "Chapter", "Section", "Table", "Figure", "Part",
    "New", "Old", "First", "Last", "Next",
    "Mr", "Mrs", "Ms", "Dr", "Prof",
}


# ---------------------------------------------------------------------------
# Consistency Checker
# ---------------------------------------------------------------------------

class ConsistencyChecker:
    """Check translated chunks for cross-chunk consistency.

    Usage::

        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["English text 1...", "English text 2..."],
            translated_chunks=["Bản dịch 1...", "Bản dịch 2..."],
            glossary={"Machine Learning": "Học máy"},
        )

        if not report.passed:
            for issue in report.inconsistencies:
                print(issue.description)
    """

    def __init__(
        self,
        min_term_frequency: int = 2,
        name_pattern: Optional[re.Pattern] = None,
    ):
        self.min_term_frequency = min_term_frequency
        self.name_pattern = name_pattern or re.compile(
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
        )

    def check(
        self,
        source_chunks: List[str],
        translated_chunks: List[str],
        glossary: Optional[Dict[str, str]] = None,
        source_language: str = "en",
        target_language: str = "vi",
    ) -> ConsistencyReport:
        """Run all consistency checks.

        Args:
            source_chunks: Original text chunks (before translation).
            translated_chunks: Translated text chunks.
            glossary: Expected term mappings {source: target}.
            source_language: Source language code.
            target_language: Target language code.

        Returns:
            ConsistencyReport with all found issues.
        """
        start = time.time()

        if not translated_chunks:
            return ConsistencyReport(
                total_chunks=0,
                issues_found=0,
                high_severity=0,
                medium_severity=0,
                low_severity=0,
                inconsistencies=[],
                score=1.0,
                checked_at=time.time(),
            )

        if len(source_chunks) != len(translated_chunks):
            logger.warning(
                "Chunk count mismatch: %d source vs %d translated",
                len(source_chunks), len(translated_chunks),
            )

        issues: List[Inconsistency] = []

        # Check 1: Terminology consistency
        issues.extend(
            self._check_terminology(
                source_chunks, translated_chunks, glossary or {},
            )
        )

        # Check 2: Proper name consistency
        issues.extend(
            self._check_proper_names(source_chunks, translated_chunks)
        )

        # Check 3: Style consistency
        issues.extend(
            self._check_style(translated_chunks, target_language)
        )

        # Check 4: Number/date consistency
        issues.extend(
            self._check_numbers(source_chunks, translated_chunks)
        )

        # Calculate severity counts
        high = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in issues if i.severity == Severity.LOW)

        # Score: start at 1.0, deduct per issue
        score = 1.0
        score -= high * 0.15
        score -= medium * 0.05
        score -= low * 0.01
        score = max(0.0, min(1.0, score))

        report = ConsistencyReport(
            total_chunks=len(translated_chunks),
            issues_found=len(issues),
            high_severity=high,
            medium_severity=medium,
            low_severity=low,
            inconsistencies=issues,
            score=score,
            checked_at=time.time(),
        )

        logger.info(
            "Consistency: %d chunks, %d issues (H=%d M=%d L=%d), "
            "score=%.3f, duration=%.3fs",
            len(translated_chunks), len(issues),
            high, medium, low, score, time.time() - start,
        )

        return report

    # --- Check 1: Terminology ---

    def _check_terminology(
        self,
        source_chunks: List[str],
        translated_chunks: List[str],
        glossary: Dict[str, str],
    ) -> List[Inconsistency]:
        """Check that glossary terms are translated consistently."""
        issues = []

        for source_term, expected_translation in glossary.items():
            # Find chunks containing this source term
            chunks_with_term = []
            for i, src in enumerate(source_chunks):
                if source_term.lower() in src.lower():
                    chunks_with_term.append(i)

            if len(chunks_with_term) < self.min_term_frequency:
                continue

            # Check if expected translation appears in translated chunks
            missing_in = []
            for chunk_idx in chunks_with_term:
                if chunk_idx < len(translated_chunks):
                    trans = translated_chunks[chunk_idx]
                    if expected_translation.lower() not in trans.lower():
                        missing_in.append(chunk_idx)

            if missing_in:
                issues.append(Inconsistency(
                    type=InconsistencyType.TERMINOLOGY,
                    severity=Severity.HIGH,
                    description=(
                        f"Glossary term '{source_term}' should translate to "
                        f"'{expected_translation}' but may differ in "
                        f"chunks {missing_in}"
                    ),
                    locations=missing_in,
                    source_term=source_term,
                    variants=[expected_translation],
                    suggested_fix=(
                        f"Ensure '{source_term}' → '{expected_translation}' "
                        f"in all chunks"
                    ),
                ))

        return issues

    # --- Check 2: Proper Names ---

    def _check_proper_names(
        self,
        source_chunks: List[str],
        translated_chunks: List[str],
    ) -> List[Inconsistency]:
        """Detect proper names in source and check consistency in translation."""
        issues = []

        # Extract proper names from source
        name_occurrences: Dict[str, List[int]] = defaultdict(list)

        for i, src in enumerate(source_chunks):
            names = set(self.name_pattern.findall(src))
            for name in names:
                if len(name) < 4:
                    continue
                # Filter false positives
                first_word = name.split()[0] if name.split() else ""
                if first_word in _COMMON_FALSE_POSITIVES:
                    continue
                name_occurrences[name].append(i)

        # For names in 2+ chunks, check consistency
        for name, chunk_indices in name_occurrences.items():
            if len(chunk_indices) < self.min_term_frequency:
                continue

            present_in = []
            absent_from = []

            for idx in chunk_indices:
                if idx < len(translated_chunks):
                    if name in translated_chunks[idx]:
                        present_in.append(idx)
                    else:
                        absent_from.append(idx)

            if present_in and absent_from:
                issues.append(Inconsistency(
                    type=InconsistencyType.PROPER_NAME,
                    severity=Severity.MEDIUM,
                    description=(
                        f"Name '{name}' kept in chunks {present_in} "
                        f"but missing/changed in chunks {absent_from}"
                    ),
                    locations=absent_from,
                    source_term=name,
                    suggested_fix=f"Keep '{name}' consistent across all chunks",
                ))

        return issues

    # --- Check 3: Style ---

    def _check_style(
        self,
        translated_chunks: List[str],
        target_language: str,
    ) -> List[Inconsistency]:
        """Check for style/register shifts between chunks."""
        issues = []

        if len(translated_chunks) < 2:
            return issues

        # Compute sentence length profile per chunk
        profiles = []
        for chunk in translated_chunks:
            sentences = re.split(r'[.!?。！？]+', chunk)
            sentences = [s.strip() for s in sentences if s.strip()]
            if sentences:
                avg_len = sum(len(s) for s in sentences) / len(sentences)
                profiles.append(avg_len)
            else:
                profiles.append(0)

        # Check for dramatic sentence length shifts
        if len(profiles) >= 3:
            for i in range(1, len(profiles)):
                if profiles[i] > 0 and profiles[i - 1] > 0:
                    ratio = (
                        max(profiles[i], profiles[i - 1])
                        / min(profiles[i], profiles[i - 1])
                    )
                    if ratio > 3.0:
                        issues.append(Inconsistency(
                            type=InconsistencyType.STYLE,
                            severity=Severity.LOW,
                            description=(
                                f"Sentence length shift between chunk {i - 1} "
                                f"(avg {profiles[i - 1]:.0f} chars) and "
                                f"chunk {i} (avg {profiles[i]:.0f} chars)"
                            ),
                            locations=[i - 1, i],
                        ))

        # Vietnamese formality check
        if target_language in ("vi", "vie"):
            issues.extend(
                self._check_vietnamese_formality(translated_chunks)
            )

        return issues

    def _check_vietnamese_formality(
        self, chunks: List[str]
    ) -> List[Inconsistency]:
        """Vietnamese-specific: check formality register consistency."""
        issues = []

        formal_markers = ["quý vị", "quý khách", "thưa", "kính"]
        informal_markers = ["bạn", "cậu", "mày", "tao"]

        chunk_registers = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            formal_count = sum(chunk_lower.count(m) for m in formal_markers)
            informal_count = sum(chunk_lower.count(m) for m in informal_markers)

            if formal_count > informal_count and formal_count > 0:
                chunk_registers.append("formal")
            elif informal_count > formal_count and informal_count > 0:
                chunk_registers.append("informal")
            else:
                chunk_registers.append("neutral")

        registers_used = {r for r in chunk_registers if r != "neutral"}
        if len(registers_used) > 1:
            formal_chunks = [
                i for i, r in enumerate(chunk_registers) if r == "formal"
            ]
            informal_chunks = [
                i for i, r in enumerate(chunk_registers) if r == "informal"
            ]
            issues.append(Inconsistency(
                type=InconsistencyType.STYLE,
                severity=Severity.MEDIUM,
                description=(
                    f"Formality register inconsistent: "
                    f"formal in chunks {formal_chunks}, "
                    f"informal in chunks {informal_chunks}"
                ),
                locations=formal_chunks + informal_chunks,
                suggested_fix="Use consistent formality register throughout",
            ))

        return issues

    # --- Check 4: Numbers ---

    def _check_numbers(
        self,
        source_chunks: List[str],
        translated_chunks: List[str],
    ) -> List[Inconsistency]:
        """Check that numbers/dates in source appear in translation."""
        issues = []

        number_pattern = re.compile(r'\b\d{2,}\b')

        for i in range(min(len(source_chunks), len(translated_chunks))):
            source_numbers = set(number_pattern.findall(source_chunks[i]))
            trans_numbers = set(number_pattern.findall(translated_chunks[i]))

            missing = source_numbers - trans_numbers

            # Filter: check if digits appear in any format
            truly_missing = set()
            trans_clean = translated_chunks[i].replace(',', '').replace('.', '')
            for num in missing:
                if num.lstrip('0') not in trans_clean:
                    truly_missing.add(num)

            if truly_missing:
                issues.append(Inconsistency(
                    type=InconsistencyType.NUMBERING,
                    severity=Severity.HIGH,
                    description=(
                        f"Numbers {truly_missing} found in source chunk {i} "
                        f"but missing from translation"
                    ),
                    locations=[i],
                    source_term=", ".join(sorted(truly_missing)),
                    suggested_fix=(
                        f"Verify numbers {truly_missing} in chunk {i}"
                    ),
                ))

        return issues
