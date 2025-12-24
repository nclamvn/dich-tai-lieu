#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Table Detection Patterns - Regex patterns for various table formats.

Supports:
- Markdown tables (| col | col |)
- ASCII box tables (+---+---+)
- Plain text aligned tables (space/tab separated)
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# MARKDOWN TABLE PATTERNS
# =============================================================================

# Line that looks like a markdown table row: | cell | cell |
MARKDOWN_ROW_PATTERN = re.compile(r'^\s*\|.*\|\s*$')

# Separator line: |---|---|---| or |:--|:--:|--:|
MARKDOWN_SEPARATOR_PATTERN = re.compile(r'^\s*\|[\s\-:]+\|[\s\-:]*\|\s*$')

# Individual separator cell: ---, :---, :---:, ---:
MARKDOWN_ALIGN_PATTERN = re.compile(r'^:?-+:?$')


# =============================================================================
# ASCII TABLE PATTERNS
# =============================================================================

# Border line: +---+---+ or +===+===+
ASCII_BORDER_PATTERN = re.compile(r'^[\s]*[\+\-\=]+[\+\-\=]*$')

# Row with pipe separators (ASCII style)
ASCII_ROW_PATTERN = re.compile(r'^[\s]*\|.*\|[\s]*$')


# =============================================================================
# PLAIN TEXT TABLE DETECTION
# =============================================================================

# Minimum spaces between columns for plain text tables
MIN_COLUMN_GAP = 2


def is_markdown_table_row(line: str) -> bool:
    """Check if line is a markdown table row."""
    return bool(MARKDOWN_ROW_PATTERN.match(line))


def is_markdown_separator(line: str) -> bool:
    """Check if line is a markdown table separator."""
    if not MARKDOWN_SEPARATOR_PATTERN.match(line):
        return False

    # Verify each cell is a valid separator
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    cells = line.split('|')
    for cell in cells:
        cell = cell.strip()
        if cell and not MARKDOWN_ALIGN_PATTERN.match(cell):
            return False

    return True


def parse_markdown_alignment(separator_line: str) -> List[str]:
    """
    Parse alignment from markdown separator line.

    Args:
        separator_line: The |---|:--:|---:| line

    Returns:
        List of alignments: "left", "center", "right"
    """
    line = separator_line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    alignments = []
    cells = line.split('|')

    for cell in cells:
        cell = cell.strip()
        if cell.startswith(':') and cell.endswith(':'):
            alignments.append('center')
        elif cell.endswith(':'):
            alignments.append('right')
        else:
            alignments.append('left')

    return alignments


def parse_markdown_row(line: str) -> List[str]:
    """
    Parse a markdown table row into cells.

    Args:
        line: Table row like "| cell1 | cell2 | cell3 |"

    Returns:
        List of cell contents
    """
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    cells = [cell.strip() for cell in line.split('|')]
    return cells


def is_ascii_border(line: str) -> bool:
    """Check if line is an ASCII table border."""
    stripped = line.strip()
    if not stripped:
        return False

    # Must start with + or - or =
    if stripped[0] not in '+-=':
        return False

    # Should only contain +, -, =, and spaces
    return bool(re.match(r'^[\+\-\=\s]+$', stripped))


def detect_plain_text_columns(lines: List[str]) -> Optional[List[Tuple[int, int]]]:
    """
    Detect column boundaries in plain text table.

    Uses heuristic: find positions where multiple lines have spaces.

    Args:
        lines: Consecutive lines that might be a table

    Returns:
        List of (start, end) column positions, or None if not a table
    """
    if len(lines) < 2:
        return None

    # Find the longest line
    max_len = max(len(line) for line in lines)

    # Count spaces at each position across all lines
    space_counts = [0] * max_len

    for line in lines:
        padded = line.ljust(max_len)
        for i, char in enumerate(padded):
            if char == ' ' or char == '\t':
                space_counts[i] += 1

    # Find positions where ALL lines have spaces (column separators)
    threshold = len(lines) * 0.8  # 80% of lines must have space

    # Find runs of separator positions
    separators = []
    in_separator = False
    sep_start = 0

    for i, count in enumerate(space_counts):
        if count >= threshold:
            if not in_separator:
                in_separator = True
                sep_start = i
        else:
            if in_separator:
                # End of separator run
                if i - sep_start >= MIN_COLUMN_GAP:
                    separators.append((sep_start, i))
                in_separator = False

    # Need at least one separator for 2+ columns
    if not separators:
        return None

    # Build column boundaries
    columns = []
    prev_end = 0

    for sep_start, sep_end in separators:
        if sep_start > prev_end:
            columns.append((prev_end, sep_start))
        prev_end = sep_end

    # Add final column
    if prev_end < max_len:
        columns.append((prev_end, max_len))

    return columns if len(columns) >= 2 else None


