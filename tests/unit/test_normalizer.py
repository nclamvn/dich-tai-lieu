"""Tests for core/docx_engine/normalizer.py — DocumentNormalizer markdown parsing."""

import json
import pytest
from pathlib import Path

from core.docx_engine.normalizer import DocumentNormalizer
from core.docx_engine.models import (
    BlockType, ContentBlock, DocumentMeta, NormalizedDocument,
    Chapter, TextRun, InlineStyle, ListType, TableData,
)


@pytest.fixture
def normalizer():
    return DocumentNormalizer()


# ==================== from_markdown ====================


class TestFromMarkdown:
    """from_markdown() creates NormalizedDocument from markdown string."""

    def test_basic_markdown(self, normalizer):
        md = "# Title\n\nSome paragraph text."
        doc = normalizer.from_markdown(md)
        assert isinstance(doc, NormalizedDocument)
        assert doc.meta.title == "Untitled"
        assert len(doc.chapters) == 1

    def test_with_custom_meta(self, normalizer):
        meta = DocumentMeta(title="Custom Title", author="Test Author")
        doc = normalizer.from_markdown("# Heading\n\nContent", meta)
        assert doc.meta.title == "Custom Title"
        assert doc.meta.author == "Test Author"

    def test_toc_generated(self, normalizer):
        md = "## Section 1\n\nContent\n\n## Section 2\n\nMore"
        doc = normalizer.from_markdown(md)
        assert doc.toc is not None
        assert len(doc.toc.items) >= 1


# ==================== Heading Parsing ====================


class TestHeadingParsing:
    """_parse_heading and heading detection."""

    def test_h1(self, normalizer):
        blocks = normalizer._parse_markdown("# Title")
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].level == 1
        assert blocks[0].content == "Title"

    def test_h2(self, normalizer):
        blocks = normalizer._parse_markdown("## Section")
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].level == 2

    def test_h3(self, normalizer):
        blocks = normalizer._parse_markdown("### Subsection")
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].level == 3

    def test_h6(self, normalizer):
        blocks = normalizer._parse_markdown("###### Deep heading")
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].level == 6

    def test_heading_with_special_chars(self, normalizer):
        blocks = normalizer._parse_markdown("## Section: Important (2024)")
        assert blocks[0].content == "Section: Important (2024)"


# ==================== Paragraph Parsing ====================


class TestParagraphParsing:
    """_parse_paragraph extracts text runs."""

    def test_simple_paragraph(self, normalizer):
        blocks = normalizer._parse_markdown("This is a paragraph.")
        assert blocks[0].type == BlockType.PARAGRAPH
        runs = blocks[0].content
        assert isinstance(runs, list)
        assert runs[0].text == "This is a paragraph."

    def test_multiline_paragraph(self, normalizer):
        blocks = normalizer._parse_markdown("Line one\nLine two")
        assert blocks[0].type == BlockType.PARAGRAPH
        text = " ".join(r.text for r in blocks[0].content)
        assert "Line one" in text
        assert "Line two" in text

    def test_two_paragraphs(self, normalizer):
        blocks = normalizer._parse_markdown("Para one.\n\nPara two.")
        paras = [b for b in blocks if b.type == BlockType.PARAGRAPH]
        assert len(paras) == 2


# ==================== Inline Formatting ====================


