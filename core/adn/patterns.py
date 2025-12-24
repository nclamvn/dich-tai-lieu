#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structural Pattern Detector

Detects repeating structural patterns in documents:
- Chapter/section markers
- Quote blocks
- Dialogue patterns
- List structures
- Footnotes

Version: 1.0.0
"""

import re
from typing import List, Dict, Tuple
from collections import Counter

from .schema import Pattern, PatternType


class PatternDetector:
    """
    Detect structural patterns in document content.
    """

    # Pattern definitions by type and language
    PATTERN_RULES = {
        PatternType.CHAPTER_START: {
            'en': [
                r'^(?:Chapter|CHAPTER)\s+(?:\d+|[IVXLCDM]+)',
                r'^(?:Part|PART)\s+(?:\d+|[IVXLCDM]+)',
                r'^(?:Section|SECTION)\s+\d+(?:\.\d+)*',
                r'^(?:Book|BOOK)\s+(?:\d+|[IVXLCDM]+)',
                r'^\d+\.\s+[A-Z][a-z]+',  # Numbered chapter: "1. Introduction"
            ],
            'vi': [
                r'^(?:Chương|CHƯƠNG)\s+(?:\d+|[IVXLCDM]+)',
                r'^(?:Phần|PHẦN)\s+(?:\d+|[IVXLCDM]+)',
                r'^(?:Mục|MỤC)\s+\d+(?:\.\d+)*',
                r'^(?:Quyển|QUYỂN)\s+(?:\d+|[IVXLCDM]+)',
            ],
            'ja': [
                r'^第[一二三四五六七八九十百千]+章',
                r'^第\d+章',
                r'^[一二三四五六七八九十]+\s*[、．]',
            ],
            'zh': [
                r'^第[一二三四五六七八九十百千]+章',
                r'^第\d+章',
                r'^[一二三四五六七八九十]+[、．]',
            ],
            'ko': [
                r'^제\s*\d+\s*장',
                r'^제\s*[일이삼사오육칠팔구십]+\s*장',
            ],
        },
        PatternType.SECTION_BREAK: {
            'en': [
                r'^\s*\*\s*\*\s*\*\s*$',
                r'^\s*-{3,}\s*$',
                r'^\s*#{3,}\s*$',
                r'^\s*={3,}\s*$',
                r'^\s*~{3,}\s*$',
                r'^\s*•\s*•\s*•\s*$',
            ],
            'vi': [
                r'^\s*\*\s*\*\s*\*\s*$',
                r'^\s*-{3,}\s*$',
                r'^\s*oOo\s*$',
            ],
            'ja': [
                r'^\s*\*\s*\*\s*\*\s*$',
                r'^\s*―{3,}\s*$',
                r'^\s*・・・\s*$',
            ],
            'zh': [
                r'^\s*\*\s*\*\s*\*\s*$',
                r'^\s*—{3,}\s*$',
            ],
            'ko': [
                r'^\s*\*\s*\*\s*\*\s*$',
                r'^\s*-{3,}\s*$',
            ],
        },
        PatternType.QUOTE_BLOCK: {
            'en': [
                r'^>\s+.+',  # Markdown quote
                r'^[""].+[""]\s*$',  # Full quoted line
                r'^『.+』\s*$',  # Asian-style quotes
            ],
            'vi': [
                r'^>\s+.+',
                r'^[""].+[""]\s*$',
                r'^«.+»\s*$',
            ],
            'ja': [
                r'^「.+」\s*$',
                r'^『.+』\s*$',
                r'^>.+',
            ],
            'zh': [
                r'^「.+」\s*$',
                r'^『.+』\s*$',
                r'^".+"$',
            ],
            'ko': [
                r'^".+"$',
                r'^『.+』$',
            ],
        },
        PatternType.DIALOGUE: {
            'en': [
                r'^[""].+?[""]\s*(?:said|asked|replied|whispered|shouted|muttered|exclaimed)',
                r'^—\s*.+',
                r'^"\s*.+\s*"$',
            ],
            'vi': [
                r'^[-–—]\s*.+',
                r'^[""].+?[""]\s*[-–—]',
            ],
            'ja': [
                r'^「.+?」と.+?(?:言った|聞いた|答えた|叫んだ|囁いた)',
                r'^「.+」$',
            ],
            'zh': [
                r'^「.+?」.+?(?:说|问|答|喊|叫)',
                r'^".+?"',
            ],
            'ko': [
                r'^".+?"',
                r'^「.+」',
            ],
        },
        PatternType.LIST_STRUCTURE: {
            'en': [
                r'^\s*[-*•]\s+.+',  # Bullet list
                r'^\s*\d+[.\)]\s+.+',  # Numbered list
                r'^\s*[a-z][.\)]\s+.+',  # Letter list
                r'^\s*\([a-z0-9]+\)\s+.+',  # Parenthesized
            ],
            'vi': [
                r'^\s*[-*•]\s+.+',
                r'^\s*\d+[.\)]\s+.+',
                r'^\s*[a-z][.\)]\s+.+',
            ],
            'ja': [
                r'^\s*[・•]\s*.+',
                r'^\s*\d+[.\)．）]\s*.+',
                r'^\s*[①②③④⑤⑥⑦⑧⑨⑩].+',
            ],
            'zh': [
                r'^\s*[・•]\s*.+',
                r'^\s*\d+[.\)．）]\s*.+',
                r'^\s*[①②③④⑤⑥⑦⑧⑨⑩].+',
            ],
            'ko': [
                r'^\s*[-*•]\s+.+',
                r'^\s*\d+[.\)]\s+.+',
            ],
        },
        PatternType.FOOTNOTE: {
            'en': [
                r'\[\d+\]',  # [1], [2], etc.
                r'\*{1,3}(?!\*)',  # *, **, ***
                r'†|‡',  # Dagger symbols
            ],
            'vi': [
                r'\[\d+\]',
                r'\*{1,3}(?!\*)',
            ],
            'ja': [
                r'[※＊]\d*',
                r'\[\d+\]',
                r'注\d+',
            ],
            'zh': [
                r'\[\d+\]',
                r'[※＊]\d*',
            ],
            'ko': [
                r'\[\d+\]',
                r'\*{1,3}(?!\*)',
            ],
        },
        PatternType.EMPHASIS: {
            'en': [
                r'\*\*.+?\*\*',  # Bold markdown
                r'\*.+?\*',  # Italic markdown
                r'__.+?__',  # Bold underscore
                r'_.+?_',  # Italic underscore
            ],
            'vi': [
                r'\*\*.+?\*\*',
                r'\*.+?\*',
            ],
            'ja': [
                r'【.+?】',  # Japanese brackets
                r'《.+?》',
            ],
            'zh': [
                r'【.+?】',
                r'《.+?》',
            ],
            'ko': [
                r'\*\*.+?\*\*',
                r'【.+?】',
            ],
        },
    }

    def __init__(self, language: str = 'en'):
        """
        Initialize pattern detector.

        Args:
            language: Language code (en, vi, ja, zh, ko)
        """
        self.language = language.lower()[:2]

    def detect(self, segments: List[str]) -> List[Pattern]:
        """
        Detect all patterns in the document.

        Args:
            segments: List of text segments

        Returns:
            List of Pattern objects
        """
        results = []
        full_text = '\n'.join(segments)

        for pattern_type, lang_patterns in self.PATTERN_RULES.items():
            # Get patterns for current language, fallback to English
            patterns = lang_patterns.get(self.language, lang_patterns.get('en', []))

            for regex in patterns:
                occurrences = 0
                examples = []

                # Search in each segment/line
                for segment in segments:
                    for line in segment.split('\n'):
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue

                        try:
                            if re.search(regex, line_stripped, re.UNICODE):
                                occurrences += 1
                                if len(examples) < 3:
                                    # Truncate long examples
                                    example = line_stripped[:100]
                                    if len(line_stripped) > 100:
                                        example += '...'
                                    examples.append(example)
                        except re.error:
                            continue

                if occurrences > 0:
                    results.append(Pattern(
                        type=pattern_type,
                        markers=self._extract_markers(regex, examples),
                        regex=regex,
                        occurrences=occurrences,
                        examples=examples,
                    ))
                    # Only use first matching pattern for each type
                    break

        return results

    def detect_custom_patterns(
        self,
        segments: List[str],
        min_occurrences: int = 3
    ) -> List[Pattern]:
        """
        Detect custom repeating patterns not in predefined rules.
        Uses frequency analysis to find structural repetitions.

        Args:
            segments: List of text segments
            min_occurrences: Minimum times a pattern must appear

        Returns:
            List of detected custom patterns
        """
        # Collect line beginnings
        line_starts = Counter()
        full_lines = Counter()

        for segment in segments:
            for line in segment.split('\n'):
                line = line.strip()
                if len(line) < 3:
                    continue

                # Extract patterns from line beginnings
                # First 15 chars or until first space
                words = line.split()
                if words:
                    first_word = words[0]
                    if len(first_word) >= 2:
                        line_starts[first_word] += 1

                # Short lines might be structural markers
                if 3 <= len(line) <= 30:
                    full_lines[line] += 1

        # Find frequent patterns
        custom_patterns = []

        # From line starts
        for start, count in line_starts.most_common(10):
            if count >= min_occurrences:
                # Skip common words
                if start.lower() in ['the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were']:
                    continue

                # Try to generalize the pattern
                generalized = self._generalize_pattern(start)

                custom_patterns.append(Pattern(
                    type=PatternType.OTHER,
                    markers=[start],
                    regex=generalized,
                    occurrences=count,
                    examples=[start],
                ))

        # From full short lines (likely structural markers)
        for line, count in full_lines.most_common(5):
            if count >= min_occurrences:
                custom_patterns.append(Pattern(
                    type=PatternType.OTHER,
                    markers=[line],
                    regex=f'^{re.escape(line)}$',
                    occurrences=count,
                    examples=[line],
                ))

        return custom_patterns

    def _extract_markers(self, regex: str, examples: List[str]) -> List[str]:
        """Extract human-readable markers from pattern"""
        markers = []

        # Extract literal strings from regex
        literals = re.findall(r'[A-Za-z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+', regex)
        for lit in literals[:3]:
            if len(lit) >= 2 and lit not in markers:
                markers.append(lit)

        # Add example prefixes
        for ex in examples[:2]:
            words = ex.split()
            if words:
                prefix = words[0]
                if prefix and prefix not in markers and len(prefix) >= 2:
                    markers.append(prefix)

        return markers[:5]  # Limit to 5 markers

    def _generalize_pattern(self, text: str) -> str:
        """Convert specific text to regex pattern"""
        # Replace numbers with \d+
        pattern = re.sub(r'\d+', r'\\d+', text)

        # Escape special regex chars (except already replaced)
        special_chars = r'\.^$*+?{}[]|()'
        for char in special_chars:
            if char != '\\':
                pattern = pattern.replace(char, '\\' + char)

        # Re-fix the \d+ patterns
        pattern = pattern.replace('\\\\d\\+', '\\d+')

        return f'^{pattern}'

    def get_document_structure_summary(self, segments: List[str]) -> Dict:
        """
        Get a summary of document structure.

        Args:
            segments: List of text segments

        Returns:
            Dictionary with structure summary
        """
        patterns = self.detect(segments)
        custom = self.detect_custom_patterns(segments)

        # Count by type
        by_type = {}
        for p in patterns + custom:
            type_name = p.type.value
            if type_name not in by_type:
                by_type[type_name] = 0
            by_type[type_name] += p.occurrences

        return {
            'total_patterns': len(patterns) + len(custom),
            'standard_patterns': len(patterns),
            'custom_patterns': len(custom),
            'by_type': by_type,
            'has_chapters': by_type.get('chapter_start', 0) > 0,
            'has_lists': by_type.get('list_structure', 0) > 0,
            'has_dialogue': by_type.get('dialogue', 0) > 0,
        }
