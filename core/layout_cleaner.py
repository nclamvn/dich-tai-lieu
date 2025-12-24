#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Layout Cleaner
==============
Cleans up document layout issues from multi-column PDFs.

PRIORITY: Clear structure > Perfect visual fidelity

Author: AI Translator Pro Team
Version: 1.0.0
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import Counter


@dataclass
class ContentPattern:
    """Represents repeating content (header/footer)"""
    text: str
    occurrences: int
    positions: List[int]  # Page numbers or positions
    is_header: bool = True


@dataclass
class DocumentSection:
    """Represents a logical document section"""
    title: str
    start_pos: int
    end_pos: int
    content: str
    section_type: str  # 'title', 'author', 'abstract', 'intro', 'section', 'references'


class LayoutCleaner:
    """
    Cleans up layout issues from PDF extraction:
    - Removes repeating headers/footers
    - Fixes multi-column reflow
    - Segments document into logical sections
    """

    def __init__(self):
        # Common header/footer patterns
        self.header_patterns = [
            r'discrete\s+analysis',
            r'www\.[\w\.]+\.com',  # URLs like www.discreteanalysisjournal.com
            r'^\s*[A-Z\s]{10,}\s*$',  # All caps author names
            r'^\s*\d+\s*$',  # Page numbers alone
            r'^\s*[A-Z][a-z]+\s+\d{4}',  # Month Year
        ]

        # Section heading patterns
        self.section_patterns = {
            'abstract': r'(?:abstract|tóm\s+tắt)',
            'introduction': r'(?:introduction|giới\s+thiệu)',
            'references': r'(?:references|tài\s+liệu\s+tham\s+khảo)',
            'theorem': r'(?:theorem|định\s+lý)\s+\d+',
            'lemma': r'(?:lemma|bổ\s+đề)\s+\d+',
            'proof': r'(?:proof|chứng\s+minh)',
        }

    def detect_repeating_content(self, pages_text: List[str]) -> List[ContentPattern]:
        """
        Detect content that repeats across multiple pages.

        Args:
            pages_text: List of text from each page

        Returns:
            List of ContentPattern objects for headers/footers
        """
        # Count line occurrences across pages
        line_counter = Counter()
        line_positions = {}

        for page_num, page_text in enumerate(pages_text):
            lines = page_text.split('\n')

            # Check first few lines (potential headers)
            for i, line in enumerate(lines[:5]):
                line = line.strip()
                if len(line) > 5:  # Ignore very short lines
                    line_counter[line] += 1
                    if line not in line_positions:
                        line_positions[line] = []
                    line_positions[line].append(page_num)

            # Check last few lines (potential footers)
            for i, line in enumerate(lines[-3:]):
                line = line.strip()
                if len(line) > 5:
                    line_counter[line] += 1
                    if line not in line_positions:
                        line_positions[line] = []
                    line_positions[line].append(page_num)

        # Identify patterns that repeat on many pages
        patterns = []
        min_occurrences = max(3, len(pages_text) // 2)  # Appear on at least half the pages

        for line, count in line_counter.most_common():
            if count >= min_occurrences:
                # Check if it matches header patterns
                is_header_pattern = any(re.search(pattern, line, re.IGNORECASE)
                                      for pattern in self.header_patterns)

                if is_header_pattern or count > len(pages_text) * 0.7:
                    patterns.append(ContentPattern(
                        text=line,
                        occurrences=count,
                        positions=line_positions[line],
                        is_header=True
                    ))

        return patterns

    def remove_repeating_patterns(self, text: str, patterns: List[ContentPattern]) -> str:
        """
        Remove identified header/footer patterns from text.

        Args:
            text: Full document text
            patterns: List of ContentPattern to remove

        Returns:
            Cleaned text
        """
        result = text

        for pattern in patterns:
            # Escape special regex characters in pattern text
            pattern_text = re.escape(pattern.text)
            # Remove the pattern (case-insensitive, preserve line structure)
            result = re.sub(f'^\\s*{pattern_text}\\s*$', '', result, flags=re.MULTILINE | re.IGNORECASE)

        # Clean up multiple blank lines
        result = re.sub(r'\n\n\n+', '\n\n', result)

        return result

    def merge_broken_paragraphs(self, text: str, formula_positions: Optional[List[Tuple[int, int]]] = None) -> str:
        """
        Merge lines that were broken by column layout.

        REGRESSION FIX (Phase 1.5):
        - Added formula boundary protection
        - Added section header detection
        - Increased merge threshold from 50 → 100 chars
        - Added equation number boundary protection
        - Checks for LaTeX delimiters

        Args:
            text: Document text to process
            formula_positions: List of (start, end) positions of formulas to protect

        Heuristics:
        - If line ends mid-sentence (no period) and next line starts lowercase → merge
        - If line is very short and next continues → merge
        - BUT: Don't merge across formula boundaries, section headers, or equation numbers
        """
        if formula_positions is None:
            formula_positions = []

        lines = text.split('\n')
        merged = []
        i = 0

        # Section header patterns (ALL CAPS or common section titles)
        section_header_patterns = [
            r'^(ABSTRACT|INTRODUCTION|RESULTS|DISCUSSION|CONCLUSION|REFERENCES|ACKNOWLEDGMENTS)$',
            r'^(TÓM TẮT|GIỚI THIỆU|KẾT QUẢ|THẢO LUẬN|KẾT LUẬN|TÀI LIỆU THAM KHẢO|CẢM ƠN)$',
            r'^\d+\.?\s+(Introduction|Methods|Results|Discussion|Conclusion|References)',
            r'^(Theorem|Lemma|Proposition|Corollary|Definition|Proof)\s+\d+',
        ]

        # LaTeX delimiters that indicate formula boundaries
        latex_delimiters = [r'\$', r'\\\[', r'\\\]', r'\\\(', r'\\\)',
                           r'\\begin\{', r'\\end\{']

        # Equation number patterns
        equation_number_pattern = r'\(\d+(?:\.\d+)?\)|\[\d+(?:\.\d+)?\]|Eq\.\s*\(\d+(?:\.\d+)?\)'

        # Calculate character positions for each line
        char_position = 0
        line_positions = []
        for line in lines:
            start = char_position
            end = char_position + len(line)
            line_positions.append((start, end))
            char_position = end + 1  # +1 for newline

        while i < len(lines):
            current = lines[i].strip()

            if not current:
                merged.append('')
                i += 1
                continue

            # Check if should merge with next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                should_merge = False

                # PROTECTION 1: Check if current or next line is a section header
                is_section_header = any(re.search(pattern, current, re.IGNORECASE)
                                       for pattern in section_header_patterns)
                next_is_section_header = any(re.search(pattern, next_line, re.IGNORECASE)
                                             for pattern in section_header_patterns)

                # PROTECTION 2: Check if lines contain LaTeX delimiters (formula boundaries)
                has_latex_delim = any(re.search(delim, current) for delim in latex_delimiters)
                next_has_latex_delim = any(re.search(delim, next_line) for delim in latex_delimiters)

                # PROTECTION 3: Check if lines contain equation numbers
                has_eq_number = re.search(equation_number_pattern, current)
                next_has_eq_number = re.search(equation_number_pattern, next_line)

                # PROTECTION 4: Check if merging would cross formula boundaries
                current_start, current_end = line_positions[i]
                next_start, next_end = line_positions[i + 1]

                crosses_formula = False
                for formula_start, formula_end in formula_positions:
                    # Check if there's a formula between current line end and next line start
                    if current_end < formula_start < next_start:
                        crosses_formula = True
                        break
                    # Check if current or next line overlaps with formula
                    if (current_start <= formula_start <= current_end or
                        current_start <= formula_end <= current_end or
                        next_start <= formula_start <= next_end or
                        next_start <= formula_end <= next_end):
                        crosses_formula = True
                        break

                # Don't merge if any protection condition is met
                if (is_section_header or next_is_section_header or
                    has_latex_delim or next_has_latex_delim or
                    has_eq_number or next_has_eq_number or
                    crosses_formula):
                    merged.append(current)
                    i += 1
                    continue

                # Standard merge conditions (with increased threshold)
                if next_line and not re.search(r'[.!?:]\s*$', current):
                    # Next line starts lowercase or is a continuation
                    # INCREASED THRESHOLD: 50 → 100 chars
                    if next_line[0].islower() or len(current) < 100:
                        should_merge = True

                if should_merge:
                    current = current + ' ' + next_line
                    i += 2  # Skip next line
                else:
                    i += 1
            else:
                i += 1

            merged.append(current)

        return '\n'.join(merged)

    def detect_document_structure(self, text: str) -> List[DocumentSection]:
        """
        Identify logical sections in the document.

        Returns:
            List of DocumentSection objects (Title, Abstract, Sections, References)
        """
        sections = []
        lines = text.split('\n')

        # Try to find title (usually first substantial text in ALL CAPS or large font)
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            if len(line) > 10 and line.isupper():
                sections.append(DocumentSection(
                    title='Title',
                    start_pos=0,
                    end_pos=len(line),
                    content=line,
                    section_type='title'
                ))
                break

        # Find sections by pattern matching
        for section_type, pattern in self.section_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                start = match.start()
                # Find section end (next section or end of document)
                end = len(text)
                for other_match in matches[matches.index(match) + 1:]:
                    end = other_match.start()
                    break

                sections.append(DocumentSection(
                    title=match.group(0),
                    start_pos=start,
                    end_pos=end,
                    content=text[start:end],
                    section_type=section_type
                ))

        # Sort by position
        sections.sort(key=lambda s: s.start_pos)
        return sections

    def clean_references(self, references_text: str) -> str:
        """
        Clean up the references section.

        - One reference per paragraph
        - Remove stray page numbers
        - Fix broken lines
        """
        # Remove single digits on their own lines (page numbers)
        cleaned = re.sub(r'^\s*\d{1,2}\s*$', '', references_text, flags=re.MULTILINE)

        # Merge broken references
        cleaned = self.merge_broken_paragraphs(cleaned)

        # Ensure each reference starts on new line if it starts with [1], [2], etc.
        cleaned = re.sub(r'(\[\d+\])', r'\n\1', cleaned)

        # Clean multiple blank lines
        cleaned = re.sub(r'\n\n\n+', '\n\n', cleaned)

        return cleaned.strip()

    def clean_document(self, text: str, pages_text: Optional[List[str]] = None,
                      formula_positions: Optional[List[Tuple[int, int]]] = None) -> str:
        """
        Complete document cleaning pipeline.

        REGRESSION FIX (Phase 1.5): Added formula_positions parameter to protect
        formula boundaries during paragraph merging.

        Args:
            text: Full document text
            pages_text: Optional list of per-page text for header detection
            formula_positions: Optional list of (start, end) positions of formulas

        Returns:
            Cleaned document text
        """
        result = text

        # 1. Detect and remove headers/footers
        if pages_text:
            patterns = self.detect_repeating_content(pages_text)
            result = self.remove_repeating_patterns(result, patterns)

        # 2. Fix paragraph breaks (WITH FORMULA PROTECTION)
        result = self.merge_broken_paragraphs(result, formula_positions)

        # 3. Detect sections
        sections = self.detect_document_structure(result)

        # 4. Clean references section specifically
        for section in sections:
            if section.section_type == 'references':
                cleaned_refs = self.clean_references(section.content)
                result = result.replace(section.content, cleaned_refs)

        # 5. Final cleanup
        result = re.sub(r'\n\n\n+', '\n\n', result)  # Remove excessive blank lines
        result = result.strip()

        return result
