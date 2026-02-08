"""
EPUB 3.0 Renderer — Convert LayoutDNA to valid EPUB 3.0 ebook.

Architecture:
1. LayoutDNA regions → XHTML chapter(s)
2. CSS stylesheet embedded
3. Table of Contents from heading regions
4. EPUB 3.0 package (OPF + NCX + XHTML + CSS)

Uses ebooklib for EPUB packaging.
Consumes Region/RegionType from layout_dna.py (Sprint 12).

Standalone module — no extraction or translation imports.

Usage::

    from api.services.layout_dna import LayoutDNA, RegionType
    from api.services.epub_renderer import EpubRenderer

    renderer = EpubRenderer()
    epub_path = renderer.render(
        layout_dna=dna,
        output_path="/tmp/output.epub",
        title="My Book",
        language="vi",
    )
"""

from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from api.services.layout_dna import LayoutDNA, Region, RegionType
from api.services import epub_styles

logger = logging.getLogger(__name__)

# Graceful import — renderer works only when ebooklib available
try:
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    epub = None  # type: ignore[assignment]
    EBOOKLIB_AVAILABLE = False
    logger.warning("ebooklib not installed — EPUB rendering unavailable")


# ---------------------------------------------------------------------------
# XHTML template
# ---------------------------------------------------------------------------

