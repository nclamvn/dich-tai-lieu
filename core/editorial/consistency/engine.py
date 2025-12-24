#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consistency Engine

Checks and enforces consistency across the document:
- Terminology usage
- Style consistency
- Numbering consistency
- Reference validation

Version: 1.0.0
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging
import re
from collections import Counter

from core.contracts import (
    ManuscriptCoreOutput,
    Segment,
    ConsistencyReport,
)

logger = logging.getLogger(__name__)


@dataclass
class TermInconsistency:
    """A terminology inconsistency"""
    term: str
    variants: List[str]
    occurrences: Dict[str, List[int]]  # variant -> segment indices
    suggested_standard: str
    severity: str = "warning"  # warning, error

    def to_dict(self) -> Dict:
        return {
            "term": self.term,
            "variants": self.variants,
            "occurrences": self.occurrences,
            "suggested_standard": self.suggested_standard,
            "severity": self.severity,
        }


@dataclass
class StyleInconsistency:
    """A style inconsistency"""
    issue_type: str  # heading_style, quote_style, list_style
    description: str
    segment_indices: List[int]
    examples: List[str]
    suggestion: str

    def to_dict(self) -> Dict:
        return {
            "issue_type": self.issue_type,
            "description": self.description,
            "segment_indices": self.segment_indices,
            "examples": self.examples[:3],
            "suggestion": self.suggestion,
        }


