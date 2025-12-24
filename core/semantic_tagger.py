#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semantic Tagger - Phase 2.0.5
Detect and classify academic structures: theorems, proofs, equations, headings
"""

import re
from typing import Optional, Tuple, List
from enum import Enum


class BlockType(Enum):
    """Types of academic text blocks"""
    THEOREM = "theorem"
    LEMMA = "lemma"
    COROLLARY = "corollary"
    PROPOSITION = "proposition"
    DEFINITION = "definition"
    EXAMPLE = "example"
    PROOF = "proof"
    EQUATION = "equation"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BODY = "body"
    QED = "qed"


class SemanticTagger:
    """Detect and classify academic structures in text"""

    # ========== THEOREM PATTERNS ==========

    # English patterns
    THEOREM_PATTERNS_EN = [
        r'^Theorem\s+\d+\.?\d*',
        r'^Lemma\s+\d+\.?\d*',
        r'^Corollary\s+\d+\.?\d*',
        r'^Proposition\s+\d+\.?\d*',
        r'^Definition\s+\d+\.?\d*',
        r'^Example\s+\d+\.?\d*',
    ]

    # Vietnamese patterns
    THEOREM_PATTERNS_VI = [
        r'^Định lý\s+\d+\.?\d*',
        r'^Bổ đề\s+\d+\.?\d*',
        r'^Hệ quả\s+\d+\.?\d*',
        r'^Mệnh đề\s+\d+\.?\d*',
        r'^Định nghĩa\s+\d+\.?\d*',
        r'^Ví dụ\s+\d+\.?\d*',
    ]

    # Mapping theorem keywords to types
    THEOREM_TYPE_MAP = {
        'theorem': BlockType.THEOREM,
        'định lý': BlockType.THEOREM,
        'lemma': BlockType.LEMMA,
        'bổ đề': BlockType.LEMMA,
        'corollary': BlockType.COROLLARY,
        'hệ quả': BlockType.COROLLARY,
        'proposition': BlockType.PROPOSITION,
        'mệnh đề': BlockType.PROPOSITION,
        'definition': BlockType.DEFINITION,
        'định nghĩa': BlockType.DEFINITION,
        'example': BlockType.EXAMPLE,
        'ví dụ': BlockType.EXAMPLE,
    }

    # ========== PROOF PATTERNS ==========

    PROOF_PATTERNS_EN = [
        r'^Proof\.',
        r'^Proof of Theorem',
        r'^Proof of Lemma',
        r'^Proof of Corollary',
        r'^Proof:',
    ]

    PROOF_PATTERNS_VI = [
        r'^Chứng minh\.',
        r'^Chứng minh Định lý',
        r'^Chứng minh Bổ đề',
        r'^Chứng minh Hệ quả',
        r'^Chứng minh:',
    ]

    # ========== QED PATTERNS ==========

    QED_PATTERNS = [
        r'\s*□\s*$',           # Hollow square
        r'\s*■\s*$',           # Filled square
        r'\s*∎\s*$',           # End of proof symbol
        r'\s*Q\.?E\.?D\.?\s*$',  # QED
        r'\s*\(Đpcm\)\s*$',    # Vietnamese abbreviation
    ]

    # ========== EQUATION PATTERNS ==========

    # Math symbols indicating equations
    MATH_SYMBOLS = {
        '∑', '∫', '∏', '∂', '∇', '∆',  # Operators
        '∈', '∉', '⊂', '⊃', '⊆', '⊇',  # Set theory
        '∀', '∃', '∄',                  # Quantifiers
        '≤', '≥', '≠', '≈', '≡',        # Relations
        '→', '←', '⇒', '⇐', '↔', '⇔',  # Arrows
        '∧', '∨', '¬',                  # Logic
        '∞', '∅', 'ℕ', 'ℤ', 'ℚ', 'ℝ', 'ℂ',  # Special
        '±', '∓', '×', '÷',             # Arithmetic
        '∪', '∩', '⊕', '⊗',             # Operations
        '⟨', '⟩', '⟦', '⟧',             # Brackets
    }

    # LaTeX delimiter patterns
    LATEX_DELIMITERS = [
        r'\$\$',      # Display math
        r'\$',        # Inline math
        r'\\\[',      # Display math
        r'\\\]',      # Display math
        r'\\\(',      # Inline math
        r'\\\)',      # Inline math
    ]

    # ========== HEADING PATTERNS ==========

    # Section numbering patterns (1. Introduction, 1.1 Background, etc.)
    HEADING_PATTERNS = [
        r'^\d+\.\s+[A-Z]',          # 1. Introduction
        r'^\d+\.\d+\s+[A-Z]',       # 1.1 Background
        r'^\d+\.\d+\.\d+\s+[A-Z]',  # 1.1.1 Details
    ]

    # Vietnamese heading patterns
    HEADING_PATTERNS_VI = [
        r'^Chương\s+\d+',           # Chapter
        r'^Phần\s+\d+',             # Section
        r'^Mục\s+\d+',              # Subsection
    ]

    def __init__(self):
        """Initialize semantic tagger"""
        # Compile regex patterns for performance
        self.theorem_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (self.THEOREM_PATTERNS_EN + self.THEOREM_PATTERNS_VI)
        ]
        self.proof_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (self.PROOF_PATTERNS_EN + self.PROOF_PATTERNS_VI)
        ]
        self.qed_patterns = [
            re.compile(p)
            for p in self.QED_PATTERNS
        ]
        self.heading_patterns = [
            re.compile(p)
            for p in (self.HEADING_PATTERNS + self.HEADING_PATTERNS_VI)
        ]

    def detect_block_type(self, text: str) -> BlockType:
        """
        Detect the type of academic block from text

        Args:
            text: Text to analyze (typically first 200 chars of paragraph)

        Returns:
            BlockType enum
        """
        text_clean = text.strip()
        if not text_clean:
            return BlockType.BODY

        # Check QED marker (end of proof)
        if self.is_qed_marker(text_clean):
            return BlockType.QED

        # Check theorem-like structures
        theorem_type = self.detect_theorem_type(text_clean)
        if theorem_type:
            return theorem_type

        # Check proof
        if self.is_proof_start(text_clean):
            return BlockType.PROOF

        # Check headings
        heading_level = self.detect_heading_level(text_clean)
        if heading_level:
            return heading_level

        # Check equation
        if self.is_equation_block(text_clean):
            return BlockType.EQUATION

        # Default to body text
        return BlockType.BODY

    def detect_theorem_type(self, text: str) -> Optional[BlockType]:
        """
        Detect if text starts with a theorem-like structure

        Returns:
            BlockType.THEOREM/LEMMA/etc or None
        """
        for pattern in self.theorem_patterns:
            if pattern.search(text):
                # Extract keyword to determine type
                keyword = self._extract_theorem_keyword(text)
                if keyword:
                    return self.THEOREM_TYPE_MAP.get(keyword.lower(), BlockType.THEOREM)
                return BlockType.THEOREM
        return None

    def _extract_theorem_keyword(self, text: str) -> Optional[str]:
        """Extract the theorem keyword (Theorem, Lemma, etc.)"""
        words = text.split()
        if words:
            first_word = words[0].lower()
            for keyword in self.THEOREM_TYPE_MAP.keys():
                if first_word == keyword.lower() or first_word.startswith(keyword.lower()):
                    return keyword
        return None

    def is_proof_start(self, text: str) -> bool:
        """Check if text starts a proof block"""
        for pattern in self.proof_patterns:
            if pattern.search(text):
                return True
        return False

    def is_qed_marker(self, text: str) -> bool:
        """Check if text is a QED marker (end of proof)"""
        for pattern in self.qed_patterns:
            if pattern.search(text):
                return True
        return False

    def detect_heading_level(self, text: str) -> Optional[BlockType]:
        """
        Detect heading level (H1, H2, H3) from section numbering

        Returns:
            BlockType.HEADING_1/2/3 or None
        """
        for pattern in self.heading_patterns:
            match = pattern.search(text)
            if match:
                # Count dots to determine level
                numbering = match.group(0)
                dot_count = numbering.count('.')

                if dot_count == 1:  # 1. Introduction
                    return BlockType.HEADING_1
                elif dot_count == 2:  # 1.1 Background
                    return BlockType.HEADING_2
                elif dot_count == 3:  # 1.1.1 Details
                    return BlockType.HEADING_3

        # Check Vietnamese patterns
        if text.startswith('Chương'):
            return BlockType.HEADING_1
        elif text.startswith('Phần'):
            return BlockType.HEADING_2
        elif text.startswith('Mục'):
            return BlockType.HEADING_3

        return None

    def is_equation_block(self, text: str, threshold: float = 0.20) -> bool:
        """
        Check if text is an equation block

        Args:
            text: Text to check
            threshold: Minimum ratio of math symbols (default 20%)

        Returns:
            bool: True if equation block
        """
        if not text or len(text) < 3:
            return False

        # Count math symbols
        math_count = sum(1 for char in text if char in self.MATH_SYMBOLS)
        ratio = math_count / len(text)

        # Check for LaTeX delimiters
        has_latex = any(delimiter in text for delimiter in ['$$', '\\[', '\\]', '\\(', '\\)'])

        # Heuristic: >20% math symbols OR has LaTeX delimiters
        return ratio >= threshold or has_latex

    def extract_equation_number(self, text: str) -> Optional[str]:
        """
        Extract equation number from text like '(1.1)' or '(2)'

        Returns:
            Equation number string or None
        """
        pattern = r'\((\d+\.?\d*)\)\s*$'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def should_add_qed(self, text: str) -> bool:
        """
        Check if QED symbol should be added at end of proof

        Returns:
            bool: True if no QED marker exists
        """
        return not self.is_qed_marker(text)

    def get_theorem_title(self, text: str) -> Tuple[str, str]:
        """
        Extract theorem title and body

        Args:
            text: Full theorem text

        Returns:
            Tuple of (title, body)
            e.g., ("Theorem 1.1 (Main Result)", "For all n...")
        """
        # Find first period or newline to separate title from body
        lines = text.split('\n', 1)

        if len(lines) == 1:
            # Single line, try to split by period
            parts = text.split('.', 1)
            if len(parts) == 2:
                return (parts[0].strip() + '.', parts[1].strip())
            return (text.strip(), '')

        # Multi-line: first line is title, rest is body
        return (lines[0].strip(), lines[1].strip() if len(lines) > 1 else '')


class EquationNumbering:
    """Handle equation numbering (1.1), (1.2), etc."""

    def __init__(self):
        self.section_number = 1
        self.equation_counter = 0
        self.numbered_equations = {}  # Map equation_id -> number

    def set_section(self, section_num: int):
        """Set current section number and reset equation counter"""
        self.section_number = section_num
        self.equation_counter = 0

    def get_next_number(self) -> str:
        """
        Get next equation number

        Returns:
            String like "1.1", "1.2", etc.
        """
        self.equation_counter += 1
        return f"{self.section_number}.{self.equation_counter}"

    def format_number(self, number: str) -> str:
        """Format equation number with parentheses"""
        return f"({number})"
