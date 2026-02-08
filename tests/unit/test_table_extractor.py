"""
Unit tests for api/services/table_extractor.py — TextTableExtractor.

Target: comprehensive coverage of markdown, grid, tab-separated detection.
"""

import pytest

from api.services.table_extractor import (
    TextTableExtractor,
    DetectedTable,
    TableCell,
    TableFormat,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md_table(rows=3, cols=3, header=True):
    """Generate a markdown table string."""
    headers = " | ".join(f"Col{c}" for c in range(cols))
    sep = " | ".join("---" for _ in range(cols))
    data = []
    for r in range(rows):
        data.append(" | ".join(f"R{r}C{c}" for c in range(cols)))
    lines = [f"| {headers} |", f"| {sep} |"]
    for d in data:
        lines.append(f"| {d} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown tables
# ---------------------------------------------------------------------------

class TestMarkdownTables:
    def test_simple_table(self):
        text = _md_table(rows=2, cols=2)
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        t = tables[0]
        assert t.format == TableFormat.MARKDOWN
        assert t.num_cols == 2
        assert t.num_rows >= 2
        assert t.has_header is True

    def test_3x3_table(self):
        text = _md_table(rows=3, cols=3)
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].num_cols == 3

    def test_table_with_surrounding_text(self):
        text = (
            "Some text before.\n\n"
            + _md_table(rows=2, cols=2)
            + "\n\nSome text after."
        )
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1

    def test_two_tables(self):
        text = (
            _md_table(rows=2, cols=2)
            + "\n\nMiddle text.\n\n"
            + _md_table(rows=2, cols=3)
        )
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 2
        assert tables[0].num_cols == 2
        assert tables[1].num_cols == 3

    def test_cell_content_parsed(self):
        text = "| Name | Age |\n|---|---|\n| Alice | 30 |\n| Bob | 25 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        t = tables[0]
        cell = t.get_cell(0, 0)
        assert cell is not None
        assert cell.content == "Name"
        assert cell.is_header is True

    def test_get_row(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        row = tables[0].get_row(0)
        assert len(row) == 2

    def test_get_cell_not_found(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert tables[0].get_cell(99, 99) is None

    def test_no_table(self):
        text = "Just some text without any table."
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 0

    def test_empty_text(self):
        ext = TextTableExtractor()
        assert ext.extract("") == []
        assert ext.extract("   ") == []

    def test_single_column_rejected(self):
        """Single column table should be rejected (min_cols=2)."""
        text = "| Col1 |\n|---|\n| Val1 |\n| Val2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 0

    def test_to_dict(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        d = tables[0].to_dict()
        assert d["format"] == "markdown"
        assert d["num_rows"] >= 2
        assert d["num_cols"] == 2
        assert "cells" in d


# ---------------------------------------------------------------------------
# Grid tables
# ---------------------------------------------------------------------------

class TestGridTables:
    def test_simple_grid(self):
        text = (
            "+-----+-----+\n"
            "| A   | B   |\n"
            "+-----+-----+\n"
            "| 1   | 2   |\n"
            "+-----+-----+\n"
        )
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].format == TableFormat.GRID
        assert tables[0].num_cols == 2

    def test_grid_with_multiple_rows(self):
        text = (
            "+---+---+---+\n"
            "| A | B | C |\n"
            "+---+---+---+\n"
            "| 1 | 2 | 3 |\n"
            "| 4 | 5 | 6 |\n"
            "+---+---+---+\n"
        )
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].num_rows == 3
        assert tables[0].num_cols == 3


# ---------------------------------------------------------------------------
# Tab-separated tables
# ---------------------------------------------------------------------------

class TestTabTables:
    def test_simple_tab_table(self):
        text = "Name\tAge\tCity\nAlice\t30\tNYC\nBob\t25\tLA"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].format == TableFormat.TAB_SEPARATED
        assert tables[0].num_cols == 3
        assert tables[0].num_rows == 3

    def test_tab_table_too_few_rows(self):
        text = "Name\tAge\tCity"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 0  # Only 1 row

    def test_tab_single_column_rejected(self):
        text = "col1\ncol2\ncol3"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 0


# ---------------------------------------------------------------------------
# has_tables
# ---------------------------------------------------------------------------

class TestHasTables:
    def test_has_markdown_table(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        assert ext.has_tables(text) is True

    def test_has_grid_table(self):
        text = "+---+---+\n| A | B |\n+---+---+"
        ext = TextTableExtractor()
        assert ext.has_tables(text) is True

    def test_has_tab_table(self):
        text = "A\tB\n1\t2\n3\t4"
        ext = TextTableExtractor()
        assert ext.has_tables(text) is True

    def test_no_tables(self):
        text = "Just plain text."
        ext = TextTableExtractor()
        assert ext.has_tables(text) is False


# ---------------------------------------------------------------------------
# Caption detection
# ---------------------------------------------------------------------------

class TestCaptions:
    def test_caption_before_table(self):
        text = "Table 1: Revenue data\n\n| Year | Revenue |\n|---|---|\n| 2024 | 100 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].caption is not None
        assert "Revenue" in tables[0].caption

    def test_vietnamese_caption(self):
        text = "Bảng 1: Dữ liệu\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].caption is not None

    def test_no_caption(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1
        assert tables[0].caption is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_overlapping_tables_resolved(self):
        """Same region shouldn't produce multiple table detections."""
        text = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        ext = TextTableExtractor()
        tables = ext.extract(text)
        assert len(tables) == 1

    def test_custom_min_rows(self):
        ext = TextTableExtractor(min_rows=5)
        text = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        tables = ext.extract(text)
        assert len(tables) == 0  # Only 3 rows

    def test_custom_min_cols(self):
        ext = TextTableExtractor(min_cols=4)
        text = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |"
        tables = ext.extract(text)
        assert len(tables) == 0  # Only 3 cols
