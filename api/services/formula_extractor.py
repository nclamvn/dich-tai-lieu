"""
Standalone Formula Extractor.

Detects and extracts mathematical formulas from text using ``re`` only
(no ``regex`` dependency).  Supports:

1. INLINE:  $...$  and  \\(...\\)
2. DISPLAY: $$...$$ and \\[...\\]
3. LATEX ENVIRONMENTS: \\begin{equation}...\\end{equation}
4. UNICODE MATH: sequences of math symbols (∑, ∫, √, etc.)

Lighter than core/stem/formula_detector.py (which uses ``regex``).
Designed for LayoutDNA analysis — not for academic paper processing.

Standalone module — no extraction or translation imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from config.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class FormulaMode(str, Enum):
    """Display mode of a formula."""
    INLINE = "inline"
    DISPLAY = "display"


class FormulaKind(str, Enum):
    """Source notation of the formula."""
    DOLLAR_INLINE = "dollar_inline"       # $...$
    DOLLAR_DISPLAY = "dollar_display"     # $$...$$
    PAREN_INLINE = "paren_inline"         # \(...\)
    BRACKET_DISPLAY = "bracket_display"   # \[...\]
    LATEX_ENV = "latex_env"               # \begin{...}...\end{...}
    UNICODE = "unicode"                   # ∑∫√ sequences


@dataclass
class ExtractedFormula:
    """One formula found in text."""

    content: str
    start: int
    end: int
    mode: FormulaMode
    kind: FormulaKind
    env_name: Optional[str] = None  # For LATEX_ENV

    @property
    def inner(self) -> str:
        """Formula content without delimiters."""
        if self.kind == FormulaKind.DOLLAR_DISPLAY:
            return self.content[2:-2].strip()
        if self.kind == FormulaKind.DOLLAR_INLINE:
            return self.content[1:-1].strip()
        if self.kind == FormulaKind.PAREN_INLINE:
            return self.content[2:-2].strip()
        if self.kind == FormulaKind.BRACKET_DISPLAY:
            return self.content[2:-2].strip()
        if self.kind == FormulaKind.LATEX_ENV and self.env_name:
            prefix = f"\\begin{{{self.env_name}}}"
            suffix = f"\\end{{{self.env_name}}}"
            inner = self.content
            if inner.startswith(prefix):
                inner = inner[len(prefix):]
            if inner.endswith(suffix):
                inner = inner[:-len(suffix)]
            return inner.strip()
        return self.content

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "inner": self.inner,
            "start": self.start,
            "end": self.end,
            "mode": self.mode.value,
            "kind": self.kind.value,
            "env_name": self.env_name,
        }


# ---------------------------------------------------------------------------
# Compiled patterns (module level for reuse)
# ---------------------------------------------------------------------------

# Display math: $$...$$ — must come before inline
_DISPLAY_DOLLAR = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)

# Inline math: $...$ — single line, not preceded/followed by $
_INLINE_DOLLAR = re.compile(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)')

# Display math: \[...\]
_DISPLAY_BRACKET = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)

# Inline math: \(...\)
_INLINE_PAREN = re.compile(r'\\\((.+?)\\\)', re.DOTALL)

# LaTeX environments
_LATEX_ENVS = [
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

_ENV_NAMES = '|'.join(re.escape(e) for e in _LATEX_ENVS)
_LATEX_ENV_RE = re.compile(
    rf'\\begin\{{({_ENV_NAMES})\}}(.*?)\\end\{{\1\}}',
    re.DOTALL,
)

# Unicode math symbols (3+ consecutive)
_UNICODE_MATH = re.compile(
    r'['
    r'\u2200-\u22FF'   # Mathematical Operators
    r'\u2A00-\u2AFF'   # Supplemental Mathematical Operators
    r'\u27C0-\u27EF'   # Miscellaneous Mathematical Symbols-A
    r'\u2980-\u29FF'   # Miscellaneous Mathematical Symbols-B
    r'∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑√∛∜∝∞'
    r']{3,}'
)


# ---------------------------------------------------------------------------
# FormulaExtractor
# ---------------------------------------------------------------------------

class FormulaExtractor:
    """Extract formulas from text.

    Usage::

        extractor = FormulaExtractor()
        formulas = extractor.extract("Given $x^2 + y^2 = r^2$ we have...")
        for f in formulas:
            print(f.mode, f.inner)
    """

    def extract(self, text: str) -> List[ExtractedFormula]:
        """Find all formulas in text.

        Detection priority: LaTeX env > display $$ > display \\[
        > inline $ > inline \\( > unicode.
        Non-overlapping: first detection wins.
        """
        if not text:
            return []

        formulas: List[ExtractedFormula] = []

        # 1. LaTeX environments (highest priority)
        for m in _LATEX_ENV_RE.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.DISPLAY,
                kind=FormulaKind.LATEX_ENV,
                env_name=m.group(1),
            ))

        # 2. Display $$...$$
        for m in _DISPLAY_DOLLAR.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.DISPLAY,
                kind=FormulaKind.DOLLAR_DISPLAY,
            ))

        # 3. Display \[...\]
        for m in _DISPLAY_BRACKET.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.DISPLAY,
                kind=FormulaKind.BRACKET_DISPLAY,
            ))

        # 4. Inline $...$
        for m in _INLINE_DOLLAR.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.INLINE,
                kind=FormulaKind.DOLLAR_INLINE,
            ))

        # 5. Inline \(...\)
        for m in _INLINE_PAREN.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.INLINE,
                kind=FormulaKind.PAREN_INLINE,
            ))

        # 6. Unicode math sequences
        for m in _UNICODE_MATH.finditer(text):
            formulas.append(ExtractedFormula(
                content=m.group(0),
                start=m.start(),
                end=m.end(),
                mode=FormulaMode.INLINE,
                kind=FormulaKind.UNICODE,
            ))

        # Remove overlaps
        formulas = self._remove_overlaps(formulas)

        # Sort by position
        formulas.sort(key=lambda f: f.start)

        logger.info(
            "FormulaExtractor: found %d formulas in %d chars",
            len(formulas), len(text),
        )

        return formulas

    def has_formulas(self, text: str) -> bool:
        """Quick check — any formulas in text?"""
        if not text:
            return False
        if _DISPLAY_DOLLAR.search(text):
            return True
        if _INLINE_DOLLAR.search(text):
            return True
        if _DISPLAY_BRACKET.search(text):
            return True
        if _INLINE_PAREN.search(text):
            return True
        if _LATEX_ENV_RE.search(text):
            return True
        if _UNICODE_MATH.search(text):
            return True
        return False

    def count(self, text: str) -> dict:
        """Count formulas by kind."""
        formulas = self.extract(text)
        by_kind: dict = {}
        for f in formulas:
            key = f.kind.value
            by_kind[key] = by_kind.get(key, 0) + 1
        inline = sum(1 for f in formulas if f.mode == FormulaMode.INLINE)
        display = sum(1 for f in formulas if f.mode == FormulaMode.DISPLAY)
        return {
            "total": len(formulas),
            "inline": inline,
            "display": display,
            "by_kind": by_kind,
        }

    # -- Internal ------------------------------------------------------------

    def _remove_overlaps(
        self, formulas: List[ExtractedFormula],
    ) -> List[ExtractedFormula]:
        """Keep first/longest detection when overlapping."""
        if not formulas:
            return []

        # Sort by start, then by length descending
        formulas.sort(key=lambda f: (f.start, -(f.end - f.start)))

        result: List[ExtractedFormula] = []
        for f in formulas:
            overlaps = False
            for accepted in result:
                if f.start < accepted.end and f.end > accepted.start:
                    overlaps = True
                    break
            if not overlaps:
                result.append(f)

        return result
