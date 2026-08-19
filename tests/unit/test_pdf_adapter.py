"""Sóng 1: render the AST to PDF (ReportLab). Content asserted via pypdf."""

import pypdf

from core.rendering.document_ast import (
    Caption,
    DocumentAST,
    DocumentMetadata,
    Heading,
    HeadingLevel,
    ListBlock,
    PageBreak,
    Paragraph,
    TableBlock,
    create_book_stylesheet,
)
from core.rendering.pdf_adapter import render_pdf_from_ast


def _ast() -> DocumentAST:
    doc = DocumentAST(metadata=DocumentMetadata(title="Doc"), styles=create_book_stylesheet())
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chapter One"))
    doc.add_block(Paragraph(text="Body text alpha."))
    doc.add_block(ListBlock(items=["item-x", "item-y"], ordered=False))
    doc.add_block(TableBlock(rows=[["H1", "H2"], ["c1", "c2"]], header_rows=1, caption="Table cap"))
    doc.add_block(Caption(text="A caption", target="figure", number="1"))
    doc.add_block(PageBreak())
    doc.add_block(Paragraph(text="Đoạn tiếng Việt có dấu đầy đủ."))
    return doc


def _pdf_text(path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_render_produces_valid_pdf(tmp_path):
    out = tmp_path / "out.pdf"
    render_pdf_from_ast(_ast(), out)
    assert out.exists() and out.stat().st_size > 500


def test_page_break_creates_second_page(tmp_path):
    out = tmp_path / "out.pdf"
    render_pdf_from_ast(_ast(), out)
    assert len(pypdf.PdfReader(str(out)).pages) >= 2


def test_pdf_contains_expected_content(tmp_path):
    out = tmp_path / "out.pdf"
    render_pdf_from_ast(_ast(), out)
    text = _pdf_text(out)
    assert "Chapter One" in text
    assert "H1" in text and "c1" in text  # table cells rendered
    assert "item-x" in text  # list item rendered


def test_vietnamese_does_not_crash(tmp_path):
    doc = DocumentAST(metadata=DocumentMetadata(), styles=create_book_stylesheet())
    doc.add_block(Paragraph(text="Tiếng Việt: sắc huyền hỏi ngã nặng — đủ dấu."))
    out = tmp_path / "vn.pdf"
    render_pdf_from_ast(doc, out)
    assert out.exists() and out.stat().st_size > 300


def test_empty_document_still_writes_pdf(tmp_path):
    doc = DocumentAST(metadata=DocumentMetadata(), styles=create_book_stylesheet())
    out = tmp_path / "empty.pdf"
    render_pdf_from_ast(doc, out)
    assert out.exists()
