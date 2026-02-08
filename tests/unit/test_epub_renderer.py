"""
Unit tests for api/services/epub_renderer.py — EpubRenderer.

Target: 90%+ coverage.
"""

import zipfile
import pytest

from api.services.epub_renderer import EpubRenderer, is_available
from api.services.layout_dna import LayoutDNA, Region, RegionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_dna(text="Hello world."):
    """LayoutDNA with single TEXT region."""
    dna = LayoutDNA()
    dna.add_region(RegionType.TEXT, text)
    return dna


def _chapter_dna():
    """LayoutDNA with 2 chapters (H1 headings)."""
    dna = LayoutDNA()
    dna.add_region(RegionType.HEADING, "Chapter 1", level=1)
    dna.add_region(RegionType.TEXT, "Content of chapter 1.")
    dna.add_region(RegionType.HEADING, "Chapter 2", level=1)
    dna.add_region(RegionType.TEXT, "Content of chapter 2.")
    return dna


def _full_dna():
    """LayoutDNA with all region types."""
    dna = LayoutDNA()
    dna.add_region(RegionType.HEADING, "Title", level=1)
    dna.add_region(RegionType.TEXT, "Introduction paragraph.")
    dna.add_region(
        RegionType.TABLE,
        "| A | B |\n|---|---|\n| 1 | 2 |",
        metadata={"format": "markdown", "caption": "Table 1"},
    )
    dna.add_region(
        RegionType.FORMULA, "$$E=mc^2$$",
        metadata={"mode": "display"},
    )
    dna.add_region(
        RegionType.FORMULA, "$x^2$",
        metadata={"mode": "inline"},
    )
    dna.add_region(RegionType.LIST, "- Item 1\n- Item 2\n- Item 3")
    dna.add_region(
        RegionType.IMAGE, "![diagram](img.png)",
        metadata={"alt_text": "Architecture diagram"},
    )
    dna.add_region(
        RegionType.CODE, "def hello():\n    print('hi')",
        metadata={"language": "python"},
    )
    return dna


def _read_epub_file(path, filename):
    """Read a file from inside an EPUB."""
    with zipfile.ZipFile(path) as z:
        # EPUB files are in EPUB/ subdirectory
        try:
            return z.read(f"EPUB/{filename}").decode("utf-8")
        except KeyError:
            # Try without EPUB prefix
            return z.read(filename).decode("utf-8")


# ---------------------------------------------------------------------------
# Init / availability
# ---------------------------------------------------------------------------

class TestInit:
    def test_is_available(self):
        assert is_available() is True

    def test_init_succeeds(self):
        renderer = EpubRenderer()
        assert renderer is not None


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

