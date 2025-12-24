r"""
Formula Detection Module

Detects and extracts mathematical formulas from text, including:
- Inline math: $...$, \(...\)
- Display math: $$...$$, \[...\]
- LaTeX environments: \begin{equation}, \begin{align}, etc.
- Unicode math symbols
"""

import re
import regex
from dataclasses import dataclass
from typing import List, Tuple, Pattern
from enum import Enum


class FormulaType(Enum):
    """Types of mathematical formulas and chemical formulas"""
    INLINE_DOLLAR = "inline_dollar"  # $...$
    INLINE_PAREN = "inline_paren"    # \(...\)
    DISPLAY_DOLLAR = "display_dollar"  # $$...$$
    DISPLAY_BRACKET = "display_bracket"  # \[...\]
    LATEX_ENV = "latex_env"  # \begin{equation}...\end{equation}
    UNICODE_MATH = "unicode_math"  # ∫, ∑, √, etc.
    CHEMICAL = "chemical"  # Chemical formulas (SMILES-like patterns)


@dataclass
class FormulaMatch:
    """Represents a detected formula"""
    content: str
    start: int
    end: int
    formula_type: FormulaType
    environment_name: str = None  # For LaTeX environments

    def __repr__(self) -> str:
        type_str = self.formula_type.value
        if self.environment_name:
            type_str += f"[{self.environment_name}]"
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"FormulaMatch(type={type_str}, pos={self.start}-{self.end}, content='{preview}')"


