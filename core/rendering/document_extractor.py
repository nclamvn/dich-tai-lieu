"""Extract a structure-preserving DocumentAST from a source file (L0 phase 2).

Reading order, headings, paragraphs, tables, lists and figures are mapped to AST
blocks so every downstream renderer works from one faithful representation.

Supported here: DOCX (python-docx gives clean structure) and TXT/MD. PDF
extraction is heuristic and tracked as an L0 follow-up — extract_to_ast raises a
clear NotImplementedError for it rather than returning a lossy result silently.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional, Union

from core.rendering.document_ast import (
    DocumentAST,
    DocumentMetadata,
    Figure,
    Heading,
    HeadingLevel,
    ListBlock,
    Paragraph,
    StyleSheet,
    TableBlock,
)


def extract_to_ast(source: Union[str, Path]) -> DocumentAST:
    """Extract *source* into a DocumentAST, dispatching on file extension."""
    path = Path(source)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in (".txt", ".md", ".markdown"):
        return extract_text(path)
    raise NotImplementedError(
        f"extract_to_ast does not support '{suffix}' yet "
        "(DOCX and TXT/MD are supported; PDF extraction is an L0 follow-up)."
    )


def _new_ast(title: str) -> DocumentAST:
    return DocumentAST(metadata=DocumentMetadata(title=title), styles=StyleSheet())


def _heading_level(style_name: Optional[str]) -> HeadingLevel:
    match = re.search(r"(\d+)", style_name or "")
    level = int(match.group(1)) if match else 1
    return HeadingLevel(max(1, min(3, level)))


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #
def _iter_block_items(document) -> Iterator:
    """Yield python-docx Paragraph and Table objects in document order."""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph as DocxParagraph

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield DocxParagraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _paragraph_image_ref(paragraph) -> Optional[str]:
    """Return an image reference if the paragraph embeds a picture, else None."""
    from docx.oxml.ns import qn

    blips = paragraph._p.findall(".//" + qn("a:blip"))
    if not blips:
        return None
    rid = blips[0].get(qn("r:embed"))
    try:
        part = paragraph.part.related_parts.get(rid)
        if part is not None:
            return str(part.partname)
    except Exception:
        pass
    return rid or "embedded-image"


def extract_docx(path: Union[str, Path]) -> DocumentAST:
    from docx import Document as DocxDocument
    from docx.table import Table as DocxTable

    path = Path(path)
    doc = DocxDocument(str(path))
    ast = _new_ast(path.stem)

    pending_list: Optional[tuple] = None  # (ordered: bool, items: list[str])

    def flush_list() -> None:
        nonlocal pending_list
        if pending_list is not None:
            ordered, items = pending_list
            ast.add_block(ListBlock(items=items, ordered=ordered))
            pending_list = None

    for item in _iter_block_items(doc):
        if isinstance(item, DocxTable):
            flush_list()
            rows = [[cell.text.strip() for cell in row.cells] for row in item.rows]
            ast.add_block(TableBlock(rows=rows, header_rows=1))
            continue

        paragraph = item
        image_ref = _paragraph_image_ref(paragraph)
        text = paragraph.text.strip()
        style = (paragraph.style.name if paragraph.style else "") or ""

        if image_ref:
            flush_list()
            ast.add_block(Figure(image_ref=image_ref, caption=text or None))
        elif not text:
            continue  # skip empty spacer paragraphs
        elif style.startswith("Heading") or style == "Title":
            flush_list()
            ast.add_block(Heading(level=_heading_level(style), text=text))
        elif "List" in style:
            ordered = "Number" in style
            if pending_list is None or pending_list[0] != ordered:
                flush_list()
                pending_list = (ordered, [])
            pending_list[1].append(text)
        else:
            flush_list()
            ast.add_block(Paragraph(text=text))

    flush_list()
    return ast


# --------------------------------------------------------------------------- #
# Plain text / Markdown
# --------------------------------------------------------------------------- #
_MD_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_MD_LIST = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")


def extract_text(path: Union[str, Path]) -> DocumentAST:
    path = Path(path)
    ast = _new_ast(path.stem)
    pending_list: Optional[tuple] = None

    def flush_list() -> None:
        nonlocal pending_list
        if pending_list is not None:
            ordered, items = pending_list
            ast.add_block(ListBlock(items=items, ordered=ordered))
            pending_list = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            flush_list()
            continue

        heading = _MD_HEADING.match(line)
        if heading:
            flush_list()
            ast.add_block(
                Heading(level=HeadingLevel(len(heading.group(1))), text=heading.group(2).strip())
            )
            continue

        list_item = _MD_LIST.match(line)
        if list_item:
            ordered = list_item.group(1) not in ("-", "*", "+")
            if pending_list is None or pending_list[0] != ordered:
                flush_list()
                pending_list = (ordered, [])
            pending_list[1].append(list_item.group(2).strip())
            continue

        flush_list()
        ast.add_block(Paragraph(text=line))

    flush_list()
    return ast
