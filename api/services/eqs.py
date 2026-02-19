"""
Extraction Quality Score (EQS) — evaluate PDF text extraction quality.

Computes a 0.0–1.0 composite score from six independent signals:
  1. text_density    – chars-per-page vs expected range
  2. structure       – headings, paragraphs, lists detected
  3. encoding        – mojibake / garbled-char ratio
  4. language        – plausible natural-language content
  5. completeness    – extracted pages vs total pages
  6. format_integrity – LaTeX / markdown artefact preservation

The scorer is **standalone** — it does not import or depend on any
extraction module.  It operates on plain text + basic metadata.
"""

from __future__ import annotations

import re
import math
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SignalScore:
    """Individual signal result."""
    name: str
    score: float          # 0.0 – 1.0
    weight: float         # contribution weight
    details: str = ""     # human-readable explanation


@dataclass
class EQSReport:
    """Full extraction-quality report."""
    overall_score: float                # weighted composite 0.0–1.0
    grade: str                          # A / B / C / D / F
    signals: List[SignalScore] = field(default_factory=list)
    recommendation: str = ""            # human-readable next step
    metadata: Dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.overall_score >= 0.6

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 4),
            "grade": self.grade,
            "passed": self.passed,
            "signals": [
                {"name": s.name, "score": round(s.score, 4),
                 "weight": s.weight, "details": s.details}
                for s in self.signals
            ],
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

# Default signal weights (must sum to 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "text_density":     0.25,
    "structure":        0.15,
    "encoding":         0.20,
    "language":         0.20,
    "completeness":     0.10,
    "format_integrity": 0.10,
}

# Mojibake sequences — common garbled-encoding artefacts
_MOJIBAKE_PATTERNS = re.compile(
    r"[\ufffd\ufffe\ufeff]"          # replacement / BOM chars
    r"|Ã[\x80-\xbf]"                 # UTF-8 misread as latin-1
    r"|Â[\xa0-\xff]"                 # ditto
    r"|â\x80[\x90-\x9f]"            # ditto (dashes/quotes)
    r"|\x00"                         # null bytes
)

# Minimum expected chars-per-page for a "real" document
_MIN_CHARS_PER_PAGE = 100
_IDEAL_CHARS_PER_PAGE = 1500
_MAX_CHARS_PER_PAGE = 8000


