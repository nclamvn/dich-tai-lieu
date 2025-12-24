"""
Phase 2.2.0 - LaTeX Equation Splitter

High-confidence LaTeX equation extraction from compound LaTeX blocks.
Designed to work with arXiv LaTeX sources that may contain text + multiple equations.

Conservative approach: Accuracy over coverage.
If uncertain about splitting safety, returns is_confident=False to trigger fallback.

Usage:
    >>> from core.latex.eq_splitter import split_latex_equations
    >>> result = split_latex_equations("Given $f\\colon \\N \\to H$ in $H$ where ...")
    >>> if result.is_confident:
    ...     for eq in result.equation_segments:
    ...         convert_to_omml(eq)
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SplitEquationResult:
    """
    Represents the result of splitting a LaTeX source string
    that may contain text + multiple equations.

    Attributes:
        original: Original input LaTeX string
        text_segments: Plain text portions (Phase 2.2.0: not used, reserved for future)
        equation_segments: List of isolated LaTeX equations, ready for OMML conversion
        is_confident: True if splitting is safe and accurate, False triggers fallback
        reason: Optional explanation for is_confident=False (for debugging/logging)
    """
    original: str
    text_segments: List[str]
    equation_segments: List[str]
    is_confident: bool
    reason: Optional[str] = None


def _strip_delimiters(latex_str: str) -> str:
    """
    Remove common LaTeX math delimiters from a string.

    Supports: $...$, $$...$$, \\[...\\], \\(...\\)

    Args:
        latex_str: LaTeX string with delimiters

    Returns:
        LaTeX string without delimiters, trimmed
    """
    s = latex_str.strip()

    # Display math: $$...$$ or \[...\]
    if s.startswith('$$') and s.endswith('$$'):
        return s[2:-2].strip()
    if s.startswith('\\[') and s.endswith('\\]'):
        return s[2:-2].strip()

    # Inline math: $...$ or \(...\)
    if s.startswith('$') and s.endswith('$') and not s.startswith('$$'):
        return s[1:-1].strip()
    if s.startswith('\\(') and s.endswith('\\)'):
        return s[2:-2].strip()

    return s


def _detect_environment_block(latex_str: str) -> Optional[str]:
    """
    Detect if latex_str is a single LaTeX environment block.

    Looks for: \\begin{env_name}...\\end{env_name}
    where env_name is equation, align, gather, multline, eqnarray (with optional *)

    Args:
        latex_str: LaTeX string to analyze

    Returns:
        Full environment block if found and valid, None otherwise
    """
    s = latex_str.strip()

    # Pattern: \begin{env}...\end{env}
    # Supported environments: equation, align, gather, multline, eqnarray (+ starred variants)
    env_pattern = r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?)\}(.*?)\\end\{\1\}'

    match = re.search(env_pattern, s, re.DOTALL)
    if match:
        # Check if the entire string is just this environment (possibly with leading/trailing whitespace)
        full_match = match.group(0)
        remaining = s.replace(full_match, '').strip()

        if not remaining:
            # Entire string is just this environment → confident
            return full_match

    return None


def _detect_display_math(latex_str: str) -> Optional[str]:
    """
    Detect if latex_str is a single display math expression.

    Looks for: $$...$$ or \\[...\\]

    Args:
        latex_str: LaTeX string to analyze

    Returns:
        Inner expression (without delimiters) if found and valid, None otherwise
    """
    s = latex_str.strip()

    # Case 1: $$...$$
    if s.startswith('$$') and s.endswith('$$'):
        inner = s[2:-2].strip()
        # Check for nested $$ (would be invalid)
        if '$$' not in inner:
            return inner

    # Case 2: \[...\]
    if s.startswith('\\[') and s.endswith('\\]'):
        inner = s[2:-2].strip()
        # Check for nested \[...\] (would be invalid)
        if '\\[' not in inner and '\\]' not in inner:
            return inner

    return None


def _count_inline_math(latex_str: str) -> int:
    """
    Count the number of inline math expressions ($...$) in a string.

    Note: This is a simplified counter. It doesn't handle escaped dollars (\\$).
    For Phase 2.2.0 conservative approach, presence of inline math with text
    → is_confident=False.

    Args:
        latex_str: LaTeX string to analyze

    Returns:
        Count of inline math expressions (number of $ pairs)
    """
    # Simple heuristic: count $ symbols and divide by 2
    # This is not perfect (doesn't handle \\$), but sufficient for confidence check
    dollar_count = latex_str.count('$') - latex_str.count('\\$')
    return dollar_count // 2


def _has_text_content(latex_str: str) -> bool:
    """
    Check if latex_str contains significant plain text (not just math).

    Heuristic: If there are words outside of math delimiters, it's text.

    Args:
        latex_str: LaTeX string to analyze

    Returns:
        True if plain text detected, False if appears to be pure math
    """
    s = latex_str.strip()

    # Remove all math content temporarily
    # Remove $$...$$ (display)
    s = re.sub(r'\$\$.*?\$\$', '', s, flags=re.DOTALL)
    # Remove \[...\] (display)
    s = re.sub(r'\\\[.*?\\\]', '', s, flags=re.DOTALL)
    # Remove $...$ (inline)
    s = re.sub(r'\$[^\$]+\$', '', s)
    # Remove environments
    s = re.sub(r'\\begin\{[^}]+\}.*?\\end\{[^}]+\}', '', s, flags=re.DOTALL)

    # Check what's left
    s = s.strip()

    # If there are alphabetic words remaining (not LaTeX commands), it's text
    # Improved heuristic: look for common English words that indicate prose
    # This distinguishes between LaTeX variable/function names and actual text
    # Common prose indicators: articles, prepositions, conjunctions, verbs
    # IMPORTANT: Exclude LaTeX commands (preceded by \)
    prose_indicators = r'(?<!\\)\b(the|a|an|in|on|at|to|for|of|with|by|from|that|this|these|those|' \
                       r'is|are|was|were|be|been|being|have|has|had|do|does|did|' \
                       r'given|where|such|which|when|then|than|or|and|but|if|so|' \
                       r'let|suppose|assume|consider|prove|show|hence|thus|therefore)\b'

    # Case insensitive search for prose
    return bool(re.search(prose_indicators, s, re.IGNORECASE))


def _is_single_clean_equation(latex_str: str) -> bool:
    """
    Check if latex_str appears to be a single, clean LaTeX equation
    without delimiters or surrounding text.

    Args:
        latex_str: LaTeX string to analyze

    Returns:
        True if appears to be clean single equation, False otherwise
    """
    s = latex_str.strip()

    # Check for no obvious delimiters
    if s.startswith('$') or s.startswith('\\[') or s.startswith('\\begin'):
        return False

    # Check for no obvious text content
    if _has_text_content(s):
        return False

    # Should contain typical math LaTeX commands
    math_indicators = ['\\', '_', '^', '{', '}']
    has_math = any(indicator in s for indicator in math_indicators)

    return has_math


def split_latex_equations(latex_source: str) -> SplitEquationResult:
    """
    Phase 2.2.0 - High confidence LaTeX equation splitter.

    Extracts individual math equations from compound LaTeX blocks that may contain
    text + multiple equations. Conservative approach: only returns is_confident=True
    when absolutely certain about extraction safety.

    Handles 5 cases:
    1. Single clean equation (no delimiters, no text) → confident, 1 segment
    2. Inline math with text (text + $...$) → not confident, fallback
    3. Clean display math ($$...$$ or \\[...\\]) → confident, extract inner
    4. Environment block (\\begin{equation}...\\end{equation}) → confident, keep full block
    5. Mixed content → conservative: not confident unless can safely extract clean display

    Args:
        latex_source: Raw LaTeX string from DocNode.metadata["latex_source"]

    Returns:
        SplitEquationResult with:
            - equation_segments: list of isolated equations (if confident)
            - is_confident: True if safe for OMML conversion, False for fallback
            - reason: explanation for is_confident=False (for debugging)

    Examples:
        >>> # Case 1: Single clean equation
        >>> result = split_latex_equations(r"\\sup_{n,d\\in\\N} \\|x\\|")
        >>> assert result.is_confident and len(result.equation_segments) == 1

        >>> # Case 3: Display math
        >>> result = split_latex_equations(r"$$ E = mc^2 $$")
        >>> assert result.is_confident and result.equation_segments[0] == "E = mc^2"

        >>> # Case 2: Text with inline math (not confident)
        >>> result = split_latex_equations(r"Given $f: \\N \\to H$ in space $H$")
        >>> assert not result.is_confident
    """
    if not latex_source or not latex_source.strip():
        return SplitEquationResult(
            original=latex_source,
            text_segments=[],
            equation_segments=[],
            is_confident=False,
            reason="empty or whitespace-only input"
        )

    original = latex_source
    s = latex_source.strip()

    # Case 4: Check for environment block (equation, align, etc.)
    env_block = _detect_environment_block(s)
    if env_block:
        logger.debug(f"Phase 2.2.0: Detected environment block")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[env_block],
            is_confident=True,
            reason=None
        )

    # Case 3: Check for clean display math ($$...$$ or \[...\])
    display_math = _detect_display_math(s)
    if display_math:
        logger.debug(f"Phase 2.2.0: Detected clean display math")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[display_math],
            is_confident=True,
            reason=None
        )

    # Case 1: Check for single clean equation (no delimiters, no text)
    if _is_single_clean_equation(s):
        logger.debug(f"Phase 2.2.0: Detected single clean equation")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[s],
            is_confident=True,
            reason=None
        )

    # Case 2 & 5: Mixed content or inline math with text
    # Check for inline math
    inline_count = _count_inline_math(s)
    has_text = _has_text_content(s)

    if inline_count > 0 and has_text:
        logger.debug(f"Phase 2.2.0: Detected text with inline math (not confident)")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[],
            is_confident=False,
            reason="contains inline math with surrounding text"
        )

    if inline_count > 0 and not has_text:
        # Only inline math, no text → could extract, but Phase 2.2.0 keeps it simple
        # Inline math is low priority for OMML (usually renders fine as text)
        logger.debug(f"Phase 2.2.0: Detected inline-only math (not confident for OMML)")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[],
            is_confident=False,
            reason="inline math only (low priority for OMML)"
        )

    # Case 5: Mixed content without clear pattern
    if has_text:
        logger.debug(f"Phase 2.2.0: Detected mixed content (not confident)")
        return SplitEquationResult(
            original=original,
            text_segments=[],
            equation_segments=[],
            is_confident=False,
            reason="mixed content without clear extraction pattern"
        )

    # Fallback: Uncertain about content
    logger.debug(f"Phase 2.2.0: Unable to confidently classify LaTeX source")
    return SplitEquationResult(
        original=original,
        text_segments=[],
        equation_segments=[],
        is_confident=False,
        reason="unable to confidently classify LaTeX structure"
    )


def get_splitter_statistics(results: List[SplitEquationResult]) -> dict:
    """
    Calculate statistics from a batch of splitting results.

    Useful for testing and reporting.

    Args:
        results: List of SplitEquationResult objects

    Returns:
        Dictionary with statistics:
            - total: total results
            - confident: number with is_confident=True
            - confident_rate: percentage confident
            - total_equations: sum of equation_segments
            - avg_equations_per_result: average when confident
    """
    if not results:
        return {
            'total': 0,
            'confident': 0,
            'confident_rate': 0.0,
            'total_equations': 0,
            'avg_equations_per_result': 0.0
        }

    total = len(results)
    confident = sum(1 for r in results if r.is_confident)
    total_equations = sum(len(r.equation_segments) for r in results if r.is_confident)

    return {
        'total': total,
        'confident': confident,
        'confident_rate': confident / total * 100 if total > 0 else 0.0,
        'total_equations': total_equations,
        'avg_equations_per_result': total_equations / confident if confident > 0 else 0.0
    }
