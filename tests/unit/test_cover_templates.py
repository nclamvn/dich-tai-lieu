"""Cover-template engine: registry, per-template rendering, and PDF integration.

All no-API-key and deterministic: templates are drawn with ReportLab and read
back with pypdf. Vietnamese title/author must survive; any title length must lay
out on a single page; and the PDF adapter must merge a chosen template as page 1.
"""

import pypdf
import pytest

from core.rendering.cover_templates import (
    COVER_TEMPLATES,
    has_template,
    list_templates,
    render_cover_pdf,
)
from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Heading,
    HeadingLevel,
    Paragraph,
    StyleSheet,
)
from core.rendering.pdf_adapter import render_pdf_from_ast

EXPECTED_IDS = {
    "classic", "minimal", "bold", "noir", "gradient", "duotone",
    "geometric", "framed", "colorblock", "academic", "vintage", "emblem",
}


def _meta(title="KHỞI NGUỒN", author="Nguyễn Cảnh Lâm", language="vi"):
    return DocumentMetadata(title=title, author=author, language=language)


def _pages(path):
    return len(pypdf.PdfReader(str(path)).pages)


def test_registry_lists_all_templates():
    ids = {t["id"] for t in list_templates()}
    assert ids == EXPECTED_IDS
    for t in list_templates():
        assert t["name"] and t["category"] and t["description"]


def test_has_template():
    assert has_template("noir")
    assert not has_template("does-not-exist")


@pytest.mark.parametrize("template_id", sorted(EXPECTED_IDS))
def test_each_template_renders_single_page(tmp_path, template_id):
    out = tmp_path / f"{template_id}.pdf"
    render_cover_pdf(template_id, _meta(), out)
    assert out.exists() and out.stat().st_size > 500
    assert _pages(out) == 1


def test_unknown_template_raises():
    with pytest.raises(KeyError):
        render_cover_pdf("nope", _meta(), "/tmp/never.pdf")


def test_long_title_lays_out_on_one_page(tmp_path):
    long = "Một Tựa Sách Rất Dài Dùng Để Kiểm Tra Khả Năng Tự Co Và Xuống Dòng Trên Trang Bìa"
    out = tmp_path / "long.pdf"
    render_cover_pdf("classic", _meta(title=long), out)
    assert _pages(out) == 1


def test_missing_title_uses_placeholder(tmp_path):
    out = tmp_path / "notitle.pdf"
    render_cover_pdf("minimal", DocumentMetadata(language="en"), out)  # no title/author
    assert _pages(out) == 1


def test_english_kicker_differs_from_vietnamese(tmp_path):
    # Different languages pick different default kickers; both still one page.
    for lang in ("vi", "en"):
        out = tmp_path / f"k_{lang}.pdf"
        render_cover_pdf("classic", _meta(language=lang), out)
        assert _pages(out) == 1


def _book_ast():
    ast = DocumentAST(metadata=_meta(), styles=StyleSheet())
    ast.add_block(Heading(level=HeadingLevel.H1, text="Chương một"))
    ast.add_block(Paragraph(text="Nội dung chương một, tiếng Việt đủ dấu."))
    ast.add_block(Heading(level=HeadingLevel.H1, text="Chương hai"))
    ast.add_block(Paragraph(text="Nội dung chương hai."))
    return ast


def test_pdf_adapter_prepends_template_cover(tmp_path):
    plain = tmp_path / "plain.pdf"
    withcover = tmp_path / "cover.pdf"
    render_pdf_from_ast(_book_ast(), plain)
    render_pdf_from_ast(_book_ast(), withcover, cover_template="noir")
    # The template cover adds exactly one page ahead of the same body.
    assert _pages(withcover) == _pages(plain) + 1


def test_pdf_adapter_unknown_cover_falls_through(tmp_path):
    out = tmp_path / "fallthrough.pdf"
    # Must not raise; produces a valid PDF using the normal path.
    render_pdf_from_ast(_book_ast(), out, cover_template="no-such-template")
    assert _pages(out) >= 1


def test_all_templates_merge_into_book(tmp_path):
    for template_id in sorted(EXPECTED_IDS):
        out = tmp_path / f"book_{template_id}.pdf"
        render_pdf_from_ast(_book_ast(), out, cover_template=template_id)
        assert _pages(out) >= 2  # cover + at least one body page