class TestInlineFormatting:
    """_parse_inline bold, italic, code, strikethrough."""

    def test_bold(self, normalizer):
        runs = normalizer._parse_inline("Hello **world**")
        bold_runs = [r for r in runs if r.style.bold]
        assert len(bold_runs) == 1
        assert bold_runs[0].text == "world"

    def test_italic(self, normalizer):
        runs = normalizer._parse_inline("Hello *world*")
        italic_runs = [r for r in runs if r.style.italic]
        assert len(italic_runs) == 1
        assert italic_runs[0].text == "world"

    def test_bold_italic(self, normalizer):
        runs = normalizer._parse_inline("***bold italic***")
        bi_runs = [r for r in runs if r.style.bold and r.style.italic]
        assert len(bi_runs) == 1

    def test_inline_code(self, normalizer):
        runs = normalizer._parse_inline("Use `print()` function")
        code_runs = [r for r in runs if r.style.code]
        assert len(code_runs) == 1
        assert code_runs[0].text == "print()"

    def test_strikethrough(self, normalizer):
        runs = normalizer._parse_inline("~~deleted~~")
        strike_runs = [r for r in runs if r.style.strikethrough]
        assert len(strike_runs) == 1
        assert strike_runs[0].text == "deleted"

    def test_plain_text(self, normalizer):
        runs = normalizer._parse_inline("No formatting here")
        assert len(runs) == 1
        assert runs[0].text == "No formatting here"
        assert not runs[0].style.bold
        assert not runs[0].style.italic

    def test_mixed_formatting(self, normalizer):
        runs = normalizer._parse_inline("Normal **bold** and *italic*")
        assert len(runs) >= 3
        texts = [r.text for r in runs]
        assert "bold" in texts
        assert "italic" in texts

    def test_underscore_bold(self, normalizer):
        runs = normalizer._parse_inline("__bold__")
        bold_runs = [r for r in runs if r.style.bold]
        assert len(bold_runs) == 1


# ==================== Code Block Parsing ====================


