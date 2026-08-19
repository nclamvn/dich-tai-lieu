"""Unified render facade (Sóng 1) — one entry point over the AST renderers.

- ``render_ast(ast, output_path)`` dispatches to the DOCX / PDF / EPUB adapter
  by the output extension (or an explicit ``fmt``).
- ``convert_document(input_path, output_path)`` is the full pipeline:
  read a file into the AST (extract_to_ast) then render it to another format —
  e.g. ``convert_document("book.docx", "book.epub")``.

This ties L0 (one AST) and Sóng 1 (three renderers) into a single call so the
whole read↔write loop is usable from the app or a script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from core.rendering.document_ast import DocumentAST

SUPPORTED_FORMATS = ("docx", "pdf", "epub")


def _infer_format(output_path: Path) -> str:
    return output_path.suffix.lower().lstrip(".")


def render_ast(ast: DocumentAST, output_path: Union[str, Path], fmt: Optional[str] = None) -> Path:
    """Render a DocumentAST to a file. Format is the extension unless given."""
    output_path = Path(output_path)
    resolved = (fmt or _infer_format(output_path)).lower()

    if resolved == "docx":
        from core.rendering.docx_adapter import render_docx_from_ast

        render_docx_from_ast(ast, output_path)
    elif resolved == "pdf":
        from core.rendering.pdf_adapter import render_pdf_from_ast

        render_pdf_from_ast(ast, output_path)
    elif resolved == "epub":
        from core.rendering.epub_adapter import render_epub_from_ast

        render_epub_from_ast(ast, output_path)
    else:
        raise ValueError(
            f"Unsupported output format '{resolved or '(none)'}'. "
            f"Supported: {', '.join(SUPPORTED_FORMATS)}."
        )
    return output_path


def convert_document(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    fmt: Optional[str] = None,
) -> Path:
    """Full pipeline: extract *input_path* into the AST, then render to *output_path*."""
    from core.rendering.document_extractor import extract_to_ast

    ast = extract_to_ast(input_path)
    return render_ast(ast, output_path, fmt)
