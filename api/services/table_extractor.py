"""
Text-Based Table Extractor.

Detects and extracts tables from plain text using pattern matching:
1. MARKDOWN tables:  | col1 | col2 |
2. TAB-SEPARATED:    col1\\tcol2\\tcol3
3. ALIGNED COLUMNS:  col1    col2    col3  (whitespace-aligned)

No Vision API needed — pure regex + heuristics.
Returns structured TableRegion objects ready for LayoutDNA.

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

class TableFormat(str, Enum):
    """Detected table format."""
    MARKDOWN = "markdown"
    TAB_SEPARATED = "tab_separated"
    ALIGNED = "aligned"
    GRID = "grid"  # +---+---+ style


@dataclass
class TableCell:
    """One cell in a detected table."""
    content: str
    row: int
    col: int
    is_header: bool = False


@dataclass
class DetectedTable:
    """A table found in text.

    Attributes:
        raw_text: Original text of the table region.
        cells: Parsed cells (row, col indexed).
        num_rows: Number of rows.
        num_cols: Number of columns.
        format: Detected format.
        start_offset: Position in source text.
        end_offset: Position (exclusive) in source text.
        has_header: Whether first row looks like a header.
        caption: Optional caption detected near the table.
    """
    raw_text: str
    cells: List[TableCell] = field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0
    format: TableFormat = TableFormat.MARKDOWN
    start_offset: int = 0
    end_offset: int = 0
    has_header: bool = False
    caption: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "format": self.format.value,
            "has_header": self.has_header,
            "caption": self.caption,
            "cells": [
                {
                    "content": c.content,
                    "row": c.row,
                    "col": c.col,
                    "is_header": c.is_header,
                }
                for c in self.cells
            ],
        }

    def get_row(self, row_idx: int) -> List[TableCell]:
        """Return all cells in a given row."""
        return [c for c in self.cells if c.row == row_idx]

    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """Return a specific cell."""
        for c in self.cells:
            if c.row == row and c.col == col:
                return c
        return None


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Markdown table row: | cell | cell | ... |
_MD_ROW = re.compile(r'^\s*\|(.+\|)\s*$', re.MULTILINE)

# Markdown separator: |---|---|  or  | :---: | ---: |
_MD_SEP = re.compile(r'^\s*\|[\s:]*-[-:|\s]+\|\s*$', re.MULTILINE)

# Grid table row:  +---+---+---+
_GRID_LINE = re.compile(r'^\s*\+[-=+]+\+\s*$', re.MULTILINE)

# Tab-separated: 2+ columns separated by tabs
_TAB_ROW = re.compile(r'^[^\t\n]+\t[^\t\n]+(?:\t[^\t\n]+)*$', re.MULTILINE)

# Caption: "Table N:" or "Table N." at start of line
_TABLE_CAPTION = re.compile(
    r'^(?:Table|TABLE|Bảng)\s+\d+[.:]\s*(.+)$',
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# TableExtractor
# ---------------------------------------------------------------------------

class TextTableExtractor:
    """Extract tables from plain text.

    Usage::

        extractor = TextTableExtractor()
        tables = extractor.extract(text)

        for table in tables:
            print(f"{table.num_rows}x{table.num_cols} {table.format.value}")
    """

    def __init__(
        self,
        min_rows: int = 2,
        min_cols: int = 2,
        aligned_min_spaces: int = 3,
    ):
        self.min_rows = min_rows
        self.min_cols = min_cols
        self.aligned_min_spaces = aligned_min_spaces

    def extract(self, text: str) -> List[DetectedTable]:
        """Find all tables in text.

        Detection priority: markdown > grid > tab-separated > aligned.
        Non-overlapping: earlier detection wins.
        """
        if not text or not text.strip():
            return []

        tables: List[DetectedTable] = []

        # 1. Markdown tables
        tables.extend(self._find_markdown_tables(text))

        # 2. Grid tables
        tables.extend(self._find_grid_tables(text))

        # 3. Tab-separated tables
        tables.extend(self._find_tab_tables(text))

        # Remove overlaps (keep first found)
        tables = self._remove_overlapping(tables)

        # Sort by position
        tables.sort(key=lambda t: t.start_offset)

        # Try to find captions
        for table in tables:
            table.caption = self._find_caption(text, table.start_offset)

        logger.info(
            "TextTableExtractor: found %d tables in %d chars",
            len(tables), len(text),
        )

        return tables

    def has_tables(self, text: str) -> bool:
        """Quick check — any tables in text?"""
        if _MD_SEP.search(text):
            return True
        if _GRID_LINE.search(text):
            return True
        tab_rows = _TAB_ROW.findall(text)
        if len(tab_rows) >= self.min_rows:
            return True
        return False

    # -- Markdown tables -----------------------------------------------------

    def _find_markdown_tables(self, text: str) -> List[DetectedTable]:
        """Find markdown pipe tables."""
        tables = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            # Look for separator line
            if _MD_SEP.match(lines[i]):
                # Check for header row above
                header_start = i - 1 if i > 0 and _MD_ROW.match(lines[i - 1]) else i
                # Gather data rows below
                end = i + 1
                while end < len(lines) and _MD_ROW.match(lines[end]):
                    end += 1

                table_lines = lines[header_start:end]
                if len(table_lines) >= self.min_rows:
                    table = self._parse_markdown_table(
                        table_lines, text, header_start, lines,
                    )
                    if table and table.num_cols >= self.min_cols:
                        tables.append(table)
                i = end
            else:
                i += 1

        return tables

    def _parse_markdown_table(
        self,
        table_lines: List[str],
        full_text: str,
        first_line_idx: int,
        all_lines: List[str],
    ) -> Optional[DetectedTable]:
        """Parse a markdown table from its lines."""
        # Calculate offsets
        start_offset = sum(len(all_lines[j]) + 1 for j in range(first_line_idx))
        raw_text = '\n'.join(table_lines)
        end_offset = start_offset + len(raw_text)

        cells: List[TableCell] = []
        data_rows = []
        has_header = False

        for line_idx, line in enumerate(table_lines):
            # Skip separator lines
            if _MD_SEP.match(line):
                has_header = True
                continue

            # Parse cells
            stripped = line.strip()
            if stripped.startswith('|'):
                stripped = stripped[1:]
            if stripped.endswith('|'):
                stripped = stripped[:-1]

            parts = [p.strip() for p in stripped.split('|')]
            data_rows.append(parts)

        if not data_rows:
            return None

        num_cols = max(len(row) for row in data_rows)
        num_rows = len(data_rows)

        for row_idx, row in enumerate(data_rows):
            for col_idx, cell_text in enumerate(row):
                cells.append(TableCell(
                    content=cell_text,
                    row=row_idx,
                    col=col_idx,
                    is_header=(has_header and row_idx == 0),
                ))

        return DetectedTable(
            raw_text=raw_text,
            cells=cells,
            num_rows=num_rows,
            num_cols=num_cols,
            format=TableFormat.MARKDOWN,
            start_offset=start_offset,
            end_offset=end_offset,
            has_header=has_header,
        )

    # -- Grid tables ---------------------------------------------------------

    def _find_grid_tables(self, text: str) -> List[DetectedTable]:
        """Find grid-style tables (+---+---+)."""
        tables = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            if _GRID_LINE.match(lines[i]):
                start_idx = i
                end_idx = i + 1
                grid_rows = [i]

                while end_idx < len(lines):
                    if _GRID_LINE.match(lines[end_idx]):
                        grid_rows.append(end_idx)
                        end_idx += 1
                    elif lines[end_idx].strip().startswith('|'):
                        end_idx += 1
                    else:
                        break

                if len(grid_rows) >= 2:
                    table_lines = lines[start_idx:end_idx]
                    table = self._parse_grid_table(
                        table_lines, text, start_idx, lines,
                    )
                    if table and table.num_cols >= self.min_cols:
                        tables.append(table)
                    i = end_idx
                else:
                    i += 1
            else:
                i += 1

        return tables

    def _parse_grid_table(
        self,
        table_lines: List[str],
        full_text: str,
        first_line_idx: int,
        all_lines: List[str],
    ) -> Optional[DetectedTable]:
        """Parse a grid table."""
        start_offset = sum(len(all_lines[j]) + 1 for j in range(first_line_idx))
        raw_text = '\n'.join(table_lines)
        end_offset = start_offset + len(raw_text)

        cells: List[TableCell] = []
        data_rows = []

        for line in table_lines:
            if _GRID_LINE.match(line):
                continue
            stripped = line.strip()
            if stripped.startswith('|') and stripped.endswith('|'):
                parts = [p.strip() for p in stripped[1:-1].split('|')]
                data_rows.append(parts)

        if len(data_rows) < self.min_rows:
            return None

        num_cols = max(len(row) for row in data_rows)
        num_rows = len(data_rows)

        for row_idx, row in enumerate(data_rows):
            for col_idx, cell_text in enumerate(row):
                cells.append(TableCell(
                    content=cell_text,
                    row=row_idx,
                    col=col_idx,
                    is_header=(row_idx == 0),
                ))

        return DetectedTable(
            raw_text=raw_text,
            cells=cells,
            num_rows=num_rows,
            num_cols=num_cols,
            format=TableFormat.GRID,
            start_offset=start_offset,
            end_offset=end_offset,
            has_header=True,
        )

    # -- Tab-separated tables ------------------------------------------------

    def _find_tab_tables(self, text: str) -> List[DetectedTable]:
        """Find tab-separated tables."""
        tables = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            if '\t' in lines[i] and _TAB_ROW.match(lines[i]):
                start_idx = i
                end_idx = i + 1
                col_count = lines[i].count('\t') + 1

                while end_idx < len(lines):
                    if _TAB_ROW.match(lines[end_idx]):
                        row_cols = lines[end_idx].count('\t') + 1
                        if abs(row_cols - col_count) <= 1:
                            end_idx += 1
                        else:
                            break
                    else:
                        break

                num_rows = end_idx - start_idx
                if num_rows >= self.min_rows and col_count >= self.min_cols:
                    table_lines = lines[start_idx:end_idx]
                    table = self._parse_tab_table(
                        table_lines, text, start_idx, lines, col_count,
                    )
                    if table:
                        tables.append(table)
                    i = end_idx
                else:
                    i += 1
            else:
                i += 1

        return tables

    def _parse_tab_table(
        self,
        table_lines: List[str],
        full_text: str,
        first_line_idx: int,
        all_lines: List[str],
        col_count: int,
    ) -> Optional[DetectedTable]:
        """Parse a tab-separated table."""
        start_offset = sum(len(all_lines[j]) + 1 for j in range(first_line_idx))
        raw_text = '\n'.join(table_lines)
        end_offset = start_offset + len(raw_text)

        cells: List[TableCell] = []
        for row_idx, line in enumerate(table_lines):
            parts = line.split('\t')
            for col_idx, cell_text in enumerate(parts):
                cells.append(TableCell(
                    content=cell_text.strip(),
                    row=row_idx,
                    col=col_idx,
                    is_header=(row_idx == 0),
                ))

        return DetectedTable(
            raw_text=raw_text,
            cells=cells,
            num_rows=len(table_lines),
            num_cols=col_count,
            format=TableFormat.TAB_SEPARATED,
            start_offset=start_offset,
            end_offset=end_offset,
            has_header=True,
        )

    # -- Helpers -------------------------------------------------------------

    def _remove_overlapping(
        self, tables: List[DetectedTable],
    ) -> List[DetectedTable]:
        """Remove overlapping table detections."""
        if not tables:
            return []

        tables.sort(key=lambda t: t.start_offset)
        result = [tables[0]]

        for table in tables[1:]:
            if table.start_offset >= result[-1].end_offset:
                result.append(table)

        return result

    def _find_caption(self, text: str, table_start: int) -> Optional[str]:
        """Look for table caption near the table."""
        # Search in the 200 chars before the table
        search_start = max(0, table_start - 200)
        search_text = text[search_start:table_start]

        match = _TABLE_CAPTION.search(search_text)
        if match:
            return match.group(1).strip()
        return None
