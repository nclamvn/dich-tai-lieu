#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Math Formula Reconstructor
==========================
Preserves mathematical formulas during translation process.

PRIORITY: Translation quality (correctness) > Layout preservation

Author: AI Translator Pro Team
Version: 1.0.0
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class FormulaType(Enum):
    """Types of mathematical formulas"""
    INLINE = "inline"          # Within text: $x^2$
    DISPLAY = "display"        # Standalone: $$\sum_{i=1}^n$$
    NUMBERED = "numbered"      # With equation number: (1.1)


@dataclass
class MathSegment:
    """Represents a mathematical formula segment"""
    text: str
    formula_type: FormulaType
    start_pos: int
    end_pos: int
    equation_number: Optional[str] = None  # e.g., "(1.1)"
    latex_content: Optional[str] = None


class MathReconstructor:
    """
    Reconstructs and preserves mathematical formulas.

    Ensures:
    - Math structure is preserved (not flattened to text)
    - Special characters are normalized
    - Equation numbers are associated correctly
    """

    def __init__(self):
        # Common math symbol mappings for Unicode normalization
        # PHASE 1.5: Expanded from 18 → 60+ symbols for comprehensive coverage
        self.unicode_fixes = {
            # Name corrections (OCR corruption fixes)
            'Erd˝os': 'Erdős',  # Fix Erdős specifically (U+02DD → U+0151)
            'erd˝os': 'erdős',  # Lowercase version
            '˝o': 'ő',  # General double acute + o → ő
            '˝O': 'Ő',  # Uppercase version

            # Greek letters (lowercase)
            'α': 'α', 'β': 'β', 'γ': 'γ', 'δ': 'δ', 'ε': 'ε',
            'ζ': 'ζ', 'η': 'η', 'θ': 'θ', 'ι': 'ι', 'κ': 'κ',
            'λ': 'λ', 'μ': 'μ', 'ν': 'ν', 'ξ': 'ξ', 'ο': 'ο',
            'π': 'π', 'ρ': 'ρ', 'ς': 'ς', 'σ': 'σ', 'τ': 'τ',
            'υ': 'υ', 'φ': 'φ', 'χ': 'χ', 'ψ': 'ψ', 'ω': 'ω',

            # Greek letters (uppercase)
            'Α': 'Α', 'Β': 'Β', 'Γ': 'Γ', 'Δ': 'Δ', 'Ε': 'Ε',
            'Ζ': 'Ζ', 'Η': 'Η', 'Θ': 'Θ', 'Ι': 'Ι', 'Κ': 'Κ',
            'Λ': 'Λ', 'Μ': 'Μ', 'Ν': 'Ν', 'Ξ': 'Ξ', 'Ο': 'Ο',
            'Π': 'Π', 'Ρ': 'Ρ', 'Σ': 'Σ', 'Τ': 'Τ', 'Υ': 'Υ',
            'Φ': 'Φ', 'Χ': 'Χ', 'Ψ': 'Ψ', 'Ω': 'Ω',

            # Set theory symbols
            '∅': '∅',  # Empty set
            'ℕ': 'ℕ',  # Natural numbers
            'ℤ': 'ℤ',  # Integers
            'ℚ': 'ℚ',  # Rationals
            'ℝ': 'ℝ',  # Reals
            'ℂ': 'ℂ',  # Complex

            # Logic symbols
            '∀': '∀',  # For all
            '∃': '∃',  # Exists
            '¬': '¬',  # Not
            '∧': '∧',  # And
            '∨': '∨',  # Or

            # Comparison and relations
            '≤': '≤',  # Less than or equal
            '≥': '≥',  # Greater than or equal
            '≠': '≠',  # Not equal
            '≈': '≈',  # Approximately equal
            '≡': '≡',  # Equivalent
            '∼': '∼',  # Similar
            '≅': '≅',  # Congruent

            # Arrows
            '→': '→',  # Right arrow
            '←': '←',  # Left arrow
            '↔': '↔',  # Left-right arrow
            '⇒': '⇒',  # Right double arrow (implies)
            '⇐': '⇐',  # Left double arrow
            '⇔': '⇔',  # Left-right double arrow (iff)
            '↦': '↦',  # Maps to
            '⟶': '⟶',  # Long right arrow

            # Operators
            '∑': '∑',  # Sum
            '∫': '∫',  # Integral
            '∏': '∏',  # Product
            '∞': '∞',  # Infinity
            '∂': '∂',  # Partial derivative
            '∇': '∇',  # Nabla (gradient)
            '√': '√',  # Square root
            '∝': '∝',  # Proportional to
            '±': '±',  # Plus-minus
            '∓': '∓',  # Minus-plus
            '×': '×',  # Times
            '÷': '÷',  # Divide
            '·': '·',  # Middle dot

            # Set operations
            '∈': '∈',  # Element of
            '∉': '∉',  # Not element of
            '⊂': '⊂',  # Subset
            '⊃': '⊃',  # Superset
            '⊆': '⊆',  # Subset or equal
            '⊇': '⊇',  # Superset or equal
            '∪': '∪',  # Union
            '∩': '∩',  # Intersection
            '∖': '∖',  # Set minus

            # Special brackets and delimiters
            '⟨': '⟨',  # Left angle bracket
            '⟩': '⟩',  # Right angle bracket
            '⌈': '⌈',  # Left ceiling
            '⌉': '⌉',  # Right ceiling
            '⌊': '⌊',  # Left floor
            '⌋': '⌋',  # Right floor

            # Norm symbol
            '‖': '‖',  # Norm (double vertical bar)

            # Other mathematical symbols
            '∅': '∅',  # Empty set (duplicate check)
            '°': '°',  # Degree
            '′': '′',  # Prime
            '″': '″',  # Double prime
            '…': '…',  # Ellipsis
        }

        # Context-aware normalization patterns
        # PHASE 1.5: These patterns are applied AFTER simple replacements
        # to handle context-dependent transformations
        self.context_patterns = [
            # Double pipe to norm symbol (ONLY when surrounding a variable/expression)
            (re.compile(r'\|\|([^|]+)\|\|'), r'‖\1‖'),

            # Apostrophe to prime in math context (f'(x) → f′(x))
            # Only when apostrophe is between letter and parenthesis
            (re.compile(r"([a-zA-Z])'([₀₁₂₃₄₅₆₇₈₉]*)(\(|,|\s|$)"), r"\1′\2\3"),

            # Double apostrophe to double prime
            (re.compile(r"([a-zA-Z])''"), r"\1″"),

            # Three dots to ellipsis in math (within $...$)
            (re.compile(r'\$([^$]*)\.\.\.([^$]*)\$'), r'$\1…\2$'),
        ]

        # Patterns for detecting formulas
        # PHASE 1.5: Expanded to cover all LaTeX delimiters
        self.latex_inline_pattern = re.compile(r'\$([^\$]+)\$')
        self.latex_display_pattern = re.compile(r'\$\$([^\$]+)\$\$')

        # Additional LaTeX delimiters (PHASE 1.5)
        self.display_bracket_pattern = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)  # \[...\]
        self.inline_paren_pattern = re.compile(r'\\\((.+?)\\\)', re.DOTALL)     # \(...\)

        # LaTeX environments (PHASE 1.5)
        latex_environments = [
            'equation', 'equation*',
            'align', 'align*',
            'gather', 'gather*',
            'multline', 'multline*',
            'split',
            'cases',
            'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix',
            'array',
            'eqnarray', 'eqnarray*'
        ]
        env_names = '|'.join(latex_environments)
        self.latex_env_pattern = re.compile(
            rf'\\begin\{{({env_names})\*?}}(.+?)\\end\{{\1\*?}}',
            re.DOTALL | re.MULTILINE
        )

        # Expanded equation number patterns (PHASE 1.5)
        self.equation_number_patterns = [
            re.compile(r'\((\d+\.\d+)\)'),           # (1.1)
            re.compile(r'\((\d+)\)'),                 # (1)
            re.compile(r'Eq\.\s*\((\d+(?:\.\d+)?)\)'),  # Eq. (1.1)
            re.compile(r'\[(\d+\.\d+)\]'),            # [1.1]
        ]

        # Keep single pattern for backward compatibility
        self.equation_number_pattern = self.equation_number_patterns[0]

        # Math symbols that indicate formula content
        # PHASE 1.5: Updated to include new symbols
        self.math_indicators = r'[∑∫∏∪∩⊂⊃∈∉≤≥≠≈∞‖∂∇√∀∃→⇒±×·]|\\[a-z]+'

    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode characters to fix OCR/encoding issues.

        PHASE 1.5: Enhanced with context-aware patterns.

        WARNING: This method applies normalization GLOBALLY to entire text.
        For STEM translation, use normalize_unicode_scoped() to avoid
        corrupting Vietnamese prose.

        Examples:
            "Erd˝os" → "Erdős"
            "||x||" → "‖x‖"
            "f'(x)" → "f′(x)"

        Args:
            text: Input text with potential Unicode issues

        Returns:
            Normalized text with correct Unicode symbols
        """
        result = text

        # Step 1: Simple character replacements
        for wrong, correct in self.unicode_fixes.items():
            result = result.replace(wrong, correct)

        # Step 2: Context-aware pattern replacements
        # Applied AFTER simple replacements for safety
        for pattern, replacement in self.context_patterns:
            result = pattern.sub(replacement, result)

        return result

    def normalize_unicode_scoped(self, text: str, formula_segments) -> str:
        """
        Normalize Unicode ONLY within formula boundaries (REGRESSION FIX Phase 1.5).

        This prevents corruption of Vietnamese prose by scoping normalization
        to math content only.

        Args:
            text: Full document text
            formula_segments: List of FormulaMatch or MathSegment objects with formula positions

        Returns:
            Text with Unicode normalized ONLY in formulas

        Example:
            Input: "Định lý ||x|| ≤ 1 trong không gian"
            Formula at positions [8, 14]
            Output: "Định lý ‖x‖ ≤ 1 trong không gian"
                   (only formula content normalized, Vietnamese text untouched)
        """
        if not formula_segments:
            # No formulas, return text unchanged
            return text

        # Sort segments by position (handle both FormulaMatch and MathSegment)
        def get_start(seg):
            return seg.start if hasattr(seg, 'start') else seg.start_pos

        def get_end(seg):
            return seg.end if hasattr(seg, 'end') else seg.end_pos

        segments = sorted(formula_segments, key=get_start)

        # Build result by processing segments
        result_parts = []
        last_pos = 0

        for segment in segments:
            start = get_start(segment)
            end = get_end(segment)

            # Add non-formula text as-is
            if start > last_pos:
                result_parts.append(text[last_pos:start])

            # Normalize formula content only
            formula_text = text[start:end]
            normalized_formula = self.normalize_unicode(formula_text)
            result_parts.append(normalized_formula)

            last_pos = end

        # Add remaining non-formula text
        if last_pos < len(text):
            result_parts.append(text[last_pos:])

        return ''.join(result_parts)

    def detect_formulas(self, text: str) -> List[MathSegment]:
        """
        Detect all mathematical formulas in text.

        PHASE 1.5: Enhanced to detect all LaTeX delimiter types.

        Returns list of MathSegment objects with:
        - Formula type (inline, display, numbered)
        - Position in text
        - Associated equation number if any
        """
        segments = []

        # PHASE 1.5: Detect LaTeX environments FIRST (highest priority)
        # These are usually display equations: \begin{equation}...\end{equation}
        for match in self.latex_env_pattern.finditer(text):
            env_name = match.group(1)
            latex_content = match.group(2)
            segments.append(MathSegment(
                text=match.group(0),
                formula_type=FormulaType.DISPLAY,  # Environments are always display
                start_pos=match.start(),
                end_pos=match.end(),
                latex_content=latex_content
            ))

        # 1. Detect LaTeX display equations ($$...$$)
        for match in self.latex_display_pattern.finditer(text):
            # Skip if already part of environment
            if any(s.start_pos <= match.start() < s.end_pos for s in segments):
                continue

            latex_content = match.group(1)
            segments.append(MathSegment(
                text=match.group(0),
                formula_type=FormulaType.DISPLAY,
                start_pos=match.start(),
                end_pos=match.end(),
                latex_content=latex_content
            ))

        # PHASE 1.5: Detect \[...\] (display math)
        for match in self.display_bracket_pattern.finditer(text):
            # Skip if already covered
            if any(s.start_pos <= match.start() < s.end_pos for s in segments):
                continue

            latex_content = match.group(1)
            segments.append(MathSegment(
                text=match.group(0),
                formula_type=FormulaType.DISPLAY,
                start_pos=match.start(),
                end_pos=match.end(),
                latex_content=latex_content
            ))

        # 2. Detect LaTeX inline equations ($...$)
        for match in self.latex_inline_pattern.finditer(text):
            # Skip if already part of display equation or environment
            if any(s.start_pos <= match.start() < s.end_pos for s in segments):
                continue

            latex_content = match.group(1)
            segments.append(MathSegment(
                text=match.group(0),
                formula_type=FormulaType.INLINE,
                start_pos=match.start(),
                end_pos=match.end(),
                latex_content=latex_content
            ))

        # PHASE 1.5: Detect \(...\) (inline math)
        for match in self.inline_paren_pattern.finditer(text):
            # Skip if already covered
            if any(s.start_pos <= match.start() < s.end_pos for s in segments):
                continue

            latex_content = match.group(1)
            segments.append(MathSegment(
                text=match.group(0),
                formula_type=FormulaType.INLINE,
                start_pos=match.start(),
                end_pos=match.end(),
                latex_content=latex_content
            ))

        # 3. Detect equation numbers and associate with nearby formulas
        # PHASE 1.5: Use all equation number patterns, not just one
        for pattern in self.equation_number_patterns:
            for match in pattern.finditer(text):
                eq_num = match.group(1)
                pos = match.start()
                eq_text = match.group(0)  # Full match like "(1.1)" or "Eq. (1)"

                # PHASE 1.5: Improved association logic
                # Find display equation on same line (more reliable than proximity)
                line_start = text.rfind('\n', 0, pos) + 1
                line_end = text.find('\n', pos)
                if line_end == -1:
                    line_end = len(text)

                # Check if formula is on same line
                found = False
                for segment in segments:
                    if segment.formula_type == FormulaType.DISPLAY:
                        # Same line check OR close proximity check
                        on_same_line = (line_start <= segment.start_pos <= line_end)
                        very_close = abs(segment.end_pos - pos) < 50

                        if on_same_line or very_close:
                            segment.equation_number = eq_text
                            segment.formula_type = FormulaType.NUMBERED
                            found = True
                            break

                # If not found on same line, try proximity fallback
                if not found:
                    for segment in segments:
                        if segment.formula_type == FormulaType.DISPLAY:
                            if abs(segment.end_pos - pos) < 100:
                                segment.equation_number = eq_text
                                segment.formula_type = FormulaType.NUMBERED
                                break

        # Sort by position
        segments.sort(key=lambda s: s.start_pos)
        return segments

    def extract_equation_numbers(self, text: str) -> Dict[str, int]:
        """
        Extract all equation numbers and their positions.

        Returns: {"(1.1)": 234, "(2.3)": 1456, ...}
        """
        numbers = {}
        for match in self.equation_number_pattern.finditer(text):
            numbers[match.group(0)] = match.start()
        return numbers

    def replace_with_placeholders(self, text: str, segments: List[MathSegment]) -> Tuple[str, Dict[str, MathSegment]]:
        """
        Replace math formulas with placeholders for safe translation.

        Returns:
            - Text with placeholders: "The formula MATH_TOKEN_001 shows..."
            - Mapping: {"MATH_TOKEN_001": MathSegment(...)}
        """
        result = text
        mapping = {}

        # Process in reverse order to maintain positions
        for i, segment in enumerate(reversed(segments)):
            token = f"MATH_TOKEN_{len(segments) - i:03d}"
            mapping[token] = segment

            # Replace formula with token
            result = result[:segment.start_pos] + token + result[segment.end_pos:]

        return result, mapping

    def restore_formulas(self, text: str, mapping: Dict[str, MathSegment]) -> str:
        """
        Restore math formulas from placeholders after translation.

        Input: "Công thức MATH_TOKEN_001 cho thấy..."
        Output: "Công thức $x^2 + y^2 = z^2$ cho thấy..."
        """
        result = text

        for token, segment in mapping.items():
            # Restore original formula (DO NOT TRANSLATE MATH)
            result = result.replace(token, segment.text)

        return result

    def format_for_docx(self, segment: MathSegment) -> Dict[str, any]:
        """
        Format math segment for DOCX export.

        Returns formatting hints:
        - is_equation: bool
        - is_display: bool
        - equation_number: str or None
        - latex: str
        """
        return {
            'is_equation': True,
            'is_display': segment.formula_type in [FormulaType.DISPLAY, FormulaType.NUMBERED],
            'equation_number': segment.equation_number,
            'latex': segment.latex_content or segment.text,
            'type': segment.formula_type.value
        }

    def has_math_content(self, text: str) -> bool:
        """Quick check if text contains mathematical content"""
        return bool(re.search(self.math_indicators, text)) or \
               bool(self.latex_inline_pattern.search(text)) or \
               bool(self.latex_display_pattern.search(text))

    def detect_quality_issues(self, text: str) -> Dict[str, List[str]]:
        """
        Detect potential formula quality issues.

        PHASE 1.5: Proactive quality monitoring to catch formula degradation.

        Returns dictionary with:
            'flattened': Formulas that lost structure
            'spacing': Spacing issues in formulas
            'missing_symbols': Symbols that should be normalized

        Example:
            >>> reconstructor.detect_quality_issues("x ^ 2 + ||x||")
            {
                'flattened': ["Possible flattened exponent: 'x ^ 2'"],
                'spacing': [],
                'missing_symbols': ["Double pipes found (||), should use norm symbol ‖"]
            }
        """
        issues = {
            'flattened': [],
            'spacing': [],
            'missing_symbols': []
        }

        # Detect flattened formulas
        # Pattern 1: Spaces around exponent operator (x ^ 2 instead of x^2)
        if re.search(r'[a-zA-Z]\s+\^\s+\d+', text):
            matches = re.findall(r'([a-zA-Z]\s+\^\s+\d+)', text)
            for match in matches[:3]:  # Limit to first 3 examples
                issues['flattened'].append(f"Malformed exponent: '{match}' (spaces around ^)")

        # Pattern 2: Spaces between variable and number (x 2 instead of x²)
        if re.search(r'[a-zA-Z]\s+\d+\s+[a-zA-Z]', text):
            matches = re.findall(r'([a-zA-Z]\s+\d+\s+[a-zA-Z])', text)
            for match in matches[:3]:
                issues['flattened'].append(f"Possible flattened superscript: '{match}'")

        # Pattern 3: Function with weird spacing (sin ( x ) instead of sin(x))
        if re.search(r'\b(sin|cos|tan|log|ln|exp)\s+\(', text):
            matches = re.findall(r'(\b(?:sin|cos|tan|log|ln|exp)\s+\()', text)
            for match in matches[:3]:
                issues['spacing'].append(f"Extra space in function: '{match}'")

        # Spacing issues in inline formulas
        # Pattern: $ ... $ with extra spaces
        if re.search(r'\$\s+[^$]+\s+\$', text):
            count = len(re.findall(r'\$\s+[^$]+\s+\$', text))
            issues['spacing'].append(f"Found {count} inline formulas with extra spaces inside delimiters")

        # Missing norm symbols (double pipes not converted)
        if '||' in text and '‖' not in text:
            count = text.count('||')
            issues['missing_symbols'].append(f"Found {count} double pipes (||), should use norm symbol ‖")

        # Check for plain ASCII arrows instead of Unicode
        plain_arrows = []
        if '->' in text and '→' not in text:
            plain_arrows.append("'->' should be '→'")
        if '=>' in text and '⇒' not in text:
            plain_arrows.append("'=>' should be '⇒'")
        if '<=' in text and '⇐' not in text and '≤' not in text:
            # Could be either "implies" or "less than or equal"
            plain_arrows.append("'<=' might need Unicode (⇐ or ≤)")

        if plain_arrows:
            issues['missing_symbols'].extend(plain_arrows)

        # Check for missing Greek letters (written as words)
        greek_words = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu', 'sigma', 'omega']
        for word in greek_words:
            # Match whole word, case-insensitive, but not in LaTeX commands
            pattern = r'(?<![\\])\b' + word + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Check if it's likely a math context (near formulas or symbols)
                context = re.findall(r'.{0,20}\b' + word + r'\b.{0,20}', text, re.IGNORECASE)
                for ctx in context[:2]:
                    if any(sym in ctx for sym in ['=', '+', '-', '*', '/', '$', '^']):
                        issues['missing_symbols'].append(f"Greek letter as word: '{word}' in context '{ctx.strip()}'")
                        break

        return issues