class ConsistencyEngine:
    """
    Engine for checking document consistency.

    Usage:
        engine = ConsistencyEngine()
        report = engine.check(manuscript_output)
    """

    def __init__(
        self,
        strict: bool = False,
        custom_terms: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize consistency engine.

        Args:
            strict: If True, treat warnings as errors
            custom_terms: Custom terminology mappings
        """
        self.strict = strict
        self.custom_terms = custom_terms or {}

        # Term variation patterns
        self.variation_patterns = [
            (r'\bA\.?I\.?\b', 'AI'),  # AI, A.I., A.I
            (r'\be-?mail\b', 'email', re.IGNORECASE),
            (r'\bweb-?site\b', 'website', re.IGNORECASE),
        ]

    def check(self, manuscript: ManuscriptCoreOutput) -> ConsistencyReport:
        """
        Run all consistency checks on a manuscript.

        Args:
            manuscript: ManuscriptCoreOutput from Agent #1

        Returns:
            ConsistencyReport with all findings
        """
        logger.info("Running consistency checks...")

        report = ConsistencyReport()

        # 1. Check terminology
        term_issues = self._check_terminology(manuscript)
        report.term_inconsistencies = [t.to_dict() for t in term_issues]

        # 2. Check style
        style_issues = self._check_style(manuscript)
        report.style_inconsistencies = [s.to_dict() for s in style_issues]

        # 3. Check numbering
        numbering_issues = self._check_numbering(manuscript)
        report.numbering_issues = numbering_issues

        # 4. Check references
        reference_issues = self._check_references(manuscript)
        report.reference_issues = reference_issues

        # Count resolved/unresolved
        total_issues = (
            len(report.term_inconsistencies) +
            len(report.style_inconsistencies) +
            len(report.numbering_issues) +
            len(report.reference_issues)
        )
        report.unresolved_count = total_issues

        logger.info(f"Consistency check complete: {total_issues} issues found")

        return report

    def _check_terminology(self, manuscript: ManuscriptCoreOutput) -> List[TermInconsistency]:
        """Check terminology consistency"""
        issues = []

        # Collect all terms from ADN
        adn_terms = manuscript.adn.get("terms", [])

        # Build term -> variants mapping
        term_variants: Dict[str, Dict[str, List[int]]] = {}

        for idx, segment in enumerate(manuscript.segments):
            text = segment.translated_text.lower()

            # Check ADN terms
            for term_data in adn_terms:
                original = term_data.get("original", "").lower()
                translation = term_data.get("translation", "").lower()

                if original in text or translation in text:
                    key = original
                    if key not in term_variants:
                        term_variants[key] = {}

                    # Find actual variant used
                    for variant in [original, translation]:
                        if variant in text:
                            if variant not in term_variants[key]:
                                term_variants[key][variant] = []
                            term_variants[key][variant].append(idx)

        # Find terms with multiple variants
        for term, variants in term_variants.items():
            if len(variants) > 1:
                # Find most common variant
                most_common = max(variants.items(), key=lambda x: len(x[1]))[0]

                issues.append(TermInconsistency(
                    term=term,
                    variants=list(variants.keys()),
                    occurrences=variants,
                    suggested_standard=most_common,
                ))

        return issues

    def _check_style(self, manuscript: ManuscriptCoreOutput) -> List[StyleInconsistency]:
        """Check style consistency"""
        issues = []

        # Check heading styles
        heading_styles = self._analyze_heading_styles(manuscript)
        if heading_styles:
            issues.extend(heading_styles)

        # Check quote styles
        quote_styles = self._analyze_quote_styles(manuscript)
        if quote_styles:
            issues.extend(quote_styles)

        # Check list styles
        list_styles = self._analyze_list_styles(manuscript)
        if list_styles:
            issues.extend(list_styles)

        return issues

    def _analyze_heading_styles(self, manuscript: ManuscriptCoreOutput) -> List[StyleInconsistency]:
        """Analyze heading style consistency"""
        issues = []

        # Collect heading patterns
        heading_patterns = {
            "chapter_colon": 0,      # Chapter 1: Title
            "chapter_dash": 0,       # Chapter 1 - Title
            "chapter_dot": 0,        # Chapter 1. Title
            "number_only": 0,        # 1. Title
        }

        examples: Dict[str, List[Tuple[int, str]]] = {k: [] for k in heading_patterns.keys()}

        for idx, segment in enumerate(manuscript.segments):
            text = segment.translated_text.strip()

            if re.match(r'^(?:Chapter|Chương|第)\s*\d+\s*:', text, re.IGNORECASE):
                heading_patterns["chapter_colon"] += 1
                examples["chapter_colon"].append((idx, text[:50]))
            elif re.match(r'^(?:Chapter|Chương|第)\s*\d+\s*[-–—]', text, re.IGNORECASE):
                heading_patterns["chapter_dash"] += 1
                examples["chapter_dash"].append((idx, text[:50]))
            elif re.match(r'^(?:Chapter|Chương|第)\s*\d+\.', text, re.IGNORECASE):
                heading_patterns["chapter_dot"] += 1
                examples["chapter_dot"].append((idx, text[:50]))

        # Check for inconsistency
        used_patterns = {k: v for k, v in heading_patterns.items() if v > 0}

        if len(used_patterns) > 1:
            most_common = max(used_patterns.items(), key=lambda x: x[1])[0]

            for pattern, count in used_patterns.items():
                if pattern != most_common:
                    issues.append(StyleInconsistency(
                        issue_type="heading_style",
                        description=f"Inconsistent heading style: {pattern} used {count} times",
                        segment_indices=[e[0] for e in examples[pattern]],
                        examples=[e[1] for e in examples[pattern]],
                        suggestion=f"Standardize to {most_common} style",
                    ))

        return issues

    def _analyze_quote_styles(self, manuscript: ManuscriptCoreOutput) -> List[StyleInconsistency]:
        """Analyze quote style consistency"""
        issues = []

        quote_chars: Counter = Counter()

        for segment in manuscript.segments:
            text = segment.translated_text

            # Count quote characters
            for char in ['"', '"', '"', '「', '」', '『', '』', "'", "'"]:
                quote_chars[char] += text.count(char)

        # Check for mixed styles
        western_quotes = quote_chars['"'] + quote_chars['"'] + quote_chars['"']
        asian_quotes = quote_chars['「'] + quote_chars['」'] + quote_chars['『'] + quote_chars['』']

        if western_quotes > 0 and asian_quotes > 0:
            issues.append(StyleInconsistency(
                issue_type="quote_style",
                description="Mixed Western and Asian quote styles",
                segment_indices=[],
                examples=[],
                suggestion="Standardize to one quote style based on target language",
            ))

        return issues

    def _analyze_list_styles(self, manuscript: ManuscriptCoreOutput) -> List[StyleInconsistency]:
        """Analyze list style consistency"""
        # Similar implementation for list styles
        return []

    def _check_numbering(self, manuscript: ManuscriptCoreOutput) -> List[Dict]:
        """Check numbering consistency"""
        issues = []

        # Track chapter numbers
        chapter_numbers: List[Tuple[int, int]] = []

        for idx, segment in enumerate(manuscript.segments):
            text = segment.translated_text.strip()

            # Extract chapter number
            match = re.match(r'^(?:Chapter|Chương|第)\s*(\d+)', text, re.IGNORECASE)
            if match:
                chapter_numbers.append((idx, int(match.group(1))))

        # Check for gaps or duplicates
        if chapter_numbers:
            numbers = [n[1] for n in chapter_numbers]

            # Check for duplicates
            duplicates = [n for n in set(numbers) if numbers.count(n) > 1]
            if duplicates:
                issues.append({
                    "type": "duplicate_chapter",
                    "description": f"Duplicate chapter numbers: {duplicates}",
                    "severity": "error",
                })

            # Check for gaps
            expected = list(range(min(numbers), max(numbers) + 1))
            missing = set(expected) - set(numbers)
            if missing:
                issues.append({
                    "type": "missing_chapter",
                    "description": f"Missing chapter numbers: {sorted(missing)}",
                    "severity": "warning",
                })

        return issues

    def _check_references(self, manuscript: ManuscriptCoreOutput) -> List[Dict]:
        """Check reference consistency"""
        issues = []

        # Find all references (e.g., [1], Figure 1, Table 1)
        references: Dict[str, List[str]] = {
            "citations": [],
            "figures": [],
            "tables": [],
        }

        for idx, segment in enumerate(manuscript.segments):
            text = segment.translated_text

            # Find citations
            citations = re.findall(r'\[(\d+)\]', text)
            references["citations"].extend(citations)

            # Find figure references
            figures = re.findall(r'(?:Figure|Hình)\s*(\d+)', text, re.IGNORECASE)
            references["figures"].extend(figures)

            # Find table references
            tables = re.findall(r'(?:Table|Bảng)\s*(\d+)', text, re.IGNORECASE)
            references["tables"].extend(tables)

        # Check for undefined references (would need actual definitions)
        # For now, just check for gaps
        for ref_type, refs in references.items():
            if refs:
                numbers = [int(r) for r in refs]
                expected = list(range(1, max(numbers) + 1))
                missing = set(expected) - set(numbers)

                if missing and len(missing) < len(numbers):
                    issues.append({
                        "type": f"missing_{ref_type}",
                        "description": f"Referenced but not defined: {sorted(missing)}",
                        "severity": "warning",
                    })

        return issues

    def auto_fix(
        self,
        manuscript: ManuscriptCoreOutput,
        report: ConsistencyReport,
    ) -> ManuscriptCoreOutput:
        """
        Attempt to auto-fix consistency issues.

        Args:
            manuscript: Original manuscript
            report: Consistency report

        Returns:
            Fixed manuscript
        """
        # Create a copy to modify
        fixed = manuscript  # In production, deep copy

        # Fix terminology
        for term_issue in report.term_inconsistencies:
            standard = term_issue.get("suggested_standard", "")

            if standard:
                for variant in term_issue.get("variants", []):
                    if variant != standard:
                        for idx in term_issue.get("occurrences", {}).get(variant, []):
                            if idx < len(fixed.segments):
                                # Replace variant with standard
                                fixed.segments[idx].translated_text = (
                                    fixed.segments[idx].translated_text.replace(
                                        variant, standard
                                    )
                                )

        report.resolved_count = len(report.term_inconsistencies)

        return fixed