def parse_plain_text_row(line: str, columns: List[Tuple[int, int]]) -> List[str]:
    """
    Parse a plain text table row using column boundaries.

    Args:
        line: Table row
        columns: List of (start, end) column positions

    Returns:
        List of cell contents
    """
    cells = []
    padded = line.ljust(columns[-1][1]) if columns else line

    for start, end in columns:
        cell = padded[start:end].strip()
        cells.append(cell)

    return cells


@dataclass
class DetectedTable:
    """Result of table detection."""
    start_line: int
    end_line: int
    table_type: str  # "markdown", "ascii", "plain"
    headers: List[str]
    rows: List[List[str]]
    alignments: Optional[List[str]] = None
    has_header: bool = True


def detect_markdown_table(lines: List[str], start_idx: int) -> Optional[DetectedTable]:
    """
    Detect and parse a markdown table starting at index.

    Args:
        lines: All document lines
        start_idx: Index to start looking

    Returns:
        DetectedTable or None
    """
    if start_idx >= len(lines):
        return None

    # First line must be a table row
    if not is_markdown_table_row(lines[start_idx]):
        return None

    # Collect table lines
    table_lines = []
    i = start_idx

    while i < len(lines) and is_markdown_table_row(lines[i]):
        table_lines.append(lines[i])
        i += 1

    if len(table_lines) < 2:
        return None

    # Check for separator (should be second line for proper table)
    has_separator = len(table_lines) >= 2 and is_markdown_separator(table_lines[1])

    if has_separator:
        headers = parse_markdown_row(table_lines[0])
        alignments = parse_markdown_alignment(table_lines[1])
        rows = [parse_markdown_row(line) for line in table_lines[2:]]
    else:
        # No separator - treat first row as data
        headers = []
        alignments = None
        rows = [parse_markdown_row(line) for line in table_lines]

    return DetectedTable(
        start_line=start_idx,
        end_line=i - 1,
        table_type="markdown",
        headers=headers,
        rows=rows,
        alignments=alignments,
        has_header=has_separator,
    )


def detect_ascii_table(lines: List[str], start_idx: int) -> Optional[DetectedTable]:
    """
    Detect and parse an ASCII box table.

    Args:
        lines: All document lines
        start_idx: Index to start looking

    Returns:
        DetectedTable or None
    """
    if start_idx >= len(lines):
        return None

    # Must start with a border
    if not is_ascii_border(lines[start_idx]):
        return None

    # Collect table lines
    table_lines = []
    i = start_idx

    while i < len(lines):
        line = lines[i]
        if is_ascii_border(line) or is_markdown_table_row(line):
            table_lines.append(line)
            i += 1
        elif not line.strip():
            break
        else:
            break

    if len(table_lines) < 3:  # Need at least border + row + border
        return None

    # Parse rows (skip borders)
    data_rows = []
    for line in table_lines:
        if not is_ascii_border(line) and is_markdown_table_row(line):
            data_rows.append(parse_markdown_row(line))

    if not data_rows:
        return None

    # First data row is typically header
    headers = data_rows[0] if data_rows else []
    rows = data_rows[1:] if len(data_rows) > 1 else []

    return DetectedTable(
        start_line=start_idx,
        end_line=i - 1,
        table_type="ascii",
        headers=headers,
        rows=rows,
        has_header=len(data_rows) > 1,
    )


def count_table_columns(line: str, separator: str = '|') -> int:
    """Count columns in a table row."""
    if separator not in line:
        return 0

    # For markdown-style tables
    line = line.strip()
    if line.startswith(separator):
        line = line[1:]
    if line.endswith(separator):
        line = line[:-1]

    return line.count(separator) + 1
