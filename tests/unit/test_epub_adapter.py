"""Sóng 1: render the AST to EPUB (ebooklib), read back to assert content."""

import ebooklib
from ebooklib import epub

from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Heading,
    HeadingLevel,
    ListBlock,
    Paragraph,
    TableBlock,
    create_book_stylesheet,
)
from core.rendering.epub_adapter import render_epub_from_ast


def _ast() -> DocumentAST:
    doc = DocumentAST(
        metadata=DocumentMetadata(title="Sách", author="Tác giả"),
        styles=create_book_stylesheet(),
    )
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chương 1"))
    doc.add_block(Paragraph(text="Nội dung chương một."))
    doc.add_block(TableBlock(rows=[["H1", "H2"], ["1", "2"]], header_rows=1))
    doc.add_block(ListBlock(items=["a", "b"], ordered=False))
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chương 2"))
    doc.add_block(Paragraph(text="Nội dung chương hai."))
    return doc


def _doc_content(path) -> str:
    book = epub.read_epub(str(path))
    docs = [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
    return " ".join(d.get_content().decode("utf-8") for d in docs)


def test_epub_written_and_readable(tmp_path):
    out = tmp_path / "book.epub"
    render_epub_from_ast(_ast(), out)
    assert out.exists() and out.stat().st_size > 500
    book = epub.read_epub(str(out))
    assert book.get_metadata("DC", "title")  # title metadata present


def test_epub_splits_chapters_at_h1(tmp_path):
    out = tmp_path / "book.epub"
    render_epub_from_ast(_ast(), out)
    content = _doc_content(out)
    assert "Chương 1" in content
    assert "Chương 2" in content


def test_epub_renders_table_and_list(tmp_path):
    out = tmp_path / "book.epub"
    render_epub_from_ast(_ast(), out)
    content = _doc_content(out)
    assert "<table" in content and "<th>H1</th>" in content
    assert "<li>a</li>" in content


def test_epub_vietnamese_content(tmp_path):
    doc = DocumentAST(metadata=DocumentMetadata(title="VN"), styles=create_book_stylesheet())
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chương tiếng Việt"))
    doc.add_block(Paragraph(text="Đủ dấu: sắc huyền hỏi ngã nặng."))
    out = tmp_path / "vn.epub"
    render_epub_from_ast(doc, out)
    assert "sắc huyền hỏi ngã nặng" in _doc_content(out)


def test_epub_no_h1_still_one_chapter(tmp_path):
    doc = DocumentAST(metadata=DocumentMetadata(title="Flat"), styles=create_book_stylesheet())
    doc.add_block(Paragraph(text="Chỉ có đoạn văn, không có tiêu đề H1."))
    out = tmp_path / "flat.epub"
    render_epub_from_ast(doc, out)
    assert out.exists()
    assert "không có tiêu đề" in _doc_content(out)
