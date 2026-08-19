"""Sóng 1: unified render facade — render_ast dispatch + convert_document pipeline."""

import pytest

from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Heading,
    HeadingLevel,
    Paragraph,
    TableBlock,
    create_book_stylesheet,
)
from core.rendering.render import SUPPORTED_FORMATS, convert_document, render_ast


def _ast() -> DocumentAST:
    doc = DocumentAST(metadata=DocumentMetadata(title="Tài liệu"), styles=create_book_stylesheet())
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chương 1"))
    doc.add_block(Paragraph(text="Đoạn văn tiếng Việt."))
    doc.add_block(TableBlock(rows=[["a", "b"], ["1", "2"]], header_rows=1))
    return doc


@pytest.mark.parametrize("ext", SUPPORTED_FORMATS)
def test_render_ast_dispatches_by_extension(tmp_path, ext):
    out = tmp_path / f"out.{ext}"
    render_ast(_ast(), out)
    assert out.exists() and out.stat().st_size > 300


def test_render_ast_explicit_format_overrides_extension(tmp_path):
    out = tmp_path / "no_extension"
    render_ast(_ast(), out, fmt="pdf")
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"


def test_render_ast_unsupported_format_raises(tmp_path):
    with pytest.raises(ValueError):
        render_ast(_ast(), tmp_path / "out.rtf")


def test_convert_document_docx_to_epub(tmp_path):
    from core.rendering.docx_adapter import render_docx_from_ast

    src = tmp_path / "src.docx"
    render_docx_from_ast(_ast(), src)

    out = tmp_path / "out.epub"
    convert_document(src, out)
    assert out.exists() and out.stat().st_size > 300


def test_convert_document_markdown_to_pdf(tmp_path):
    md = tmp_path / "in.md"
    md.write_text("# Tiêu đề\n\nMột đoạn.\n\n- a\n- b\n", encoding="utf-8")

    out = tmp_path / "out.pdf"
    convert_document(md, out)
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"
