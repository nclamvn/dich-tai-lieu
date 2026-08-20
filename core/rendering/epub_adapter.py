"""EPUB Adapter — render a Document AST to EPUB via ebooklib (Sóng 1).

Third output path off the single L0 AST (with docx_adapter and pdf_adapter).
Blocks are rendered to XHTML and split into chapters at H1 headings, with a
generated nav/TOC. Figures with carried ``image_bytes`` are embedded as real
``<img>`` images (registered as EPUB image items); figures without bytes render
as captioned placeholders.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from core.rendering.document_ast import (
    Block,
    Blockquote,
    Caption,
    DocumentAST,
    Epigraph,
    Equation,
    Figure,
    Heading,
    ListBlock,
    PageBreak,
    Paragraph,
    ProofBox,
    ReferenceEntry,
    SceneBreak,
    TableBlock,
    TheoremBox,
)

logger = logging.getLogger(__name__)

_CSS = """\
body { font-family: serif; line-height: 1.5; }
h1 { font-size: 1.6em; margin: 1em 0 .5em; }
h2 { font-size: 1.3em; margin: 1em 0 .4em; }
h3 { font-size: 1.1em; margin: .8em 0 .3em; }
p { margin: .4em 0; text-align: justify; }
blockquote { margin: .6em 1.5em; font-style: italic; }
.epigraph { text-align: right; font-style: italic; }
.scene { text-align: center; margin: 1em 0; }
.caption, figcaption { font-size: .9em; font-style: italic; text-align: center; }
.equation { text-align: center; font-family: monospace; }
table { border-collapse: collapse; width: 100%; margin: .6em 0; }
th, td { border: 1px solid #999; padding: 4px 6px; }
th { background: #eee; }
"""


_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/svg+xml": "svg",
}


def _sniff_mime(data: bytes) -> Optional[str]:
    """Best-effort image MIME from magic bytes (fallback when none was carried)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:2] == b"BM":
        return "image/bmp"
    return None


def _h1_level(block: Block) -> bool:
    return isinstance(block, Heading) and getattr(block.level, "value", 1) == 1


def _table_xhtml(block: TableBlock) -> str:
    e = html.escape
    rows = block.rows or []
    if not rows:
        return ""
    parts = ["<table>"]
    for r, row in enumerate(rows):
        tag = "th" if r < block.header_rows else "td"
        parts.append("<tr>" + "".join(f"<{tag}>{e(c)}</{tag}>" for c in row) + "</tr>")
    parts.append("</table>")
    if block.caption:
        parts.append(f'<p class="caption">{e(block.caption)}</p>')
    return "".join(parts)


def _runs_to_xhtml(runs) -> str:
    """Render inline runs as semantic XHTML: ``<strong>``/``<em>``/``<code>``,
    nested code → italic → bold (innermost to outermost). Run text is escaped."""
    e = html.escape
    parts = []
    for r in runs:
        t = e(r.text)
        if r.code:
            t = f"<code>{t}</code>"
        if r.italic:
            t = f"<em>{t}</em>"
        if r.bold:
            t = f"<strong>{t}</strong>"
        parts.append(t)
    return "".join(parts)


def _block_to_xhtml(
    block: Block,
    register_image: Optional[Callable[[bytes, Optional[str]], str]] = None,
) -> str:
    e = html.escape
    if isinstance(block, Heading):
        level = max(1, min(3, getattr(block.level, "value", 1)))
        prefix = f"{e(block.number)}. " if block.number else ""
        return f"<h{level}>{prefix}{e(block.text)}</h{level}>"
    if isinstance(block, Paragraph):
        if block.runs:
            return f"<p>{_runs_to_xhtml(block.runs)}</p>"
        return f"<p>{e(block.text)}</p>"
    if isinstance(block, Blockquote):
        attr = f"<br/>— {e(block.attribution)}" if block.attribution else ""
        return f"<blockquote>{e(block.text)}{attr}</blockquote>"
    if isinstance(block, Epigraph):
        attr = f"<br/>— {e(block.attribution)}" if block.attribution else ""
        return f'<p class="epigraph">{e(block.text)}{attr}</p>'
    if isinstance(block, SceneBreak):
        return f'<p class="scene">{e(block.symbol)}</p>'
    if isinstance(block, Equation):
        return f'<p class="equation">$$ {e(block.latex)} $$</p>'
    if isinstance(block, TheoremBox):
        title = block.title + (f" {block.number}" if block.number else "")
        return f"<p><strong>{e(title)}</strong></p><p>{e(block.content)}</p>"
    if isinstance(block, ProofBox):
        return f"<p><em>Proof.</em> {e(block.content)} {e(block.qed_symbol)}</p>"
    if isinstance(block, ReferenceEntry):
        text = f"[{block.key}] {block.citation}" if block.key else block.citation
        return f'<p class="reference">{e(text)}</p>'
    if isinstance(block, TableBlock):
        return _table_xhtml(block)
    if isinstance(block, Figure):
        caption = ""
        if block.caption:
            prefix = f"Hình {e(block.number)}. " if block.number else ""
            caption = f"<figcaption>{prefix}{e(block.caption)}</figcaption>"
        if block.image_bytes and register_image is not None:
            src = register_image(block.image_bytes, block.content_type)
            alt = e(block.alt_text or block.caption or "")
            return f'<figure><img src="{e(src)}" alt="{alt}"/>{caption}</figure>'
        label = e(block.alt_text or block.caption or block.image_ref or "image")
        return f'<figure><p class="caption">[Figure: {label}]</p>{caption}</figure>'
    if isinstance(block, ListBlock):
        tag = "ol" if block.ordered else "ul"
        items = "".join(f"<li>{e(item)}</li>" for item in block.items)
        return f"<{tag}>{items}</{tag}>"
    if isinstance(block, Caption):
        label = f"{e(block.target).capitalize()} {e(block.number)}. " if (block.target and block.number) else ""
        return f'<p class="caption">{label}{e(block.text)}</p>'
    if isinstance(block, PageBreak):
        return '<div style="page-break-after: always;"></div>'
    logger.warning("EPUB: unknown block type %s", type(block).__name__)
    return ""


def _split_chapters(blocks: List[Block]) -> List[Tuple[str, List[Block]]]:
    """Group blocks into chapters, starting a new one at each H1 heading."""
    chapters: List[Tuple[str, List[Block]]] = []
    title: Optional[str] = None
    buf: List[Block] = []
    for block in blocks:
        if _h1_level(block):
            if buf:
                chapters.append((title or "Nội dung", buf))
            title = block.text
            buf = [block]
        else:
            buf.append(block)
    if buf:
        chapters.append((title or "Nội dung", buf))
    if not chapters:
        chapters = [("Nội dung", list(blocks))]
    return chapters


def render_epub_from_ast(ast: DocumentAST, output_path: Path, title: Optional[str] = None) -> None:
    """Render a DocumentAST to an EPUB 3 file."""
    from ebooklib import epub

    md = ast.metadata
    book_title = title or md.title or "Untitled"
    slug = "".join(ch if ch.isalnum() else "-" for ch in book_title.lower())[:48] or "document"

    book = epub.EpubBook()
    book.set_identifier(f"urn:aipub:{slug}")
    book.set_title(book_title)
    book.set_language(md.language or "vi")
    if md.author:
        book.add_author(md.author)

    css = epub.EpubItem(
        uid="style", file_name="style/main.css", media_type="text/css", content=_CSS
    )
    book.add_item(css)

    # Register carried figure images as EPUB image items; return their href so
    # the chapter XHTML can <img> them. Filenames are content-root relative,
    # matching how chap_N.xhtml references style/main.css.
    image_counter = {"n": 0}

    def register_image(data: bytes, content_type: Optional[str]) -> str:
        image_counter["n"] += 1
        n = image_counter["n"]
        mime = content_type or _sniff_mime(data) or "image/png"
        ext = _MIME_EXT.get(mime, "png")
        fname = f"images/fig_{n}.{ext}"
        book.add_item(
            epub.EpubItem(uid=f"img_{n}", file_name=fname, media_type=mime, content=data)
        )
        return fname

    chapters = []
    for idx, (chapter_title, blocks) in enumerate(_split_chapters(ast.blocks), start=1):
        body = "".join(_block_to_xhtml(b, register_image) for b in blocks)
        item = epub.EpubHtml(
            title=chapter_title, file_name=f"chap_{idx}.xhtml", lang=md.language or "vi"
        )
        item.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            f"<head><title>{html.escape(chapter_title)}</title>"
            '<link rel="stylesheet" href="style/main.css" type="text/css"/></head>'
            f"<body>{body}</body></html>"
        )
        item.add_item(css)
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    logger.info("EPUB saved: %s (%d chapters)", output_path, len(chapters))
