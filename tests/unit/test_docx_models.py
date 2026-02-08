"""Tests for core/docx_engine/models.py — Dataclass models for DOCX engine."""

import pytest
from core.docx_engine.models import (
    BlockType, ListType, InlineStyle, TextRun, ContentBlock,
    ListItem, TableCell, TableData, Footnote,
    Chapter, FrontMatterItem, FrontMatter,
    TocItem, TableOfContents, GlossaryItem, Glossary,
    BibliographyItem, Bibliography, Appendix,
    DocumentDNA, DocumentMeta, NormalizedDocument,
)


# ==================== Enums ====================


class TestEnums:
    """BlockType and ListType enum values."""

    def test_block_types(self):
        expected = {"heading", "paragraph", "list", "table", "figure",
                    "quote", "code", "footnote", "page_break"}
        actual = {bt.value for bt in BlockType}
        assert expected == actual

    def test_list_types(self):
        assert ListType.BULLET.value == "bullet"
        assert ListType.NUMBERED.value == "numbered"


# ==================== InlineStyle ====================


class TestInlineStyle:
    """InlineStyle defaults and creation."""

    def test_defaults(self):
        s = InlineStyle()
        assert s.bold is False
        assert s.italic is False
        assert s.underline is False
        assert s.strikethrough is False
        assert s.superscript is False
        assert s.subscript is False
        assert s.code is False

    def test_bold_italic(self):
        s = InlineStyle(bold=True, italic=True)
        assert s.bold is True
        assert s.italic is True
        assert s.code is False


# ==================== TextRun ====================


class TestTextRun:
    """TextRun creation and default style."""

    def test_plain_text(self):
        run = TextRun(text="Hello")
        assert run.text == "Hello"
        assert run.style.bold is False

    def test_styled_text(self):
        run = TextRun(text="Important", style=InlineStyle(bold=True))
        assert run.style.bold is True

    def test_default_style_is_independent(self):
        r1 = TextRun(text="A")
        r2 = TextRun(text="B")
        r1.style.bold = True
        assert r2.style.bold is False


# ==================== ContentBlock ====================


class TestContentBlock:
    """ContentBlock creation and fields."""

    def test_heading_block(self):
        block = ContentBlock(type=BlockType.HEADING, level=2, content="Section Title")
        assert block.type == BlockType.HEADING
        assert block.level == 2
        assert block.content == "Section Title"

    def test_paragraph_block(self):
        runs = [TextRun(text="Hello")]
        block = ContentBlock(type=BlockType.PARAGRAPH, content=runs)
        assert block.type == BlockType.PARAGRAPH
        assert len(block.content) == 1

    def test_default_style_hints(self):
        block = ContentBlock(type=BlockType.CODE)
        assert block.style_hints == {}

    def test_optional_fields(self):
        block = ContentBlock(type=BlockType.TABLE, id="tbl-1", caption="Table 1")
        assert block.id == "tbl-1"
        assert block.caption == "Table 1"


# ==================== ListItem ====================


class TestListItem:
    """ListItem with content and children."""

    def test_simple_item(self):
        item = ListItem(content=[TextRun(text="Item text")])
        assert item.content[0].text == "Item text"
        assert item.children == []

    def test_nested_item(self):
        child = ListItem(content=[TextRun(text="Child")])
        parent = ListItem(content=[TextRun(text="Parent")], children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].content[0].text == "Child"


# ==================== Table Models ====================


class TestTableModels:
    """TableCell and TableData."""

    def test_table_cell_defaults(self):
        cell = TableCell(content=[TextRun(text="Data")])
        assert cell.colspan == 1
        assert cell.rowspan == 1
        assert cell.is_header is False

    def test_header_cell(self):
        cell = TableCell(content=[TextRun(text="Header")], is_header=True)
        assert cell.is_header is True

    def test_table_data(self):
        header = [TableCell(content=[TextRun(text="Name")], is_header=True)]
        row1 = [TableCell(content=[TextRun(text="Alice")])]
        table = TableData(rows=[header, row1])
        assert table.has_header_row is True
        assert len(table.rows) == 2


# ==================== Chapter ====================


class TestChapter:
    """Chapter model."""

    def test_basic_chapter(self):
        ch = Chapter(number=1, title="Introduction", content=[])
        assert ch.number == 1
        assert ch.title == "Introduction"
        assert ch.subtitle is None
        assert ch.epigraph is None
        assert ch.footnotes == []

    def test_chapter_with_optional_fields(self):
        ch = Chapter(
            number=3, title="Methods",
            content=[], subtitle="Research Methods",
            epigraph="Science is organized knowledge.",
        )
        assert ch.subtitle == "Research Methods"
        assert ch.epigraph is not None


# ==================== FrontMatter ====================