_CHAPTER_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
{content}
</body>
</html>"""


# ---------------------------------------------------------------------------
# EpubRenderer
# ---------------------------------------------------------------------------

class EpubRenderer:
    """Render LayoutDNA to EPUB 3.0 file.

    Usage::

        renderer = EpubRenderer()
        path = renderer.render(
            layout_dna=dna,
            output_path="output.epub",
            title="Book Title",
            author="Author",
            language="vi",
        )
    """

    def __init__(self) -> None:
        if not EBOOKLIB_AVAILABLE:
            raise ImportError(
                "ebooklib is required for EPUB rendering. "
                "Install with: pip install ebooklib"
            )

    def render(
        self,
        layout_dna: LayoutDNA,
        output_path: str,
        title: str = "Untitled",
        author: str = "",
        language: str = "en",
        publisher: str = "AI Publisher Pro",
        description: str = "",
        cover_image_path: Optional[str] = None,
        chapter_split: bool = True,
    ) -> str:
        """Render LayoutDNA to EPUB 3.0 file.

        Args:
            layout_dna: Structured document representation.
            output_path: Where to save .epub file.
            title: Book title.
            author: Author name.
            language: Language code (en, vi, ja, ...).
            publisher: Publisher name.
            description: Book description.
            cover_image_path: Optional cover image (JPG/PNG).
            chapter_split: Split at H1 headings into chapters.

        Returns:
            Absolute path to generated EPUB file.
        """
        book = epub.EpubBook()

        # --- Metadata ---
        book.set_identifier(f"aipub-{abs(hash(title)) % 10**8:08d}")
        book.set_title(title)
        book.set_language(epub_styles.get_lang_code(language))

        if author:
            book.add_author(author)

        book.add_metadata("DC", "publisher", publisher)

        if description:
            book.add_metadata("DC", "description", description)

        # --- Stylesheet ---
        css_item = epub.EpubItem(
            uid="style_main",
            file_name="style/main.css",
            media_type="text/css",
            content=epub_styles.get_css().encode("utf-8"),
        )
        book.add_item(css_item)

        # --- Cover image ---
        if cover_image_path and Path(cover_image_path).exists():
            self._add_cover(book, cover_image_path)

        # --- Title page ---
        title_html = epub_styles.get_title_page_html(
            title=title,
            author=author,
            publisher=publisher,
            language=language,
        )
        title_page = epub.EpubHtml(
            title="Title Page",
            file_name="text/title.xhtml",
            lang=language,
        )
        title_page.content = title_html.encode("utf-8")
        title_page.add_item(css_item)
        book.add_item(title_page)

        # --- Chapters from LayoutDNA ---
        chapters = self._build_chapters(
            layout_dna, language, css_item, chapter_split,
        )

        for chapter in chapters:
            book.add_item(chapter)

        # --- Table of Contents ---
        book.toc = self._build_toc(chapters)

        # --- Navigation ---
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # --- Spine (reading order) ---
        book.spine = ["nav", title_page] + chapters

        # --- Write EPUB ---
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output), book, {})

        logger.info(
            "EPUB rendered: %s (%d chapters, %d regions)",
            output, len(chapters), layout_dna.region_count,
        )

        return str(output.resolve())

    def render_from_text(
        self,
        text: str,
        output_path: str,
        title: str = "Untitled",
        author: str = "",
        language: str = "en",
        **kwargs,
    ) -> str:
        """Convenience: render plain text to EPUB.

        Wraps text in a simple LayoutDNA with TEXT regions.
        """
        dna = LayoutDNA()

        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if para:
                dna.add_region(RegionType.TEXT, para)

        return self.render(
            layout_dna=dna,
            output_path=output_path,
            title=title,
            author=author,
            language=language,
            **kwargs,
        )

    # --- Chapter building ---------------------------------------------------

    def _build_chapters(
        self,
        dna: LayoutDNA,
        language: str,
        css_item,
        chapter_split: bool,
    ) -> list:
        """Build XHTML chapters from LayoutDNA regions."""
        if not dna.regions:
            return [self._create_chapter(
                "Content", [], 1, language, css_item,
            )]

        if not chapter_split:
            return [self._create_chapter(
                "Content", dna.regions, 1, language, css_item,
            )]

        # Split at H1 headings
        groups = self._split_at_h1(dna.regions)

        chapters = []
        for i, (ch_title, regions) in enumerate(groups, 1):
            chapter = self._create_chapter(
                ch_title, regions, i, language, css_item,
            )
            chapters.append(chapter)

        return chapters

    def _split_at_h1(
        self, regions: List[Region],
    ) -> List[Tuple[str, List[Region]]]:
        """Split regions into chapter groups at H1 headings.

        Returns: [(chapter_title, [regions]), ...]
        """
        groups: List[Tuple[str, List[Region]]] = []
        current_title = "Chapter 1"
        current_regions: List[Region] = []

        for region in regions:
            if (
                region.type == RegionType.HEADING
                and region.level == 1
                and current_regions
            ):
                groups.append((current_title, current_regions))
                current_title = region.content or f"Chapter {len(groups) + 2}"
                current_regions = [region]
            else:
                if (
                    region.type == RegionType.HEADING
                    and region.level == 1
                    and not current_regions
                ):
                    current_title = region.content or current_title
                current_regions.append(region)

        if current_regions:
            groups.append((current_title, current_regions))

        if not groups:
            groups.append(("Content", list(regions)))

        return groups

    def _create_chapter(
        self,
        title: str,
        regions: List[Region],
        chapter_num: int,
        language: str,
        css_item,
    ):
        """Create one XHTML chapter from regions."""
        content_parts = []
        for region in regions:
            xhtml = self._region_to_xhtml(region)
            if xhtml:
                content_parts.append(xhtml)

        # ebooklib requires non-empty body content
        if not content_parts:
            content_parts.append("<p>&#160;</p>")

        content = "\n".join(content_parts)

        full_html = _CHAPTER_TEMPLATE.format(
            lang=epub_styles.get_lang_code(language),
            title=html.escape(title),
            content=content,
        )

        chapter = epub.EpubHtml(
            title=title,
            file_name=f"text/chapter_{chapter_num:03d}.xhtml",
            lang=language,
        )
        chapter.content = full_html.encode("utf-8")
        chapter.add_item(css_item)

        return chapter

    # --- Region → XHTML conversion -----------------------------------------

    def _region_to_xhtml(self, region: Region) -> str:
        """Convert a LayoutDNA region to XHTML fragment."""
        if region.type == RegionType.HEADING:
            return self._heading_to_xhtml(region)
        elif region.type == RegionType.TEXT:
            return self._text_to_xhtml(region)
        elif region.type == RegionType.TABLE:
            return self._table_to_xhtml(region)
        elif region.type == RegionType.FORMULA:
            return self._formula_to_xhtml(region)
        elif region.type == RegionType.LIST:
            return self._list_to_xhtml(region)
        elif region.type == RegionType.IMAGE:
            return self._image_to_xhtml(region)
        elif region.type == RegionType.CODE:
            return self._code_to_xhtml(region)
        else:
            return f"<p>{html.escape(region.content)}</p>"

    def _heading_to_xhtml(self, region: Region) -> str:
        level = min(6, max(1, region.level))
        escaped = html.escape(region.content)
        return f"<h{level}>{escaped}</h{level}>"

    def _text_to_xhtml(self, region: Region) -> str:
        content = region.content
        if not content.strip():
            return ""

        # Split into paragraphs at double newlines
        paragraphs = content.split("\n\n")
        parts = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # Single newlines → <br/>
                lines = para.split("\n")
                if len(lines) > 1:
                    inner = "<br/>\n".join(html.escape(line) for line in lines)
                else:
                    inner = html.escape(para)
                parts.append(f"<p>{inner}</p>")

        return "\n".join(parts)

    def _table_to_xhtml(self, region: Region) -> str:
        """Convert table region to XHTML table.

        The content is the raw table text (markdown format).
        Parse it into HTML table.
        """
        content = region.content
        caption = region.metadata.get("caption")

        # Try to parse markdown table
        lines = content.strip().split("\n")
        table_rows = []
        has_sep = False

        for line in lines:
            stripped = line.strip()
            if re.match(r'^\|[\s:]*-[-:|\s]+\|', stripped):
                has_sep = True
                continue
            if re.match(r'^\+[-=+]+\+', stripped):
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped[1:-1].split("|")]
                table_rows.append(cells)

        if not table_rows:
            # Fallback: wrap raw content in pre
            return f"<pre>{html.escape(content)}</pre>"

        # Build HTML table
        parts = ["<table>"]
        if caption:
            parts.append(f"<caption>{html.escape(caption)}</caption>")

        for i, row in enumerate(table_rows):
            parts.append("<tr>")
            tag = "th" if (i == 0 and has_sep) else "td"
            for cell in row:
                parts.append(f"  <{tag}>{html.escape(cell)}</{tag}>")
            parts.append("</tr>")

        parts.append("</table>")
        return "\n".join(parts)

    def _formula_to_xhtml(self, region: Region) -> str:
        mode = region.metadata.get("mode", "display")
        escaped = html.escape(region.content)

        if mode == "inline":
            return (
                f'<span class="formula-inline">'
                f'<code class="latex">{escaped}</code>'
                f'</span>'
            )
        else:
            return (
                f'<div class="formula-block">'
                f'<code class="latex">{escaped}</code>'
                f'</div>'
            )

    def _list_to_xhtml(self, region: Region) -> str:
        content = region.content
        lines = content.strip().split("\n")

        # Detect ordered vs unordered
        ordered = False
        if lines:
            first = lines[0].strip()
            if re.match(r'^\d+[.)]', first):
                ordered = True

        tag = "ol" if ordered else "ul"
        items = []
        for line in lines:
            # Strip bullet/number marker
            cleaned = re.sub(r'^\s*(?:[-*+•]|\d+[.)])\s*', '', line)
            if cleaned.strip():
                items.append(f"  <li>{html.escape(cleaned.strip())}</li>")

        if not items:
            return ""

        return f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>"

    def _image_to_xhtml(self, region: Region) -> str:
        alt = html.escape(
            region.metadata.get("alt_text", "") or region.content or "Image"
        )
        return f"<figure>\n  <p>[{alt}]</p>\n</figure>"

    def _code_to_xhtml(self, region: Region) -> str:
        lang = region.metadata.get("language", "")
        escaped = html.escape(region.content)
        if lang:
            return f'<pre><code class="language-{html.escape(lang)}">{escaped}</code></pre>'
        return f"<pre><code>{escaped}</code></pre>"

    # --- Table of Contents --------------------------------------------------

    def _build_toc(self, chapters: list) -> list:
        """Build EPUB table of contents from chapters."""
        toc = []
        for chapter in chapters:
            toc.append(
                epub.Link(chapter.file_name, chapter.title, chapter.id)
            )
        return toc

    # --- Cover image --------------------------------------------------------

    def _add_cover(self, book, image_path: str) -> None:
        """Add cover image to EPUB."""
        path = Path(image_path)
        if not path.exists():
            logger.warning("Cover image not found: %s", image_path)
            return

        suffix = path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        try:
            image_data = path.read_bytes()
            book.set_cover(f"cover{suffix}", image_data)
            logger.info("Cover image added: %s", path.name)
        except Exception as e:
            logger.warning("Failed to add cover image: %s", e)


# ---------------------------------------------------------------------------
# Module-level utility
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Check if EPUB rendering is available (ebooklib installed)."""
    return EBOOKLIB_AVAILABLE