class FormulaDetector:
    """Detects mathematical formulas in text"""

    # LaTeX environments that should be preserved
    LATEX_ENVIRONMENTS = [
        'equation', 'equation*',
        'align', 'align*',
        'gather', 'gather*',
        'multline', 'multline*',
        'split',
        'eqnarray', 'eqnarray*',
        'array',
        'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix',
        'cases',
        'alignat', 'alignat*',
        'flalign', 'flalign*',
    ]

    # Unicode math symbols
    UNICODE_MATH_PATTERN = r'[∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟⋠⋡⋢⋣⋤⋥⋦⋧⋨⋩⋪⋫⋬⋭⋮⋯⋰⋱⋲⋳⋴⋵⋶⋷⋸⋹⋺⋻⋼⋽⋾⋿]+'

    def __init__(self):
        """Initialize the formula detector"""
        # Compile patterns for better performance
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for formula detection"""

        # Display math: $$...$$ (must check before inline $...$)
        # PHASE 1.7: Fixed regex to handle very long formulas (>3000 chars)
        # Old pattern had backtracking issues: r'\$\$(?:[^$]|\$(?!\$))+?\$\$'
        # New pattern uses negative lookahead without alternation
        self.display_dollar_pattern = regex.compile(
            r'\$\$(?:(?!\$\$).)+\$\$',
            regex.DOTALL | regex.MULTILINE
        )

        # Inline math: $...$ (not $$)
        self.inline_dollar_pattern = regex.compile(
            r'(?<!\$)\$(?!\$)(?:[^$\n])+?\$(?!\$)',
            regex.MULTILINE
        )

        # Display math: \[...\]
        self.display_bracket_pattern = regex.compile(
            r'\\\[.*?\\\]',
            regex.DOTALL | regex.MULTILINE
        )

        # Inline math: \(...\)
        self.inline_paren_pattern = regex.compile(
            r'\\\(.*?\\\)',
            regex.DOTALL | regex.MULTILINE
        )

        # LaTeX environments
        env_names = '|'.join(self.LATEX_ENVIRONMENTS)
        self.latex_env_pattern = regex.compile(
            rf'\\begin\{{({env_names})\*?}}.*?\\end\{{\1\*?}}',
            regex.DOTALL | regex.MULTILINE
        )

        # Unicode math symbols (consecutive sequences)
        self.unicode_math_pattern = regex.compile(self.UNICODE_MATH_PATTERN)

        # Chemical formulas (SMILES-like patterns)
        # Conservative pattern: tokens with only chemical elements, digits, (), =, #
        # Examples: CH3CH2OH, C(CO)N, CC(C)O, H2SO4
        self.chemical_formula_pattern = regex.compile(
            r'\b[A-Z][a-z]?(?:[a-z]?[0-9]*[A-Z]?[a-z]?[0-9]*[\(\)\[\]=\#\-\+]*){2,}\b',
            regex.MULTILINE
        )

    def detect_formulas(self, text: str, include_chemical: bool = True) -> List[FormulaMatch]:
        """
        Detect all types of formulas in text (math + chemical)

        Args:
            text: Input text to scan for formulas
            include_chemical: Include chemical formula detection (default True)

        Returns:
            List of FormulaMatch objects, sorted by position
        """
        matches = []

        # Detect LaTeX environments first (highest priority)
        matches.extend(self._detect_latex_environments(text))

        # Detect display math
        matches.extend(self._detect_display_math(text))

        # Detect inline math
        matches.extend(self._detect_inline_math(text))

        # Detect Unicode math symbols
        matches.extend(self._detect_unicode_math(text))

        # Detect chemical formulas (if enabled)
        if include_chemical:
            matches.extend(self._detect_chemical_formulas(text))

        # Remove overlapping matches (keep the first/longest one)
        matches = self._remove_overlaps(matches)

        # Sort by position
        matches.sort(key=lambda m: m.start)

        return matches

    def _detect_latex_environments(self, text: str) -> List[FormulaMatch]:
        r"""Detect LaTeX environments like \begin{equation}...\end{equation}"""
        matches = []

        for match in self.latex_env_pattern.finditer(text):
            env_name = match.group(1)
            matches.append(FormulaMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                formula_type=FormulaType.LATEX_ENV,
                environment_name=env_name
            ))

        return matches

    def _detect_display_math(self, text: str) -> List[FormulaMatch]:
        r"""Detect display math: $$...$$ and \[...\]"""
        matches = []

        # Detect $$...$$
        for match in self.display_dollar_pattern.finditer(text):
            matches.append(FormulaMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                formula_type=FormulaType.DISPLAY_DOLLAR
            ))

        # Detect \[...\]
        for match in self.display_bracket_pattern.finditer(text):
            matches.append(FormulaMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                formula_type=FormulaType.DISPLAY_BRACKET
            ))

        return matches

    def _detect_inline_math(self, text: str) -> List[FormulaMatch]:
        r"""Detect inline math: $...$ and \(...\)"""
        matches = []

        # Detect $...$ (but not $$)
        for match in self.inline_dollar_pattern.finditer(text):
            matches.append(FormulaMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                formula_type=FormulaType.INLINE_DOLLAR
            ))

        # Detect \(...\)
        for match in self.inline_paren_pattern.finditer(text):
            matches.append(FormulaMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                formula_type=FormulaType.INLINE_PAREN
            ))

        return matches

    def _detect_unicode_math(self, text: str) -> List[FormulaMatch]:
        """Detect Unicode math symbols"""
        matches = []

        for match in self.unicode_math_pattern.finditer(text):
            # Only include if it's a significant sequence (3+ symbols)
            if len(match.group(0)) >= 3:
                matches.append(FormulaMatch(
                    content=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    formula_type=FormulaType.UNICODE_MATH
                ))

        return matches

    def _detect_chemical_formulas(self, text: str) -> List[FormulaMatch]:
        """
        Detect chemical formulas (SMILES-like patterns)

        Conservative detection of chemical formulas like:
        - CH3CH2OH (ethanol)
        - H2SO4 (sulfuric acid)
        - C(CO)N (simple SMILES)
        - C6H12O6 (glucose)

        Uses heuristics to avoid false positives:
        - Must have multiple capital letters or chemical-looking structure
        - Must contain numbers or chemical symbols like (), [], =, #
        - Avoids matching normal English words
        """
        matches = []

        for match in self.chemical_formula_pattern.finditer(text):
            formula = match.group(0)

            # Apply heuristics to reduce false positives
            if self._looks_like_chemical_formula(formula):
                matches.append(FormulaMatch(
                    content=formula,
                    start=match.start(),
                    end=match.end(),
                    formula_type=FormulaType.CHEMICAL
                ))

        return matches

    def _looks_like_chemical_formula(self, text: str) -> bool:
        """
        Heuristic to determine if text looks like a chemical formula

        Args:
            text: Potential chemical formula

        Returns:
            True if it looks like a chemical formula
        """
        # Must have at least one digit (e.g., H2O, CH4)
        has_digit = any(c.isdigit() for c in text)

        # Or must have chemical symbols like (), [], =, #
        has_chem_symbols = any(c in text for c in ['(', ')', '[', ']', '=', '#', '-', '+'])

        # Must have at least 2 capital letters (element symbols)
        capital_count = sum(1 for c in text if c.isupper())

        # Chemical formula criteria
        if has_digit or has_chem_symbols:
            if capital_count >= 2:
                # Avoid common English words that match pattern
                # (e.g., "Chemistry", "CHemical")
                common_words = {'Chemistry', 'Chemical', 'CHemical', 'CHange'}
                if text not in common_words:
                    return True

        return False

    def _remove_overlaps(self, matches: List[FormulaMatch]) -> List[FormulaMatch]:
        """Remove overlapping matches, keeping the first/longest one"""
        if not matches:
            return []

        # Sort by start position, then by length (descending)
        matches.sort(key=lambda m: (m.start, -(m.end - m.start)))

        non_overlapping = []
        for match in matches:
            # Check if this match overlaps with any already accepted match
            overlaps = False
            for accepted in non_overlapping:
                if (match.start < accepted.end and match.end > accepted.start):
                    overlaps = True
                    break

            if not overlaps:
                non_overlapping.append(match)

        return non_overlapping

    def has_formulas(self, text: str) -> bool:
        """
        Quick check if text contains any formulas

        Args:
            text: Text to check

        Returns:
            True if formulas are detected
        """
        # Quick regex checks without full parsing
        if self.display_dollar_pattern.search(text):
            return True
        if self.inline_dollar_pattern.search(text):
            return True
        if self.display_bracket_pattern.search(text):
            return True
        if self.inline_paren_pattern.search(text):
            return True
        if self.latex_env_pattern.search(text):
            return True
        if self.unicode_math_pattern.search(text):
            return True

        return False

    def count_formulas(self, text: str) -> dict:
        """
        Count formulas by type

        Args:
            text: Text to analyze

        Returns:
            Dictionary with counts per formula type
        """
        matches = self.detect_formulas(text)

        counts = {ftype: 0 for ftype in FormulaType}
        for match in matches:
            counts[match.formula_type] += 1

        return {
            'total': len(matches),
            'by_type': {k.value: v for k, v in counts.items() if v > 0}
        }
