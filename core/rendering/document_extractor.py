"""Extract a structure-preserving DocumentAST from a source file (L0 phase 2).

Reading order, headings, paragraphs, tables, lists and figures are mapped to AST
blocks so every downstream renderer works from one faithful representation.

Supported here: DOCX (python-docx gives clean structure) and TXT/MD. PDF
extraction is heuristic and tracked as an L0 follow-up — extract_to_ast raises a
clear NotImplementedError for it rather than returning a lossy result silently.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Iterator, List, Optional, Union

from core.rendering.document_ast import (
    Blockquote,
    DocumentAST,
    DocumentMetadata,
    Equation,
    EquationMode,
    Figure,
    Heading,
    HeadingLevel,
    InlineRun,
    ListBlock,
    Paragraph,
    StyleSheet,
    TableBlock,
)
from core.rendering.inline import parse_inline


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
# Inline formatting (bold / italic / code) -> Paragraph.runs
# --------------------------------------------------------------------------- #
# The Markdown inline parser (parse_inline) lives in core.rendering.inline so the
# renderers share it without importing this extractor; it is imported at the top
# and re-exported here for callers/tests that reference it via the extractor.

# Monospace faces / character-style hints that mark a DOCX run as inline code.
_MONO_FONT_NAMES = {
    "consolas", "courier", "courier new", "menlo", "monaco", "monospace",
    "dejavu sans mono", "lucida console", "sf mono", "roboto mono", "cascadia code",
}


def _paragraph_with_inline(text: str) -> Paragraph:
    """Build a Paragraph, attaching inline runs when *text* has Markdown emphasis.

    Keeps ``.text`` a faithful plaintext view (markers removed) so every consumer
    that reads ``.text`` still works, whether or not runs are present.
    """
    runs = parse_inline(text)
    if runs is None:
        return Paragraph(text=text)
    return Paragraph(text="".join(r.text for r in runs), runs=runs)


def _run_is_code(run) -> bool:
    """Heuristic: a DOCX run is inline code if its font is monospace or its
    character style name mentions code/verbatim/mono."""
    fname = (getattr(run.font, "name", None) or "").strip().lower()
    if fname in _MONO_FONT_NAMES:
        return True
    try:
        sname = (run.style.name or "").lower()
    except Exception:  # pragma: no cover - defensive
        sname = ""
    return "code" in sname or "verbatim" in sname or "mono" in sname


def _trim_runs(runs: List[InlineRun]) -> List[InlineRun]:
    """Trim leading/trailing whitespace across the list so the concatenation
    equals ``"".join(...).strip()`` — matching how plain paragraph text is
    stripped — while preserving each span's formatting and internal spacing."""
    runs = [r for r in runs if r.text]
    while runs and runs[0].text.strip() == "":
        runs = runs[1:]
    if runs:
        runs[0] = replace(runs[0], text=runs[0].text.lstrip())
    while runs and runs[-1].text.strip() == "":
        runs = runs[:-1]
    if runs:
        runs[-1] = replace(runs[-1], text=runs[-1].text.rstrip())
    return [r for r in runs if r.text]


def _docx_runs(paragraph) -> Optional[List[InlineRun]]:
    """Extract inline runs from a python-docx paragraph, or ``None`` when the
    whole paragraph is unformatted (keeps it plain / backward-compatible).

    Adjacent runs with identical formatting are merged (python-docx often splits
    a visual span into several runs), and edges are trimmed so the concatenation
    matches the stripped ``paragraph.text``.
    """
    merged: List[InlineRun] = []
    any_format = False
    for run in paragraph.runs:
        if not run.text:
            continue
        bold, italic, code = bool(run.bold), bool(run.italic), _run_is_code(run)
        if bold or italic or code:
            any_format = True
        if (
            merged
            and merged[-1].bold == bold
            and merged[-1].italic == italic
            and merged[-1].code == code
        ):
            merged[-1] = replace(merged[-1], text=merged[-1].text + run.text)
        else:
            merged.append(InlineRun(text=run.text, bold=bold, italic=italic, code=code))

    if not any_format:
        return None
    trimmed = _trim_runs(merged)
    return trimmed or None


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