class TestFrontMatter:
    """FrontMatter and FrontMatterItem."""

    def test_empty_front_matter(self):
        fm = FrontMatter()
        assert fm.items == []

    def test_with_items(self):
        item = FrontMatterItem(type="dedication", title="Dedication", content=[])
        fm = FrontMatter(items=[item])
        assert len(fm.items) == 1
        assert fm.items[0].type == "dedication"


# ==================== TableOfContents ====================


class TestTableOfContents:
    """TOC model."""

    def test_defaults(self):
        toc = TableOfContents()
        assert toc.title == "Table of Contents"
        assert toc.items == []
        assert toc.auto_generate is True

    def test_with_items(self):
        items = [
            TocItem(title="Chapter 1", level=1, chapter_number=1),
            TocItem(title="Section 1.1", level=2),
        ]
        toc = TableOfContents(items=items)
        assert len(toc.items) == 2
        assert toc.items[0].chapter_number == 1
        assert toc.items[1].page_number is None


# ==================== Glossary ====================


class TestGlossary:
    """Glossary model."""

    def test_defaults(self):
        g = Glossary()
        assert g.title == "Glossary"
        assert g.items == []

    def test_with_items(self):
        item = GlossaryItem(term="API", definition="Application Programming Interface", source_term="API")
        g = Glossary(items=[item])
        assert g.items[0].term == "API"
        assert g.items[0].source_term == "API"


# ==================== Bibliography ====================


class TestBibliography:
    """Bibliography model."""

    def test_defaults(self):
        b = Bibliography()
        assert b.title == "References"
        assert b.items == []

    def test_with_items(self):
        item = BibliographyItem(id="ref1", formatted="Author (2024). Title.", type="article")
        b = Bibliography(items=[item])
        assert b.items[0].id == "ref1"
        assert b.items[0].type == "article"


# ==================== DocumentDNA (docx_engine version) ====================


class TestDocxDocumentDNA:
    """DocumentDNA from docx_engine models."""

    def test_defaults(self):
        dna = DocumentDNA()
        assert dna.genre == "general"
        assert dna.tone == "neutral"
        assert dna.has_formulas is False
        assert dna.has_code is False
        assert dna.has_tables is False
        assert dna.source_language == "en"
        assert dna.target_language == "vi"
        assert dna.characters == []
        assert dna.key_terms == {}


# ==================== DocumentMeta ====================


class TestDocumentMeta:
    """DocumentMeta model."""

    def test_required_title(self):
        meta = DocumentMeta(title="Test")
        assert meta.title == "Test"
        assert meta.author == "Unknown"
        assert meta.language == "vi"

    def test_all_fields(self):
        meta = DocumentMeta(
            title="Book", subtitle="Subtitle", author="Author",
            translator="Translator", publisher="Publisher",
            date="2024-01-01", language="en", isbn="1234567890",
            running_title="Book",
        )
        assert meta.subtitle == "Subtitle"
        assert meta.translator == "Translator"
        assert meta.isbn == "1234567890"
        assert meta.running_title == "Book"

    def test_optional_fields_default_none(self):
        meta = DocumentMeta(title="T")
        assert meta.subtitle is None
        assert meta.translator is None
        assert meta.publisher is None
        assert meta.isbn is None


# ==================== NormalizedDocument ====================


class TestNormalizedDocument:
    """NormalizedDocument assembly."""

    def _make_doc(self, chapters=None):
        meta = DocumentMeta(title="Test Doc")
        dna = DocumentDNA()
        return NormalizedDocument(
            meta=meta,
            dna=dna,
            chapters=chapters or [],
        )

    def test_basic_creation(self):
        doc = self._make_doc()
        assert doc.meta.title == "Test Doc"
        assert doc.total_chapters() == 0
        assert doc.glossary is None
        assert doc.bibliography is None

    def test_total_chapters(self):
        ch1 = Chapter(number=1, title="Ch1", content=[])
        ch2 = Chapter(number=2, title="Ch2", content=[])
        doc = self._make_doc(chapters=[ch1, ch2])
        assert doc.total_chapters() == 2

    def test_all_headings(self):
        blocks = [
            ContentBlock(type=BlockType.HEADING, level=1, content="Section 1"),
            ContentBlock(type=BlockType.HEADING, level=2, content="Subsection 1.1"),
        ]
        ch = Chapter(number=1, title="Chapter 1", content=blocks)
        doc = self._make_doc(chapters=[ch])

        headings = doc.all_headings()
        assert len(headings) >= 3  # chapter title + 2 headings
        assert headings[0].title == "Chapter 1"
        assert headings[0].level == 1

    def test_default_front_matter(self):
        doc = self._make_doc()
        assert isinstance(doc.front_matter, FrontMatter)
        assert doc.front_matter.items == []

    def test_appendices_default_empty(self):
        doc = self._make_doc()
        assert doc.appendices == []
