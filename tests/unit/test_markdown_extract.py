"""Markdown -> AST extraction now keeps tables, display math, blockquotes and
figures — so the live EPUB path (extract_to_ast on translated markdown) stops
flattening them into prose. Foundation for AST-convergence (Option A)."""

from core.rendering.document_ast import (
    Blockquote,
    Equation,
    Figure,
    Heading,
    ListBlock,
    Paragraph,
    TableBlock,
)
from core.rendering.document_extractor import extract_to_ast


def _ast(tmp_path, md):
    p = tmp_path / "doc.md"
    p.write_text(md, encoding="utf-8")
    return extract_to_ast(p)


def test_table_extracted(tmp_path):
    ast = _ast(tmp_path, "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n")
    tables = [b for b in ast.blocks if isinstance(b, TableBlock)]
    assert len(tables) == 1
    assert tables[0].rows == [["A", "B"], ["1", "2"], ["3", "4"]]
    assert tables[0].header_rows == 1


def test_display_math_single_line(tmp_path):
    ast = _ast(tmp_path, "$$E = mc^2$$\n")
    eqs = [b for b in ast.blocks if isinstance(b, Equation)]
    assert len(eqs) == 1 and eqs[0].latex == "E = mc^2"


def test_display_math_multiline(tmp_path):
    ast = _ast(tmp_path, "$$\n\\int_0^1 x\\,dx = \\tfrac12\n$$\n")
    eqs = [b for b in ast.blocks if isinstance(b, Equation)]
    assert len(eqs) == 1 and "\\int_0^1" in eqs[0].latex


def test_blockquote_extracted(tmp_path):
    ast = _ast(tmp_path, "> to be\n> or not to be\n")
    bq = [b for b in ast.blocks if isinstance(b, Blockquote)]
    assert len(bq) == 1 and bq[0].text == "to be or not to be"


def test_image_figure_extracted(tmp_path):
    ast = _ast(tmp_path, "![a small cat](images/cat.png)\n")
    figs = [b for b in ast.blocks if isinstance(b, Figure)]
    assert len(figs) == 1
    assert figs[0].image_ref == "images/cat.png"
    assert figs[0].alt_text == "a small cat"


def test_headings_lists_paragraphs_still_work(tmp_path):
    ast = _ast(tmp_path, "# Title\n\nA paragraph.\n\n- one\n- two\n")
    assert any(isinstance(b, Heading) for b in ast.blocks)
    lists = [b for b in ast.blocks if isinstance(b, ListBlock)]
    assert lists and lists[0].items == ["one", "two"]
    assert any(isinstance(b, Paragraph) and b.text == "A paragraph." for b in ast.blocks)


def test_combined_document_block_order(tmp_path):
    md = (
        "# Heading\n\n"
        "Intro paragraph.\n\n"
        "| X | Y |\n| - | - |\n| 1 | 2 |\n\n"
        "> a quote\n\n"
        "$$a + b$$\n\n"
        "![alt](p.png)\n"
    )
    ast = _ast(tmp_path, md)
    assert [type(b).__name__ for b in ast.blocks] == [
        "Heading",
        "Paragraph",
        "TableBlock",
        "Blockquote",
        "Equation",
        "Figure",
    ]


def test_live_epub_path_keeps_table(tmp_path):
    """Regression for the actual live path: markdown -> extract_to_ast -> EPUB
    must render the table as a real <table>, not flatten it."""
    import ebooklib
    from ebooklib import epub

    from core.rendering.epub_adapter import render_epub_from_ast

    ast = _ast(tmp_path, "# Chương\n\n| A | B |\n| - | - |\n| 1 | 2 |\n")
    out = tmp_path / "o.epub"
    render_epub_from_ast(ast, out)

    book = epub.read_epub(str(out))
    docs = [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
    xhtml = " ".join(d.get_content().decode("utf-8") for d in docs)
    assert "<table>" in xhtml and "<td>1</td>" in xhtml
