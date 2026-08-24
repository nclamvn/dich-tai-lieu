"""PDF style templates (Option A, stage 2b.4).

The PDF adapter now reads ast.styles and registers a serif + a sans family, so
ebook/academic render serif and business renders sans — parity with the DOCX
template system. Fonts are embedded, so the /BaseFont shows up via pypdf.
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


def _base_fonts(path) -> str:
    reader = pypdf.PdfReader(str(path))
    names = set()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for f in fonts.values():
            obj = f.get_object()
            if obj.get("/BaseFont"):
                names.add(str(obj.get("/BaseFont")))
            for df in obj.get("/DescendantFonts") or []:
                d = df.get_object()
                if d.get("/BaseFont"):
                    names.add(str(d.get("/BaseFont")))
    return " ".join(sorted(names))


def _render(tmp_path, template) -> str:
    ast = DocumentAST(metadata=DocumentMetadata(title="T"), styles=StyleSheet())
    ast.add_block(Heading(level=HeadingLevel.H1, text="Chương một"))
    ast.add_block(Paragraph(text="Đoạn văn tiếng Việt đủ dấu."))
    out = tmp_path / f"{template or 'none'}.pdf"
    render_pdf_from_ast(ast, out, template=template)
    return _base_fonts(out)


# The registered faces are whatever Vietnamese-capable family the adapter found
# (bundled Noto first, DejaVu/Liberation as fallbacks) — assert on the serif/sans
# *classification*, not on one vendor's file name.
def _is_serif(name: str) -> bool:
    return "Serif" in name


def _is_sans(name: str) -> bool:
    return ("Sans" in name) and "Serif" not in name


def test_ebook_is_serif_not_sans(tmp_path):
    fonts = _render(tmp_path, "ebook")
    assert any(_is_serif(n) for n in fonts.split())
    assert not any(_is_sans(n) for n in fonts.split())


def test_business_is_sans_not_serif(tmp_path):
    fonts = _render(tmp_path, "business")
    assert any(_is_sans(n) for n in fonts.split())
    assert not any(_is_serif(n) for n in fonts.split())


def test_academic_is_serif(tmp_path):
    assert any(_is_serif(n) for n in _render(tmp_path, "academic").split())


def test_default_no_template_uses_serif(tmp_path):
    # default StyleSheet body font is Georgia -> serif
    assert any(_is_serif(n) for n in _render(tmp_path, None).split())


def test_ebook_and_business_differ(tmp_path):
    assert _render(tmp_path, "ebook") != _render(tmp_path, "business")


class TestBodyParagraphSpacing:
    """Regression: the PDF body style silently dropped the stylesheet's
    paragraph spacing — novels rendered as one solid justified wall of text
    (no space between paragraphs, no first-line indent)."""

    def _renderer(self):
        from core.rendering.document_ast import DocumentAST, DocumentMetadata, StyleSheet
        from core.rendering.pdf_adapter import _PdfRenderer, _ensure_fonts

        ast = DocumentAST(metadata=DocumentMetadata(title="t"), styles=StyleSheet())
        return _PdfRenderer(ast, _ensure_fonts())

    def test_body_consumes_stylesheet_spacing(self):
        r = self._renderer()
        assert r.body.spaceAfter > 0, "paragraphs need breathing space"
        assert r.body.firstLineIndent > 0, "book body keeps its first-line indent"

    def test_first_paragraph_style_has_no_indent(self):
        r = self._renderer()
        assert r.body_first.firstLineIndent == 0.0
        assert r.body_first.spaceAfter == r.body.spaceAfter

    def test_extractor_tags_first_paragraph_roles(self, tmp_path):
        from core.rendering.document_extractor import extract_to_ast
        from core.rendering.document_ast import Paragraph, ParagraphRole

        md = tmp_path / "s.md"
        md.write_text("# H\n\nOpener after heading.\n\nRegular body one.\n\nRegular body two.\n")
        ast = extract_to_ast(md)
        roles = [b.role for b in ast.blocks if isinstance(b, Paragraph)]
        assert roles[0] == ParagraphRole.FIRST_PARAGRAPH
        assert all(r == ParagraphRole.BODY for r in roles[1:])
