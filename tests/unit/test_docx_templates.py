"""DOCX style templates (Option A, stage 2b.1).

Parity with the legacy renderer's ``template=`` argument: ebook (Georgia),
academic (Cambria), business (Arial). The template swaps the stylesheet for the
render without mutating the caller's AST.
"""

from docx import Document

from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Paragraph,
    StyleSheet,
)
from core.rendering.docx_adapter import (
    render_academic_docx,
    render_book_docx,
    render_docx_from_ast,
)


def _para_ast(text="Xin chào thế giới") -> DocumentAST:
    ast = DocumentAST(metadata=DocumentMetadata(title="T"), styles=StyleSheet())
    ast.add_block(Paragraph(text=text))
    return ast


def _fonts(path) -> set:
    d = Document(str(path))
    return {r.font.name for p in d.paragraphs for r in p.runs if r.font.name}


def test_academic_template_uses_cambria(tmp_path):
    out = tmp_path / "a.docx"
    render_docx_from_ast(_para_ast(), out, template="academic")
    assert "Cambria" in _fonts(out)


def test_ebook_template_uses_georgia(tmp_path):
    out = tmp_path / "e.docx"
    render_docx_from_ast(_para_ast(), out, template="ebook")
    assert "Georgia" in _fonts(out)


def test_business_template_uses_arial(tmp_path):
    out = tmp_path / "b.docx"
    render_docx_from_ast(_para_ast(), out, template="business")
    assert "Arial" in _fonts(out)


def test_convenience_academic_applies_cambria(tmp_path):
    out = tmp_path / "c.docx"
    render_academic_docx(_para_ast(), out)
    assert "Cambria" in _fonts(out)  # was a no-op stub before


def test_convenience_book_applies_georgia(tmp_path):
    out = tmp_path / "c.docx"
    render_book_docx(_para_ast(), out)
    assert "Georgia" in _fonts(out)


def test_template_does_not_mutate_caller_ast(tmp_path):
    ast = _para_ast()
    before = ast.styles.body.font.family  # Georgia (default StyleSheet)
    render_docx_from_ast(ast, tmp_path / "m.docx", template="academic")
    assert ast.styles.body.font.family == before  # caller's AST left untouched


def test_no_template_uses_ast_styles_unchanged(tmp_path):
    # A custom body font on the AST must survive when no template is forced.
    ast = _para_ast()
    ast.styles.body.font.family = "Verdana"
    out = tmp_path / "n.docx"
    render_docx_from_ast(ast, out)  # template=None
    assert "Verdana" in _fonts(out)