class ExtractionQualityScorer:
    """Compute an Extraction Quality Score for extracted text."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, abs_tol=0.01):
            raise ValueError(
                f"Signal weights must sum to 1.0, got {total:.4f}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        text: str,
        total_pages: int = 1,
        expected_language: Optional[str] = None,
    ) -> EQSReport:
        """Score extracted text quality.

        Args:
            text: The full extracted text content.
            total_pages: Total pages in the source document.
            expected_language: ISO 639-1 code (e.g. "en", "vi", "ja").

        Returns:
            EQSReport with composite score and per-signal breakdown.
        """
        if not text or not text.strip():
            return EQSReport(
                overall_score=0.0,
                grade="F",
                signals=[],
                recommendation="No text extracted. Try OCR or Vision extraction.",
                metadata={"total_pages": total_pages, "text_length": 0},
            )

        signals = [
            self._score_text_density(text, total_pages),
            self._score_structure(text),
            self._score_encoding(text),
            self._score_language(text, expected_language),
            self._score_completeness(text, total_pages),
            self._score_format_integrity(text),
        ]

        overall = sum(s.score * s.weight for s in signals)
        grade = self._grade(overall)
        recommendation = self._recommend(grade, signals)

        report = EQSReport(
            overall_score=overall,
            grade=grade,
            signals=signals,
            recommendation=recommendation,
            metadata={
                "total_pages": total_pages,
                "text_length": len(text),
                "expected_language": expected_language,
            },
        )

        logger.debug(
            "EQS score=%.3f grade=%s pages=%d len=%d",
            overall, grade, total_pages, len(text),
        )
        return report

    # ------------------------------------------------------------------
    # Signal scorers
    # ------------------------------------------------------------------

    def _score_text_density(self, text: str, total_pages: int) -> SignalScore:
        """Chars-per-page within expected range → higher score."""
        chars = len(text.strip())
        pages = max(total_pages, 1)
        cpp = chars / pages

        if cpp < _MIN_CHARS_PER_PAGE:
            score = cpp / _MIN_CHARS_PER_PAGE * 0.4  # low density
        elif cpp <= _IDEAL_CHARS_PER_PAGE:
            score = 0.4 + 0.6 * (cpp - _MIN_CHARS_PER_PAGE) / (
                _IDEAL_CHARS_PER_PAGE - _MIN_CHARS_PER_PAGE
            )
        elif cpp <= _MAX_CHARS_PER_PAGE:
            score = 1.0
        else:
            overshoot = (cpp - _MAX_CHARS_PER_PAGE) / _MAX_CHARS_PER_PAGE
            score = max(0.5, 1.0 - overshoot)

        return SignalScore(
            name="text_density",
            score=min(score, 1.0),
            weight=self.weights["text_density"],
            details=f"{cpp:.0f} chars/page ({chars} chars, {pages} pages)",
        )

    def _score_structure(self, text: str) -> SignalScore:
        """Detect structural elements (headings, lists, paragraphs)."""
        lines = text.split("\n")
        total_lines = len(lines)
        if total_lines == 0:
            return SignalScore(
                name="structure", score=0.0,
                weight=self.weights["structure"],
                details="No lines found",
            )

        non_empty = [ln for ln in lines if ln.strip()]
        headings = sum(
            1 for ln in non_empty
            if re.match(r"^#{1,6}\s", ln)           # markdown headings
            or re.match(r"^(Chapter|Section)\s", ln, re.I)
            or (len(ln.strip()) < 80 and ln.strip().isupper())
        )
        list_items = sum(
            1 for ln in non_empty
            if re.match(r"^\s*[-•*]\s", ln)
            or re.match(r"^\s*\d+[.)]\s", ln)
        )
        paragraphs = sum(
            1 for ln in non_empty
            if len(ln.strip()) > 40 and not ln.strip().startswith("#")
        )

        structure_ratio = min(
            (headings * 3 + list_items + paragraphs) / max(len(non_empty), 1),
            1.0,
        )
        score = min(structure_ratio * 1.5, 1.0)

        return SignalScore(
            name="structure",
            score=score,
            weight=self.weights["structure"],
            details=(
                f"{headings} headings, {list_items} list items, "
                f"{paragraphs} paragraphs in {len(non_empty)} lines"
            ),
        )

    def _score_encoding(self, text: str) -> SignalScore:
        """Penalise mojibake / garbled characters."""
        total_chars = len(text)
        if total_chars == 0:
            return SignalScore(
                name="encoding", score=1.0,
                weight=self.weights["encoding"],
                details="Empty text",
            )

        mojibake_count = len(_MOJIBAKE_PATTERNS.findall(text))

        # Also count Unicode "replacement character" category
        replacement_count = sum(
            1 for ch in text
            if unicodedata.category(ch) == "Cn"  # unassigned
        )

        bad_ratio = (mojibake_count + replacement_count) / total_chars
        score = max(0.0, 1.0 - bad_ratio * 50)  # 2% bad chars → score 0

        return SignalScore(
            name="encoding",
            score=score,
            weight=self.weights["encoding"],
            details=f"{mojibake_count} mojibake + {replacement_count} unassigned in {total_chars} chars",
        )

    def _score_language(
        self, text: str, expected_language: Optional[str]
    ) -> SignalScore:
        """Check that text looks like natural language."""
        words = text.split()
        if len(words) < 5:
            return SignalScore(
                name="language", score=0.3,
                weight=self.weights["language"],
                details="Too few words to assess",
            )

        # Proportion of "word-like" tokens (letters + common punct)
        word_like = sum(
            1 for w in words
            if re.match(r"^[\w'''-]+$", w, re.UNICODE)
        )
        word_ratio = word_like / len(words)

        # Average word length sanity
        avg_len = sum(len(w) for w in words) / len(words)
        len_ok = 1.0 if 2.0 <= avg_len <= 15.0 else 0.5

        # CJK boost: if expected language is CJK, accept single-char words
        if expected_language in ("ja", "zh", "ko"):
            cjk_chars = sum(
                1 for ch in text
                if "\u4e00" <= ch <= "\u9fff"
                or "\u3040" <= ch <= "\u30ff"
                or "\uac00" <= ch <= "\ud7af"
            )
            cjk_ratio = cjk_chars / max(len(text), 1)
            if cjk_ratio > 0.1:
                word_ratio = max(word_ratio, 0.8)
                len_ok = 1.0

        score = word_ratio * 0.7 + len_ok * 0.3

        return SignalScore(
            name="language",
            score=min(score, 1.0),
            weight=self.weights["language"],
            details=f"{word_ratio:.1%} word-like tokens, avg length {avg_len:.1f}",
        )

    def _score_completeness(self, text: str, total_pages: int) -> SignalScore:
        """Rough check: did we extract content from all pages?

        Heuristic: expect at least ~50 chars per page on average.
        """
        chars = len(text.strip())
        pages = max(total_pages, 1)
        expected_min = pages * 50  # very conservative

        if chars >= expected_min:
            score = 1.0
        elif chars > 0:
            score = chars / expected_min
        else:
            score = 0.0

        return SignalScore(
            name="completeness",
            score=min(score, 1.0),
            weight=self.weights["completeness"],
            details=f"{chars} chars for {pages} pages (expect ≥{expected_min})",
        )

    def _score_format_integrity(self, text: str) -> SignalScore:
        """Check preservation of formatting artefacts (LaTeX, markdown)."""
        # Count format markers
        latex_inline = len(re.findall(r"\$[^$]+\$", text))
        latex_block = len(re.findall(r"\$\$[^$]+\$\$", text))
        md_headings = len(re.findall(r"^#{1,6}\s", text, re.MULTILINE))
        md_bold = len(re.findall(r"\*\*[^*]+\*\*", text))
        md_links = len(re.findall(r"\[.*?\]\(.*?\)", text))

        total_markers = (
            latex_inline + latex_block + md_headings + md_bold + md_links
        )

        if total_markers == 0:
            # No formatting expected → neutral score
            return SignalScore(
                name="format_integrity",
                score=0.7,
                weight=self.weights["format_integrity"],
                details="No format markers detected (neutral)",
            )

        # Check for broken markers (unmatched delimiters)
        unmatched_dollars = text.count("$") - 2 * (latex_inline + 2 * latex_block)
        broken_ratio = max(0, unmatched_dollars) / max(total_markers, 1)

        score = max(0.0, 1.0 - broken_ratio * 0.5)

        return SignalScore(
            name="format_integrity",
            score=min(score, 1.0),
            weight=self.weights["format_integrity"],
            details=(
                f"{total_markers} markers "
                f"(LaTeX:{latex_inline}+{latex_block}, "
                f"MD:{md_headings}h/{md_bold}b/{md_links}l)"
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 0.9:
            return "A"
        if score >= 0.75:
            return "B"
        if score >= 0.6:
            return "C"
        if score >= 0.4:
            return "D"
        return "F"

    @staticmethod
    def _recommend(grade: str, signals: List[SignalScore]) -> str:
        if grade in ("A", "B"):
            return "Extraction quality is good. Proceed with translation."

        # Find worst signal
        worst = min(signals, key=lambda s: s.score) if signals else None
        if worst is None:
            return "Unable to assess quality."

        recommendations = {
            "text_density": "Low text density. Consider OCR or Vision extraction.",
            "structure": "Poor document structure. Try Vision extraction for better layout.",
            "encoding": "Encoding issues detected. Re-extract with different encoding or use OCR.",
            "language": "Text doesn't appear to be natural language. May need OCR.",
            "completeness": "Incomplete extraction. Some pages may be missing.",
            "format_integrity": "Format markers are damaged. Try Vision extraction.",
        }
        return recommendations.get(
            worst.name,
            f"Weak signal: {worst.name} ({worst.score:.2f}). Consider re-extraction.",
        )