class TestCodeBlockParsing:
    """_parse_code_block fenced code."""

    def test_code_block(self, normalizer):
        md = "```python\nprint('hello')\n```"
        blocks = normalizer._parse_markdown(md)
        code_blocks = [b for b in blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert "print" in code_blocks[0].content
        assert code_blocks[0].style_hints.get("language") == "python"

    def test_code_block_no_language(self, normalizer):
        md = "```\nsome code\n```"
        blocks = normalizer._parse_markdown(md)
        code_blocks = [b for b in blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert code_blocks[0].style_hints.get("language") == ""

    def test_multiline_code_block(self, normalizer):
        md = "```js\nconst x = 1;\nconst y = 2;\nreturn x + y;\n```"
        blocks = normalizer._parse_markdown(md)
        code_blocks = [b for b in blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert "\n" in code_blocks[0].content


# ==================== Blockquote Parsing ====================


class TestBlockquoteParsing:
    """_parse_blockquote."""

    def test_simple_quote(self, normalizer):
        md = "> This is a quote."
        blocks = normalizer._parse_markdown(md)
        assert blocks[0].type == BlockType.QUOTE
        assert "This is a quote." in blocks[0].content

    def test_multiline_quote(self, normalizer):
        md = "> Line one\n> Line two"
        blocks = normalizer._parse_markdown(md)
        assert blocks[0].type == BlockType.QUOTE
        assert "Line one" in blocks[0].content
        assert "Line two" in blocks[0].content


# ==================== List Parsing ====================


class TestListParsing:
    """_parse_list bullet and numbered lists."""

    def test_bullet_list(self, normalizer):
        md = "- Item 1\n- Item 2\n- Item 3"
        blocks = normalizer._parse_markdown(md)
        list_blocks = [b for b in blocks if b.type == BlockType.LIST]
        assert len(list_blocks) == 1
        assert list_blocks[0].style_hints["list_type"] == "bullet"

    def test_numbered_list(self, normalizer):
        md = "1. First\n2. Second\n3. Third"
        blocks = normalizer._parse_markdown(md)
        list_blocks = [b for b in blocks if b.type == BlockType.LIST]
        assert len(list_blocks) == 1
        assert list_blocks[0].style_hints["list_type"] == "numbered"

    def test_list_items_content(self, normalizer):
        md = "- Apple\n- Banana"
        blocks = normalizer._parse_markdown(md)
        list_block = [b for b in blocks if b.type == BlockType.LIST][0]
        items = list_block.content
        assert len(items) == 2
        assert items[0].content[0].text == "Apple"


# ==================== Table Parsing ====================


class TestTableParsing:
    """_parse_table markdown tables."""

    def test_simple_table(self, normalizer):
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |"
        blocks = normalizer._parse_markdown(md)
        table_blocks = [b for b in blocks if b.type == BlockType.TABLE]
        assert len(table_blocks) == 1
        table = table_blocks[0].content
        assert isinstance(table, TableData)
        assert table.has_header_row is True
        assert len(table.rows) == 3  # header + 2 data rows

    def test_table_header_cells(self, normalizer):
        md = "| H1 | H2 |\n| --- | --- |\n| D1 | D2 |"
        blocks = normalizer._parse_markdown(md)
        table = [b for b in blocks if b.type == BlockType.TABLE][0].content
        # First row should be header
        assert table.rows[0][0].is_header is True
        # Second row should not be header
        assert table.rows[1][0].is_header is False


# ==================== from_agent2_output ====================


class TestFromAgent2Output:
    """from_agent2_output() reads folder structure."""

    def test_missing_folder_raises(self, normalizer):
        with pytest.raises(FileNotFoundError):
            normalizer.from_agent2_output("/nonexistent/path")

    def test_missing_manifest_raises(self, normalizer, tmp_path):
        with pytest.raises(FileNotFoundError, match="manifest.json"):
            normalizer.from_agent2_output(str(tmp_path))

    def test_valid_folder(self, normalizer, tmp_path):
        # Create minimal agent2 output
        manifest = {
            "metadata": {"title": "Test Book", "author": "Author"},
            "dna": {"genre": "novel"},
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "001_intro.md").write_text("# Introduction\n\nHello world.")

        doc = normalizer.from_agent2_output(str(tmp_path))
        assert doc.meta.title == "Test Book"
        assert len(doc.chapters) == 1
        assert doc.chapters[0].title == "Introduction"


# ==================== Glossary Reading ====================


class TestGlossaryReading:
    """_read_glossary from JSON file."""

    def test_read_glossary_list_format(self, normalizer, tmp_path):
        glossary_data = [
            {"term": "API", "definition": "Application Programming Interface"},
            {"term": "REST", "definition": "Representational State Transfer"},
        ]
        path = tmp_path / "glossary.json"
        path.write_text(json.dumps(glossary_data))

        glossary = normalizer._read_glossary(path)
        assert len(glossary.items) == 2
        assert glossary.items[0].term == "API"

    def test_read_glossary_dict_format(self, normalizer, tmp_path):
        glossary_data = {
            "title": "Thuật ngữ",
            "items": [{"term": "AI", "definition": "Trí tuệ nhân tạo"}],
        }
        path = tmp_path / "glossary.json"
        path.write_text(json.dumps(glossary_data))

        glossary = normalizer._read_glossary(path)
        assert glossary.title == "Thuật ngữ"
        assert len(glossary.items) == 1


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Edge cases and unusual input."""

    def test_empty_markdown(self, normalizer):
        doc = normalizer.from_markdown("")
        assert len(doc.chapters) == 1
        assert len(doc.chapters[0].content) == 0

    def test_only_headings(self, normalizer):
        md = "# H1\n\n## H2\n\n### H3"
        blocks = normalizer._parse_markdown(md)
        headings = [b for b in blocks if b.type == BlockType.HEADING]
        assert len(headings) == 3

    def test_mixed_content(self, normalizer):
        md = """# Title

Some text.

## Section

- Item 1
- Item 2

> A quote

```python
code()
```

| A | B |
| --- | --- |
| 1 | 2 |
"""
        blocks = normalizer._parse_markdown(md)
        types = {b.type for b in blocks}
        assert BlockType.HEADING in types
        assert BlockType.PARAGRAPH in types
        assert BlockType.LIST in types
        assert BlockType.QUOTE in types
        assert BlockType.CODE in types
        assert BlockType.TABLE in types