class TestRenderBasic:
    def test_empty_dna(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            LayoutDNA(), str(tmp_path / "empty.epub"), title="Empty",
        )
        assert (tmp_path / "empty.epub").exists()

    def test_text_only(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "text.epub"), title="Text",
        )
        assert (tmp_path / "text.epub").exists()

    def test_output_is_zip(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        assert zipfile.is_zipfile(path)

    def test_epub_has_mimetype(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        with zipfile.ZipFile(path) as z:
            assert "mimetype" in z.namelist()

    def test_epub_has_css(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            assert any("main.css" in n for n in names)

    def test_epub_has_title_page(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            assert any("title.xhtml" in n for n in names)

    def test_epub_has_nav(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            assert any("nav" in n for n in names)

    def test_returns_absolute_path(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "test.epub"),
        )
        from pathlib import Path
        assert Path(path).is_absolute()


# ---------------------------------------------------------------------------
# Region rendering
# ---------------------------------------------------------------------------

class TestRegionRendering:
    def test_heading_in_output(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.HEADING, "My Heading", level=2)
        dna.add_region(RegionType.TEXT, "Content.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "h.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<h2>My Heading</h2>" in content

    def test_heading_level_clamped(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.HEADING, "Deep", level=9)
        dna.add_region(RegionType.TEXT, "Text.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "h.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<h6>" in content  # Clamped to 6

    def test_text_paragraphs(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Para one.\n\nPara two.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "p.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<p>Para one.</p>" in content
        assert "<p>Para two.</p>" in content

    def test_text_line_breaks(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Line one\nLine two")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "br.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<br/>" in content

    def test_table_rendered(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.TABLE,
            "| Name | Age |\n|------|-----|\n| Alice | 30 |",
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "t.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<table>" in content
        assert "<th>" in content
        assert "Alice" in content

    def test_table_with_caption(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.TABLE,
            "| A | B |\n|---|---|\n| 1 | 2 |",
            metadata={"caption": "My Table"},
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "tc.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<caption>" in content
        assert "My Table" in content

    def test_formula_display(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.FORMULA, "$$x^2$$",
            metadata={"mode": "display"},
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "f.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "formula-block" in content
        assert "latex" in content

    def test_formula_inline(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.FORMULA, "$x$",
            metadata={"mode": "inline"},
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "fi.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "formula-inline" in content

    def test_list_unordered(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.LIST, "- Apple\n- Banana\n- Cherry")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "ul.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<ul>" in content
        assert "<li>" in content
        assert "Apple" in content

    def test_list_ordered(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.LIST, "1. First\n2. Second\n3. Third")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "ol.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<ol>" in content

    def test_image_placeholder(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.IMAGE, "![photo](img.jpg)",
            metadata={"alt_text": "A photo"},
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "img.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<figure>" in content
        assert "A photo" in content

    def test_code_block(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.CODE, "print('hello')",
            metadata={"language": "python"},
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "code.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<pre>" in content
        assert "<code" in content
        assert "python" in content

    def test_code_no_language(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.CODE, "x = 1")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "code2.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<pre><code>" in content

    def test_all_regions(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _full_dna(), str(tmp_path / "full.epub"), title="Full",
        )
        assert zipfile.is_zipfile(path)
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<h1>" in content
        assert "<p>" in content
        assert "<table>" in content
        assert "formula-block" in content
        assert "<ul>" in content
        assert "<figure>" in content
        assert "<pre>" in content


# ---------------------------------------------------------------------------
# Chapter splitting
# ---------------------------------------------------------------------------

class TestChapterSplitting:
    def test_split_at_h1(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _chapter_dna(), str(tmp_path / "ch.epub"),
        )
        with zipfile.ZipFile(path) as z:
            chapters = [n for n in z.namelist() if "chapter_" in n]
            assert len(chapters) == 2

    def test_no_h1_single_chapter(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "No headings here.")
        dna.add_region(RegionType.TEXT, "More text.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "single.epub"))
        with zipfile.ZipFile(path) as z:
            chapters = [n for n in z.namelist() if "chapter_" in n]
            assert len(chapters) == 1

    def test_three_chapters(self, tmp_path):
        dna = LayoutDNA()
        for i in range(1, 4):
            dna.add_region(RegionType.HEADING, f"Chapter {i}", level=1)
            dna.add_region(RegionType.TEXT, f"Content {i}.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "3ch.epub"))
        with zipfile.ZipFile(path) as z:
            chapters = [n for n in z.namelist() if "chapter_" in n]
            assert len(chapters) == 3

    def test_no_split_option(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _chapter_dna(), str(tmp_path / "nosplit.epub"),
            chapter_split=False,
        )
        with zipfile.ZipFile(path) as z:
            chapters = [n for n in z.namelist() if "chapter_" in n]
            assert len(chapters) == 1

    def test_h2_does_not_split(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.HEADING, "Section A", level=2)
        dna.add_region(RegionType.TEXT, "Text A.")
        dna.add_region(RegionType.HEADING, "Section B", level=2)
        dna.add_region(RegionType.TEXT, "Text B.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "h2.epub"))
        with zipfile.ZipFile(path) as z:
            chapters = [n for n in z.namelist() if "chapter_" in n]
            assert len(chapters) == 1  # H2 doesn't split


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    def test_title_in_opf(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "meta.epub"),
            title="My Title",
        )
        with zipfile.ZipFile(path) as z:
            opf = z.read("EPUB/content.opf").decode("utf-8")
            assert "My Title" in opf

    def test_author_in_opf(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "meta.epub"),
            author="Jane Doe",
        )
        with zipfile.ZipFile(path) as z:
            opf = z.read("EPUB/content.opf").decode("utf-8")
            assert "Jane Doe" in opf

    def test_language_in_opf(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "meta.epub"),
            language="vi",
        )
        with zipfile.ZipFile(path) as z:
            opf = z.read("EPUB/content.opf").decode("utf-8")
            assert "vi" in opf

    def test_publisher_in_opf(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "meta.epub"),
            publisher="My Press",
        )
        with zipfile.ZipFile(path) as z:
            opf = z.read("EPUB/content.opf").decode("utf-8")
            assert "My Press" in opf


# ---------------------------------------------------------------------------
# render_from_text
# ---------------------------------------------------------------------------

class TestRenderFromText:
    def test_plain_text(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render_from_text(
            "Hello world.",
            str(tmp_path / "plain.epub"),
            title="Plain",
        )
        assert (tmp_path / "plain.epub").exists()
        assert zipfile.is_zipfile(path)

    def test_paragraphs(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render_from_text(
            "Para one.\n\nPara two.\n\nPara three.",
            str(tmp_path / "paras.epub"),
        )
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "Para one." in content
        assert "Para three." in content


# ---------------------------------------------------------------------------
# Cover image
# ---------------------------------------------------------------------------

class TestCoverImage:
    def test_cover_jpg(self, tmp_path):
        # Create a minimal JPEG file (just header bytes)
        cover = tmp_path / "cover.jpg"
        # Minimal JPEG: SOI marker + some data + EOI marker
        cover.write_bytes(
            b'\xff\xd8\xff\xe0' + b'\x00' * 20 + b'\xff\xd9'
        )

        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "cover.epub"),
            cover_image_path=str(cover),
        )
        assert zipfile.is_zipfile(path)

    def test_cover_png(self, tmp_path):
        cover = tmp_path / "cover.png"
        # Minimal PNG header
        cover.write_bytes(
            b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
        )

        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "cover_png.epub"),
            cover_image_path=str(cover),
        )
        assert zipfile.is_zipfile(path)

    def test_cover_not_found(self, tmp_path):
        renderer = EpubRenderer()
        path = renderer.render(
            _text_dna(), str(tmp_path / "nocover.epub"),
            cover_image_path="/nonexistent/cover.jpg",
        )
        # Should not crash
        assert (tmp_path / "nocover.epub").exists()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_unicode_content(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Xin chào thế giới. こんにちは世界.")

        renderer = EpubRenderer()
        path = renderer.render(
            dna, str(tmp_path / "unicode.epub"), language="vi",
        )
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "chào" in content
        assert "こんにちは" in content

    def test_html_escaping(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Use <div> & \"quotes\"")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "esc.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "&lt;div&gt;" in content
        assert "&amp;" in content

    def test_empty_region_content(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "")
        dna.add_region(RegionType.TEXT, "Real content.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "empty_r.epub"))
        assert (tmp_path / "empty_r.epub").exists()

    def test_many_regions(self, tmp_path):
        dna = LayoutDNA()
        for i in range(50):
            dna.add_region(RegionType.TEXT, f"Paragraph {i}.")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "many.epub"))
        assert zipfile.is_zipfile(path)

    def test_output_directory_creation(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "test.epub"
        renderer = EpubRenderer()
        path = renderer.render(_text_dna(), str(deep_path))
        assert deep_path.exists()

    def test_table_non_markdown(self, tmp_path):
        """Non-markdown table content falls back to <pre>."""
        dna = LayoutDNA()
        dna.add_region(RegionType.TABLE, "just plain text, not a table")

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "badtable.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<pre>" in content

    def test_grid_table(self, tmp_path):
        dna = LayoutDNA()
        dna.add_region(
            RegionType.TABLE,
            "+---+---+\n| A | B |\n+---+---+\n| 1 | 2 |\n+---+---+",
        )

        renderer = EpubRenderer()
        path = renderer.render(dna, str(tmp_path / "grid.epub"))
        content = _read_epub_file(path, "text/chapter_001.xhtml")
        assert "<table>" in content
        assert "A" in content
