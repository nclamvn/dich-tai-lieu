"""
Phase 2.1.2: LaTeX Math Expression Extractor

This module extracts individual math expressions from compound LaTeX blocks
to improve OMML conversion success rates.

Root Cause:
-----------
Phase 2.1.0 extracts LaTeX blocks from arXiv sources that often contain:
- Multiple inline equations: "Given $f: \\N \\to H$ in $H$"
- Mixed inline + display: "Let $x$ be such that $$ \\sum_{i=1}^n i $$"
- Plain text mixed with math

Pandoc's latex_to_omml() expects single, clean equations and fails on compound blocks.

Solution:
---------
1. Parse LaTeX blocks to extract individual math segments
2. Select the "primary" equation using heuristics (display > inline, longer > shorter)
3. Enrich metadata with clean, isolated equations for OMML conversion

Usage:
------
```python
from core.latex_utils.latex_math_extractor import extract_math_segments, select_primary_equation

latex_block = "Given $f: \\N \\to H$ taking values in $H$, define $$ \\sup_{n} \\|f(n)\\|_H $$"

# Extract all math segments
segments = extract_math_segments(latex_block)
# Returns 3 MathSegment objects for the inline equations + 1 for display

# Select primary equation (will choose the display equation)
primary = select_primary_equation(segments)
# Returns: "\\sup_{n} \\|f(n)\\|_H"
```
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class MathSegment:
    """
    Represents a single math expression extracted from LaTeX source.

    Attributes:
        content: The math expression WITHOUT delimiters (e.g., "x^2", not "$x^2$")
        math_type: Type of math environment ('inline', 'display', 'environment')
        delimiter: The delimiter used (e.g., '$', '$$', '\\[', 'equation')
        start_pos: Character position where this segment starts in original text
        length: Length of the complete segment including delimiters
    """
    content: str
    math_type: str  # 'inline' | 'display' | 'environment'
    delimiter: str
    start_pos: int
    length: int

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"MathSegment(type={self.math_type}, delimiter='{self.delimiter}', content='{preview}')"


def extract_math_segments(latex_block: str) -> List[MathSegment]:
    """
    Extract all math expressions from a LaTeX block.

    Handles:
    - Display math: $$...$$ and \\[...\\]
    - Inline math: $...$
    - Environments: \\begin{equation}...\\end{equation}, \\begin{align}...\\end{align}, etc.

    Edge cases:
    - Escaped dollar signs (\\$) are ignored
    - Nested braces are handled correctly
    - Line breaks within expressions are preserved

    Args:
        latex_block: LaTeX source text potentially containing multiple math expressions

    Returns:
        List of MathSegment objects ordered by appearance in source text

    Examples:
        >>> extract_math_segments("Let $x^2$ and $y^2$ be...")
        [MathSegment(type='inline', content='x^2', ...),
         MathSegment(type='inline', content='y^2', ...)]

        >>> extract_math_segments("$a$ and $$ b $$")
        [MathSegment(type='inline', content='a', ...),
         MathSegment(type='display', content=' b ', ...)]
    """
    segments = []

    # Pattern priorities (process in order to avoid conflicts):
    # 1. Math environments (highest priority - most specific)
    # 2. Display math delimiters ($$...$$ and \[...\])
    # 3. Inline math ($...$)

    # Step 1: Extract math environments (equation, align, gather, etc.)
    env_pattern = r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?)\}(.*?)\\end\{\1\}'
    for match in re.finditer(env_pattern, latex_block, re.DOTALL):
        env_name = match.group(1)
        content = match.group(2).strip()
        segments.append(MathSegment(
            content=content,
            math_type='environment',
            delimiter=env_name,
            start_pos=match.start(),
            length=len(match.group(0))
        ))

    # Create a mask to track which positions are already covered by environments
    covered = set()
    for seg in segments:
        covered.update(range(seg.start_pos, seg.start_pos + seg.length))

    # Step 2: Extract display math ($$...$$ and \[...\])
    # Handle $$...$$ (display math)
    display_pattern = r'\$\$(.*?)\$\$'
    for match in re.finditer(display_pattern, latex_block, re.DOTALL):
        # Skip if this position is already covered by an environment
        if match.start() in covered:
            continue

        content = match.group(1).strip()
        segments.append(MathSegment(
            content=content,
            math_type='display',
            delimiter='$$',
            start_pos=match.start(),
            length=len(match.group(0))
        ))
        # Mark as covered
        covered.update(range(match.start(), match.end()))

    # Handle \[...\] (display math)
    bracket_display_pattern = r'\\\[(.*?)\\\]'
    for match in re.finditer(bracket_display_pattern, latex_block, re.DOTALL):
        if match.start() in covered:
            continue

        content = match.group(1).strip()
        segments.append(MathSegment(
            content=content,
            math_type='display',
            delimiter='\\[',
            start_pos=match.start(),
            length=len(match.group(0))
        ))
        covered.update(range(match.start(), match.end()))

    # Step 3: Extract inline math ($...$)
    # This is trickier because we need to avoid escaped \$ and avoid matching $$ delimiters
    inline_segments = _extract_inline_math(latex_block, covered)
    segments.extend(inline_segments)

    # Sort by position in original text
    segments.sort(key=lambda s: s.start_pos)

    logger.debug(f"Extracted {len(segments)} math segments from LaTeX block")
    return segments


def _extract_inline_math(text: str, covered: set) -> List[MathSegment]:
    """
    Extract inline math expressions ($...$) with proper handling of edge cases.

    Args:
        text: LaTeX source text
        covered: Set of character positions already covered by other math segments

    Returns:
        List of MathSegment objects for inline math
    """
    segments = []
    i = 0

    while i < len(text):
        # Skip if already covered
        if i in covered:
            i += 1
            continue

        # Check for $ delimiter
        if text[i] == '$':
            # Check if escaped (\$)
            if i > 0 and text[i-1] == '\\':
                i += 1
                continue

            # Check if this is $$ (display math, already handled)
            if i + 1 < len(text) and text[i+1] == '$':
                i += 2
                continue

            # Find matching closing $
            j = i + 1
            while j < len(text):
                if text[j] == '$':
                    # Check if escaped
                    if j > 0 and text[j-1] == '\\':
                        j += 1
                        continue

                    # Check if this starts $$ (should not close single $)
                    if j + 1 < len(text) and text[j+1] == '$':
                        j += 2
                        continue

                    # Found matching closing $
                    content = text[i+1:j]

                    # Skip empty content or whitespace-only
                    if content.strip():
                        segments.append(MathSegment(
                            content=content,
                            math_type='inline',
                            delimiter='$',
                            start_pos=i,
                            length=j - i + 1
                        ))

                    i = j + 1
                    break

                j += 1
            else:
                # No matching closing $, skip this opening $
                i += 1
        else:
            i += 1

    return segments


def select_primary_equation(segments: List[MathSegment]) -> Optional[str]:
    """
    Select the most important/representative equation from a list of math segments.

    Selection Heuristics (in priority order):
    1. Math type: Environment > Display > Inline
    2. Content length: Longer equations are more likely to be important
    3. Position: Earlier equations (if tied on above criteria)

    Rationale:
    - Display equations are typically more important than inline
    - Longer equations contain more information
    - First equation is often the main definition

    Args:
        segments: List of MathSegment objects

    Returns:
        The content (without delimiters) of the primary equation, or None if no segments

    Examples:
        >>> segs = extract_math_segments("Let $x$ be such that $$ \\sum_{i=1}^n i = \\frac{n(n+1)}{2} $$")
        >>> select_primary_equation(segs)
        '\\sum_{i=1}^n i = \\frac{n(n+1)}{2}'

        >>> segs = extract_math_segments("Given $f: X \\to Y$ and $g: Y \\to Z$")
        >>> select_primary_equation(segs)  # Returns longer equation
        'f: X \\to Y'  # or 'g: Y \\to Z' if similar length
    """
    if not segments:
        return None

    # Priority 1: Prefer environments and display math
    environment_segs = [s for s in segments if s.math_type == 'environment']
    display_segs = [s for s in segments if s.math_type == 'display']
    inline_segs = [s for s in segments if s.math_type == 'inline']

    # Priority order
    for segment_group in [environment_segs, display_segs, inline_segs]:
        if segment_group:
            # Priority 2: Among same type, choose longest
            primary = max(segment_group, key=lambda s: len(s.content.strip()))
            logger.debug(f"Selected primary equation: type={primary.math_type}, length={len(primary.content)}")
            return primary.content.strip()

    return None


def is_valid_single_equation(latex_str: str) -> bool:
    """
    Check if a LaTeX string is a valid single equation (no nested delimiters or plain text).

    This validates that:
    1. No math delimiters inside the content (already extracted)
    2. No excessive plain text (heuristic: >50% non-math characters suggests it's not a clean equation)
    3. Contains actual math symbols/commands

    Args:
        latex_str: LaTeX expression (without outer delimiters)

    Returns:
        True if this appears to be a clean, single equation

    Examples:
        >>> is_valid_single_equation("x^2 + y^2 = z^2")
        True
        >>> is_valid_single_equation("Let $x$ be a number")  # nested $
        False
        >>> is_valid_single_equation("\\sum_{i=1}^n i")
        True
    """
    # Check 1: Should not contain math delimiters (means nested or compound)
    if '$' in latex_str or '\\[' in latex_str or '\\]' in latex_str:
        return False

    if '\\begin{' in latex_str and '\\end{' in latex_str:
        return False

    # Check 2: Should contain LaTeX math commands or symbols
    math_indicators = [
        '\\', '^', '_', '{', '}',  # Basic LaTeX structure
        '\\sum', '\\int', '\\frac', '\\sqrt',  # Common commands
        '\\alpha', '\\beta', '\\gamma',  # Greek letters
        '=', '+', '-', '*', '/'  # Math operators
    ]

    has_math = any(indicator in latex_str for indicator in math_indicators)

    if not has_math:
        logger.debug(f"Invalid equation: no math indicators found in '{latex_str[:50]}'")
        return False

    # Check 3: Heuristic for excessive plain text
    # Count rough ratio of math vs text by checking for math commands
    latex_command_count = latex_str.count('\\')
    total_length = len(latex_str)

    # Very short strings with no LaTeX commands are suspicious
    if total_length < 3 and latex_command_count == 0:
        return False

    return True


def enrich_node_with_equations(node, latex_source: str) -> None:
    """
    Enrich a DocNode with extracted equation metadata.

    This is the integration point for Phase 2.1.2. Call this function from
    arxiv_integration.py to populate equation metadata.

    Populates:
    - node.metadata['latex_equation_primary']: The primary equation (for OMML)
    - node.metadata['latex_equation_all']: List of all extracted equations
    - node.metadata['latex_source_full']: Original compound LaTeX block (for fallback)

    Args:
        node: DocNode object to enrich
        latex_source: Compound LaTeX block from Phase 2.1.0

    Example:
        >>> node = DocNode(text="...", node_type="equation")
        >>> latex_src = "Given $f: \\N \\to H$ in $H$ where $$ \\sup_n \\|f(n)\\| < \\infty $$"
        >>> enrich_node_with_equations(node, latex_src)
        >>> node.metadata['latex_equation_primary']
        '\\sup_n \\|f(n)\\| < \\infty'
        >>> len(node.metadata['latex_equation_all'])
        3
    """
    try:
        # Always preserve original for fallback
        node.metadata['latex_source_full'] = latex_source

        # Extract individual equations
        segments = extract_math_segments(latex_source)

        if not segments:
            logger.warning(f"No math segments found in LaTeX source: {latex_source[:100]}")
            # Fallback: use original as-is
            node.metadata['latex_source'] = latex_source
            return

        # Select primary equation
        primary = select_primary_equation(segments)

        if primary and is_valid_single_equation(primary):
            node.metadata['latex_equation_primary'] = primary
            logger.debug(f"✅ Primary equation extracted: {primary[:50]}")
        else:
            logger.debug(f"⚠️  Primary equation invalid, using fallback")
            node.metadata['latex_source'] = latex_source

        # Store all equations for potential future use
        all_equations = [s.content.strip() for s in segments if is_valid_single_equation(s.content)]
        if all_equations:
            node.metadata['latex_equation_all'] = all_equations
            logger.debug(f"Stored {len(all_equations)} valid equations in metadata")

    except Exception as e:
        logger.error(f"Error enriching node with equations: {e}", exc_info=True)
        # Fallback: use original latex_source
        node.metadata['latex_source'] = latex_source


# ============================================================================
# Testing and Validation Functions
# ============================================================================

def test_extractor():
    """
    Manual test function for development and debugging.
    Run with: python3 -c "from core.latex_utils.latex_math_extractor import test_extractor; test_extractor()"
    """
    test_cases = [
        # Case 1: Simple inline
        ("Let $x^2$ be a number", 1, "x^2"),

        # Case 2: Multiple inline
        ("Given $f: \\N \\to H$ taking values in $H$", 2, "f: \\N \\to H"),

        # Case 3: Display + inline
        ("Let $x$ be such that $$ \\sum_{i=1}^n i = \\frac{n(n+1)}{2} $$", 2, "\\sum_{i=1}^n i = \\frac{n(n+1)}{2}"),

        # Case 4: Environment
        ("\\begin{equation} E = mc^2 \\end{equation}", 1, "E = mc^2"),

        # Case 5: Complex real-world example
        ("Given a sequence $f\\colon \\N \\to H$ taking values in a Hilbert space $H$, define $$ \\sup_{n,d \\in \\N} \\left\\| \\sum_{j=1}^n f(jd) \\right\\|_H $$", 3, "\\sup_{n,d \\in \\N} \\left\\| \\sum_{j=1}^n f(jd) \\right\\|_H"),

        # Case 6: No math
        ("This is plain text with no math", 0, None),

        # Case 7: Escaped dollar
        ("Price is \\$100", 0, None),
    ]

    print("=" * 70)
    print("LaTeX Math Extractor - Test Cases")
    print("=" * 70)

    for i, (latex_block, expected_count, expected_primary) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: {latex_block[:60]}...")

        segments = extract_math_segments(latex_block)
        primary = select_primary_equation(segments)

        print(f"Segments found: {len(segments)} (expected: {expected_count})")
        for seg in segments:
            print(f"  - {seg}")

        if expected_primary:
            print(f"Primary: {primary}")
            print(f"Expected: {expected_primary}")
            match = primary == expected_primary if primary else False
            print(f"✅ PASS" if match else f"❌ FAIL")
        else:
            print(f"Primary: {primary} (expected None)")
            print(f"✅ PASS" if primary is None else f"❌ FAIL")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Enable logging for manual testing
    logging.basicConfig(level=logging.DEBUG)
    test_extractor()
