#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
List Detection Patterns - Regex patterns for bullet and numbered lists.

Supports:
- Standard bullet markers (•, -, *, etc.)
- Arabic numbered lists (1. 2. 3.)
- Alphabetic lists (a. b. c. / A. B. C.)
- Roman numeral lists (i. ii. iii. / I. II. III.)
- Parenthetical lists ((1), (a), etc.)
- Vietnamese list patterns
- Nested list detection via indentation
"""

import re
from typing import Tuple, Optional, List


# =============================================================================
# BULLET LIST PATTERNS
# =============================================================================

BULLET_PATTERNS = [
    r'^[\s]*[-•*●○▪▫▸]\s+',           # Standard bullets: -, •, *, etc.
    r'^[\s]*[➤➢→►]\s+',               # Arrow bullets
    r'^[\s]*[\+]\s+',                  # Plus sign
    r'^[\s]*[◆◇■□]\s+',               # Shape bullets
]

# Combined bullet pattern
BULLET_PATTERN_COMBINED = re.compile(
    r'^(\s*)([-•*●○▪▫▸➤➢→►+◆◇■□])\s+(.+)$'
)


# =============================================================================
# NUMBERED LIST PATTERNS
# =============================================================================

NUMBERED_PATTERNS = [
    r'^[\s]*\d+\.\s+',                 # 1. 2. 3.
    r'^[\s]*\d+\)\s+',                 # 1) 2) 3)
    r'^[\s]*[a-z]\.\s+',               # a. b. c.
    r'^[\s]*[a-z]\)\s+',               # a) b) c)
    r'^[\s]*[A-Z]\.\s+',               # A. B. C.
    r'^[\s]*[A-Z]\)\s+',               # A) B) C)
    r'^[\s]*[ivxlcdm]+\.\s+',          # i. ii. iii. (roman lowercase)
    r'^[\s]*[ivxlcdm]+\)\s+',          # i) ii) iii)
    r'^[\s]*[IVXLCDM]+\.\s+',          # I. II. III. (roman uppercase)
    r'^[\s]*[IVXLCDM]+\)\s+',          # I) II) III)
    r'^[\s]*\(\d+\)\s+',               # (1) (2) (3)
    r'^[\s]*\([a-z]\)\s+',             # (a) (b) (c)
    r'^[\s]*\([A-Z]\)\s+',             # (A) (B) (C)
]

# Combined numbered pattern with capture groups
# Groups: (1) indent, (2) marker, (3) content
NUMBERED_PATTERN_COMBINED = re.compile(
    r'^(\s*)(\d+[\.\)]|[a-zA-Z][\.\)]|[ivxlcdmIVXLCDM]+[\.\)]|\([\da-zA-Z]+\))\s+(.+)$'
)


# =============================================================================
# VIETNAMESE LIST PATTERNS
# =============================================================================

NUMBERED_PATTERNS_VI = [
    r'^[\s]*Thứ\s+\d+[.:]\s+',         # Thứ 1: Thứ 2:
    r'^[\s]*Điểm\s+[a-zđ][.:]\s+',     # Điểm a: Điểm b:
    r'^[\s]*Khoản\s+\d+[.:]\s+',       # Khoản 1: Khoản 2:
    r'^[\s]*Mục\s+\d+[.:]\s+',         # Mục 1: Mục 2:
]

NUMBERED_PATTERN_VI_COMBINED = re.compile(
    r'^(\s*)(Thứ\s+\d+|Điểm\s+[a-zđ]|Khoản\s+\d+|Mục\s+\d+)[.:]\s+(.+)$',
    re.IGNORECASE
)


# =============================================================================
# INDENTATION DETECTION
# =============================================================================

INDENT_SPACES_PER_LEVEL = 2  # 2 spaces = 1 nesting level
INDENT_TAB_SPACES = 4        # 1 tab = 4 spaces = 2 levels


def calculate_indent_level(line: str) -> int:
    """
    Calculate nesting level from leading whitespace.

    Args:
        line: Line with potential leading whitespace

    Returns:
        Nesting level (0 = top level)
    """
    if not line:
        return 0

    # Count leading whitespace
    stripped = line.lstrip()
    if not stripped:
        return 0

    indent_chars = len(line) - len(stripped)

    # Convert tabs to spaces
    expanded = line[:indent_chars].expandtabs(INDENT_TAB_SPACES)
    space_count = len(expanded)

    # Calculate level
    return space_count // INDENT_SPACES_PER_LEVEL


def is_bullet_item(line: str) -> Tuple[bool, int, str, str]:
    """
    Check if line is a bullet list item.

    Args:
        line: Line to check

    Returns:
        Tuple of (is_bullet, indent_level, marker, content)
    """
    match = BULLET_PATTERN_COMBINED.match(line)
    if match:
        indent = match.group(1)
        marker = match.group(2)
        content = match.group(3)
        level = calculate_indent_level(indent + 'x')  # Add char to avoid empty
        return True, level, marker, content

    return False, 0, '', ''


def is_numbered_item(line: str) -> Tuple[bool, int, str, str]:
    """
    Check if line is a numbered list item.

    Args:
        line: Line to check

    Returns:
        Tuple of (is_numbered, indent_level, marker, content)
    """
    # Check standard patterns
    match = NUMBERED_PATTERN_COMBINED.match(line)
    if match:
        indent = match.group(1)
        marker = match.group(2)
        content = match.group(3)
        level = calculate_indent_level(indent + 'x')
        return True, level, marker, content

    # Check Vietnamese patterns
    match_vi = NUMBERED_PATTERN_VI_COMBINED.match(line)
    if match_vi:
        indent = match_vi.group(1)
        marker = match_vi.group(2)
        content = match_vi.group(3)
        level = calculate_indent_level(indent + 'x')
        return True, level, marker + ':', content

    return False, 0, '', ''


def is_list_item(line: str) -> Tuple[bool, str, int, str, str]:
    """
    Check if line is any type of list item.

    Args:
        line: Line to check

    Returns:
        Tuple of (is_list, list_type, indent_level, marker, content)
        list_type is "bullet" or "numbered"
    """
    # Check bullet first
    is_bullet, level, marker, content = is_bullet_item(line)
    if is_bullet:
        return True, "bullet", level, marker, content

    # Check numbered
    is_num, level, marker, content = is_numbered_item(line)
    if is_num:
        return True, "numbered", level, marker, content

    return False, '', 0, '', ''


def is_list_continuation(line: str, prev_indent_level: int) -> bool:
    """
    Check if line is a continuation of a previous list item.

    A line continues a list item if:
    - It's indented more than the list marker
    - It doesn't start with a new list marker

    Args:
        line: Line to check
        prev_indent_level: Indent level of previous list item

    Returns:
        True if line continues previous item
    """
    if not line.strip():
        return False

    # Check if it's a new list item
    is_list, _, _, _, _ = is_list_item(line)
    if is_list:
        return False

    # Check indentation
    current_level = calculate_indent_level(line)
    return current_level > prev_indent_level


def detect_list_type(lines: List[str]) -> Optional[str]:
    """
    Detect the predominant list type in a group of lines.

    Args:
        lines: Lines to analyze

    Returns:
        "bullet", "numbered", or None
    """
    bullet_count = 0
    numbered_count = 0

    for line in lines:
        is_list, list_type, _, _, _ = is_list_item(line)
        if is_list:
            if list_type == "bullet":
                bullet_count += 1
            else:
                numbered_count += 1

    if bullet_count > numbered_count:
        return "bullet"
    elif numbered_count > 0:
        return "numbered"
    return None


def extract_marker_text(marker: str) -> str:
    """
    Extract clean marker text for display.

    Args:
        marker: Raw marker (e.g., "1.", "a)", "(2)")

    Returns:
        Clean marker for display
    """
    # Remove parentheses
    marker = marker.strip('()')

    return marker
