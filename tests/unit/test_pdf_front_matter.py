"""PDF front matter — title page, TOC, page-number footer (Option A polish).

Brings the PDF adapter up to the DOCX book layout: ``render_pdf_from_ast`` gains
``title_page`` / ``toc`` / ``header_footer`` flags (all default-off, so existing
callers are unaffected). The TOC uses reportlab's TableOfContents resolved with a
multiBuild pass, so entries carry real page numbers.
"""

import pypdf

from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Heading,
    HeadingLevel,
    Paragraph,
    StyleSheet,
)
from core.rendering.pdf_adapter import render_pdf_from_ast


def _book_ast(language="vi"):
    ast = DocumentAST(
        metadata=DocumentMetadata(title="Tựa sách", author="Người viết", language=language),
        styles=StyleSheet(),
    )
    ast.add_block(Heading(level=HeadingLevel.H1, text="Chương một"))
    ast.add_block(Paragraph(text="Nội dung chương một."))
    ast.add_block(Heading(level=HeadingLevel.H2, text="Mục 1.1"))
    ast.add_block(Paragraph(text="Nội dung mục."))
    ast.add_block(Heading(level=HeadingLevel.H1, text="Chương hai"))
    ast.add_block(Paragraph(text="Nội dung chương hai."))
    return ast


def _pages_text(path):
    reader = pypdf.PdfReader(str(path))
    return len(reader.pages), "".join((pg.extract_text() or "") for pg in reader.pages)


def test_default_has_no_cover_or_toc(tmp_path):
    out = tmp_path / "plain.pdf"
    render_pdf_from_ast(_book_ast(), out)  # all flags default off
    _, text = _pages_text(out)
    assert "Mục lục" not in text and "Contents" not in text
    assert "Chương một" in text  # content still renders


def test_title_page_adds_cover(tmp_path):
    plain = tmp_path / "plain.pdf"
    covered = tmp_path / "cover.pdf"
    render_pdf_from_ast(_book_ast(), plain)
    render_pdf_from_ast(_book_ast(), covered, title="Tựa sách", title_page=True)

    n_plain, _ = _pages_text(plain)
    n_cover, cover_text = _pages_text(covered)
    assert n_cover > n_plain  # the cover added a page
    assert "Tựa sách" in cover_text
    assert "Người viết" in cover_text  # author from metadata


def test_toc_heading_localized_vi(tmp_path):
    out = tmp_path / "toc_vi.pdf"
    render_pdf_from_ast(_book_ast("vi"), out, toc=True)
    _, text = _pages_text(out)
    assert "Mục lục" in text
    # TOC entries reference the chapter titles
    assert "Chương một" in text and "Chương hai" in text


def test_toc_heading_localized_en(tmp_path):
    out = tmp_path / "toc_en.pdf"
    render_pdf_from_ast(_book_ast("en"), out, toc=True)
    _, text = _pages_text(out)
    assert "Contents" in text


def test_full_front_matter_renders_and_paginates(tmp_path):
    """title_page + toc + header_footer together: cover + TOC + content, and the
    multiBuild/footer path does not crash."""
    out = tmp_path / "book.pdf"
    render_pdf_from_ast(
        _book_ast(), out, template="ebook",
        title="Tựa sách", title_page=True, toc=True, header_footer=True,
    )
    n, text = _pages_text(out)
    assert n >= 3  # cover + TOC + at least one content page
    assert "Tựa sách" in text
    assert "Mục lục" in text
    assert "Chương một" in text


def test_flags_are_backward_compatible_signature():
    """Existing callers pass only (ast, path[, title, template]); the new flags
    must remain keyword-optional and default off."""
    import inspect

    sig = inspect.signature(render_pdf_from_ast)
    for name in ("title_page", "toc", "header_footer"):
        assert sig.parameters[name].default is False
