"""
Unit tests for api/services/layout_analyzer.py — LayoutAnalyzer.

Target: comprehensive coverage of the orchestrator that combines
table + formula + heading + list + code + image detection into LayoutDNA.
"""

import pytest

from api.services.layout_analyzer import LayoutAnalyzer
from api.services.layout_dna import LayoutDNA, RegionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_doc():
    return (
        "# Introduction\n\n"
        "This is the first paragraph of the document.\n\n"
        "This is the second paragraph.\n\n"
        "## Methods\n\n"
        "We used a special method."
    )


def _doc_with_table():
    return (
        "# Results\n\n"
        "The results are shown below.\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| Acc    | 95%   |\n"
        "| F1     | 0.92  |\n\n"
        "As we can see, the results are good."
    )


def _doc_with_formula():
    return (
        "# Theory\n\n"
        "Given the equation $$E = mc^2$$ we can derive:\n\n"
        "The relationship holds."
    )


def _doc_with_code():
    return (
        "# Code Example\n\n"
        "Here is some code:\n\n"
        "```python\n"
        "def hello():\n"
        "    print('hello')\n"
        "```\n\n"
        "That was the code."
    )


def _doc_with_list():
    return (
        "# Steps\n\n"
        "Follow these steps:\n\n"
        "- Step one\n"
        "- Step two\n"
        "- Step three\n\n"
        "That covers it."
    )


# ---------------------------------------------------------------------------
# Basic
# ---------------------------------------------------------------------------

class TestBasic:
    def test_empty_text(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("")
        assert dna.region_count == 0

    def test_whitespace_only(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("   \n\t  ")
        assert dna.region_count == 0

    def test_simple_text(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("Just a plain paragraph.")
        assert dna.region_count >= 1
        assert any(r.type == RegionType.TEXT for r in dna.regions)

    def test_returns_layout_dna(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("Some text.")
        assert isinstance(dna, LayoutDNA)

    def test_metadata_passed_through(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("Text.", metadata={"source": "test"})
        assert dna.metadata["source"] == "test"


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

class TestHeadings:
    def test_markdown_heading(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("# Title\n\nSome text.")
        headings = dna.headings
        assert len(headings) >= 1
        assert headings[0].content == "Title"
        assert headings[0].level == 1

    def test_multiple_heading_levels(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("# H1\n\nText.\n\n## H2\n\nMore text.\n\n### H3\n\nEnd.")
        headings = dna.headings
        assert len(headings) >= 3
        levels = [h.level for h in headings]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels

    def test_heading_and_text_separated(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_simple_doc())
        headings = dna.headings
        texts = dna.regions_of_type(RegionType.TEXT)
        assert len(headings) >= 2
        assert len(texts) >= 1


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class TestTables:
    def test_table_detected(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_table())
        assert dna.has_tables is True
        assert len(dna.tables) == 1

    def test_table_metadata(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_table())
        table = dna.tables[0]
        assert table.metadata.get("format") == "markdown"
        assert table.metadata.get("cols") == 2

    def test_surrounding_text_preserved(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_table())
        texts = dna.regions_of_type(RegionType.TEXT)
        assert len(texts) >= 1

    def test_table_disabled(self):
        analyzer = LayoutAnalyzer(detect_tables=False)
        dna = analyzer.analyze(_doc_with_table())
        assert dna.has_tables is False


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------

class TestFormulas:
    def test_display_formula_detected(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_formula())
        assert dna.has_formulas is True
        assert len(dna.formulas) >= 1

    def test_formula_metadata(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_formula())
        formula = dna.formulas[0]
        assert formula.metadata.get("mode") == "display"

    def test_inline_formula_stays_in_text(self):
        """Inline formulas should not be extracted as separate regions."""
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("Given $x^2$ we compute things.")
        # Should be TEXT region containing the inline formula
        assert dna.has_formulas is False
        texts = dna.regions_of_type(RegionType.TEXT)
        assert any("$x^2$" in t.content for t in texts)

    def test_formula_disabled(self):
        analyzer = LayoutAnalyzer(detect_formulas=False)
        dna = analyzer.analyze(_doc_with_formula())
        assert dna.has_formulas is False


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

class TestCodeBlocks:
    def test_code_detected(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_code())
        assert dna.has_code is True
        code_blocks = dna.code_blocks
        assert len(code_blocks) == 1
        assert "print" in code_blocks[0].content

    def test_code_language_metadata(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_code())
        code = dna.code_blocks[0]
        assert code.metadata.get("language") == "python"

    def test_code_no_language(self):
        text = "```\nsome code\n```"
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(text)
        code_blocks = dna.code_blocks
        assert len(code_blocks) == 1
        assert code_blocks[0].metadata.get("language", "") == ""

    def test_code_disabled(self):
        analyzer = LayoutAnalyzer(detect_code=False)
        dna = analyzer.analyze(_doc_with_code())
        assert dna.has_code is False


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class TestLists:
    def test_list_detected(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_list())
        lists = dna.regions_of_type(RegionType.LIST)
        assert len(lists) >= 1
        assert "Step one" in lists[0].content

    def test_list_disabled(self):
        analyzer = LayoutAnalyzer(detect_lists=False)
        dna = analyzer.analyze(_doc_with_list())
        lists = dna.regions_of_type(RegionType.LIST)
        assert len(lists) == 0


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

class TestImages:
    def test_markdown_image(self):
        text = "Text before.\n\n![diagram](img.png)\n\nText after."
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(text)
        images = dna.regions_of_type(RegionType.IMAGE)
        assert len(images) == 1
        assert images[0].metadata.get("alt_text") == "diagram"

    def test_image_placeholder(self):
        text = "Text before.\n\n[IMAGE: architecture diagram]\n\nText after."
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(text)
        images = dna.regions_of_type(RegionType.IMAGE)
        assert len(images) == 1
        assert "architecture diagram" in images[0].metadata.get("alt_text", "")

    def test_image_disabled(self):
        analyzer = LayoutAnalyzer(detect_images=False)
        dna = analyzer.analyze("![img](url)")
        images = dna.regions_of_type(RegionType.IMAGE)
        assert len(images) == 0


# ---------------------------------------------------------------------------
# Full document
# ---------------------------------------------------------------------------

class TestFullDocument:
    def test_complex_document(self):
        text = (
            "# Introduction\n\n"
            "This is the introduction with $x^2$ inline math.\n\n"
            "## Data\n\n"
            "| Name | Value |\n|------|-------|\n| A | 1 |\n| B | 2 |\n\n"
            "The equation is:\n\n"
            "$$E = mc^2$$\n\n"
            "## Code\n\n"
            "```python\nprint('hello')\n```\n\n"
            "Steps:\n\n"
            "- Step 1\n"
            "- Step 2\n\n"
            "End."
        )
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(text)

        assert dna.has_tables is True
        assert dna.has_formulas is True
        assert dna.has_code is True
        assert len(dna.headings) >= 2
        assert dna.region_count >= 5

    def test_full_text_covers_all_content(self):
        """full_text should contain content from all region types."""
        text = "# Title\n\nParagraph.\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(text)
        ft = dna.full_text
        assert "Title" in ft
        assert "Paragraph" in ft

    def test_regions_sorted_by_position(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_simple_doc())
        offsets = [r.start_offset for r in dna.regions]
        assert offsets == sorted(offsets)

    def test_serialization_roundtrip(self):
        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze(_doc_with_table())
        restored = LayoutDNA.from_json(dna.to_json())
        assert restored.region_count == dna.region_count
        assert restored.has_tables == dna.has_tables