def _paragraph_image(paragraph) -> Optional[tuple]:
    """If the paragraph embeds a picture, return ``(ref, image_bytes,
    content_type)``; else ``None``.

    The bytes are carried through the AST so downstream renderers re-embed the
    real image instead of a placeholder. Bytes/content-type are best-effort: a
    ref is always returned when a picture is present, bytes only when the related
    image part is readable.
    """
    from docx.oxml.ns import qn

    blips = paragraph._p.findall(".//" + qn("a:blip"))
    if not blips:
        return None
    rid = blips[0].get(qn("r:embed"))
    ref = rid or "embedded-image"
    image_bytes: Optional[bytes] = None
    content_type: Optional[str] = None
    try:
        part = paragraph.part.related_parts.get(rid)
        if part is not None:
            ref = str(part.partname)
            blob = getattr(part, "blob", None)
            if blob:
                image_bytes = bytes(blob)
            content_type = getattr(part, "content_type", None) or None
    except Exception:
        pass
    return ref, image_bytes, content_type


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
        image = _paragraph_image(paragraph)
        text = paragraph.text.strip()
        style = (paragraph.style.name if paragraph.style else "") or ""

        if image:
            flush_list()
            image_ref, image_bytes, content_type = image
            ast.add_block(
                Figure(
                    image_ref=image_ref,
                    caption=text or None,
                    image_bytes=image_bytes,
                    content_type=content_type,
                )
            )
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
            runs = _docx_runs(paragraph)
            ast.add_block(Paragraph(text=text, runs=runs) if runs else Paragraph(text=text))

    flush_list()
    return ast


# --------------------------------------------------------------------------- #
# Plain text / Markdown
# --------------------------------------------------------------------------- #
_MD_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_MD_LIST = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")
_MD_IMAGE = re.compile(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)\s*$')
_MD_DISPLAY_MATH = re.compile(r"^\$\$(.*?)\$\$\s*$")


def _is_table_sep(line: str) -> bool:
    """True for a GFM table separator row, e.g. ``| --- | :--: |``."""
    s = line.strip()
    return bool(s) and "-" in s and set(s) <= set("|-: ")


def _split_table_row(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def extract_text(path: Union[str, Path]) -> DocumentAST:
    """Extract a Markdown/plain-text file into a faithful DocumentAST.

    Beyond headings, paragraphs and lists this recognises GFM tables, display
    math (``$$…$$``), blockquotes (``>``) and image figures (``![alt](src)``),
    so the AST — and therefore every renderer, including the live EPUB path —
    keeps those structures instead of flattening them into prose.
    """
    path = Path(path)
    ast = _new_ast(path.stem)
    lines = path.read_text(encoding="utf-8").splitlines()
    pending_list: Optional[tuple] = None

    def flush_list() -> None:
        nonlocal pending_list
        if pending_list is not None:
            ordered, items = pending_list
            ast.add_block(ListBlock(items=items, ordered=ordered))
            pending_list = None

    i, n = 0, len(lines)
    while i < n:
        line = lines[i].strip()

        if not line:
            flush_list()
            i += 1
            continue

        # Display math: $$ ... $$ (single- or multi-line)
        if line.startswith("$$"):
            flush_list()
            one = _MD_DISPLAY_MATH.match(line)
            if one:
                ast.add_block(Equation(latex=one.group(1).strip(), mode=EquationMode.DISPLAY))
                i += 1
                continue
            buf = [line[2:]]
            i += 1
            while i < n and "$$" not in lines[i]:
                buf.append(lines[i])
                i += 1
            if i < n:  # closing "$$" line
                buf.append(lines[i].split("$$", 1)[0])
                i += 1
            ast.add_block(Equation(latex="\n".join(buf).strip(), mode=EquationMode.DISPLAY))
            continue

        # GFM table: a header row immediately followed by a separator row
        if "|" in line and i + 1 < n and _is_table_sep(lines[i + 1]):
            flush_list()
            rows = [_split_table_row(line)]
            i += 2  # skip header + separator
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(_split_table_row(lines[i]))
                i += 1
            ast.add_block(TableBlock(rows=rows, header_rows=1))
            continue

        # Blockquote: consecutive ``>`` lines
        if line.startswith(">"):
            flush_list()
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            ast.add_block(Blockquote(text=" ".join(quote).strip()))
            continue

        # Image figure: ![alt](src)
        image = _MD_IMAGE.match(line)
        if image:
            flush_list()
            alt = image.group(1).strip()
            ast.add_block(Figure(image_ref=image.group(2).strip(), alt_text=alt or None))
            i += 1
            continue

        heading = _MD_HEADING.match(line)
        if heading:
            flush_list()
            ast.add_block(
                Heading(level=HeadingLevel(len(heading.group(1))), text=heading.group(2).strip())
            )
            i += 1
            continue

        list_item = _MD_LIST.match(line)
        if list_item:
            ordered = list_item.group(1) not in ("-", "*", "+")
            if pending_list is None or pending_list[0] != ordered:
                flush_list()
                pending_list = (ordered, [])
            pending_list[1].append(list_item.group(2).strip())
            i += 1
            continue

        flush_list()
        ast.add_block(_paragraph_with_inline(line))
        i += 1

    flush_list()
    return ast
