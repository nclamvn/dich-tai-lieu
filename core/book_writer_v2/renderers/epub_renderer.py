"""
EPUB Renderer (Sprint K — TIP K5)

Generates EPUB 3.0 output with optional illustrations.
Uses ebooklib for EPUB construction.

Supports all 5 layout modes, gallery CSS grid, full-page spine pages,
alt text, credits, and genre-aware CSS.
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from ..models import BookBlueprint
from ..illustration_models import (
    BookGenre,
    GalleryGroup,
    IllustrationPlan,
    ImagePlacement,
    ImageSize,
    LayoutMode,
)

logger = logging.getLogger("BookWriter.EpubRenderer")

# Maximum image dimensions for EPUB
MAX_WIDTH = 1440
MAX_HEIGHT = 1920


class EpubRenderer:
    """Renders a BookBlueprint as EPUB 3.0 with optional illustrations."""

    def __init__(self, genre: BookGenre = BookGenre.NON_FICTION):
        self.genre = genre

    def render(
        self,
        blueprint: BookBlueprint,
        output_dir: Path,
        plan: Optional[IllustrationPlan] = None,
    ) -> Path:
        """Generate EPUB file."""
        from ebooklib import epub

        book = epub.EpubBook()

        # Metadata
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(blueprint.title)
        book.set_language(blueprint.language or "en")
        book.add_author(blueprint.author)

        # Stylesheet (genre-aware)
        style = self._default_css()
        css = epub.EpubItem(
            uid="style",
            file_name="style/default.css",
            media_type="text/css",
            content=style.encode("utf-8"),
        )
        book.add_item(css)

        # Embed images if plan exists
        image_items: Dict[str, str] = {}
        if plan:
            image_items = self._embed_images(book, plan)

        # Build chapters + full-page image pages
        spine_items: List = []
        toc = []
        chapter_idx = 0

        for part in blueprint.parts:
            for chapter in part.chapters:
                # Collect full-page placements to create separate spine pages
                full_page_placements = []
                if plan:
                    ch_placements = plan.get_placements_for_chapter(chapter_idx)
                    full_page_placements = [
                        p for p in ch_placements
                        if p.layout_mode == LayoutMode.FULL_PAGE
                        and p.image_id in image_items
                    ]

                # Main chapter content (excludes full-page images)
                xhtml_content = self._build_chapter_xhtml(
                    chapter, chapter_idx, plan, image_items,
                )

                ch_filename = f"chapter_{chapter_idx + 1}.xhtml"
                epub_ch = epub.EpubHtml(
                    title=f"Chapter {chapter.number}: {chapter.title}",
                    file_name=ch_filename,
                    lang=blueprint.language or "en",
                )
                epub_ch.content = xhtml_content.encode("utf-8")
                epub_ch.add_item(css)

                book.add_item(epub_ch)
                spine_items.append(epub_ch)
                toc.append(epub_ch)

                # Full-page images as separate spine pages
                for fp_idx, fp in enumerate(full_page_placements):
                    fp_xhtml = self._build_fullpage_xhtml(fp, image_items)
                    fp_filename = f"chapter_{chapter_idx + 1}_img_{fp_idx + 1}.xhtml"
                    fp_item = epub.EpubHtml(
                        title=fp.caption or f"Image {fp_idx + 1}",
                        file_name=fp_filename,
                        lang=blueprint.language or "en",
                    )
                    fp_item.content = fp_xhtml.encode("utf-8")
                    fp_item.add_item(css)
                    book.add_item(fp_item)
                    spine_items.append(fp_item)

                # Gallery pages
                if plan:
                    for gal_idx, gallery in enumerate(plan.galleries):
                        if gallery.chapter_index == chapter_idx:
                            gal_xhtml = self._build_gallery_xhtml(
                                gallery, plan, image_items
                            )
                            gal_filename = f"chapter_{chapter_idx + 1}_gallery_{gal_idx + 1}.xhtml"
                            gal_item = epub.EpubHtml(
                                title=gallery.title or "Gallery",
                                file_name=gal_filename,
                                lang=blueprint.language or "en",
                            )
                            gal_item.content = gal_xhtml.encode("utf-8")
                            gal_item.add_item(css)
                            book.add_item(gal_item)
                            spine_items.append(gal_item)

                chapter_idx += 1

        # TOC and spine
        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav"] + spine_items

        # Write EPUB
        filename = self._sanitize_filename(blueprint.title) + ".epub"
        filepath = output_dir / filename
        epub.write_epub(str(filepath), book, {})

        logger.info(f"EPUB generated: {filepath}")
        return filepath

    def _build_chapter_xhtml(
        self,
        chapter,
        chapter_idx: int,
        plan: Optional[IllustrationPlan],
        image_items: dict,
    ) -> str:
        """Build XHTML content for a single chapter.

        Full-page images are excluded here (rendered as separate spine pages).
        """
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html>',
            '<html xmlns="http://www.w3.org/1999/xhtml">',
            "<head>",
            f"<title>Chapter {chapter.number}: {chapter.title}</title>",
            '<link rel="stylesheet" type="text/css" href="style/default.css"/>',
            "</head>",
            "<body>",
            f"<h1>Chapter {chapter.number}: {chapter.title}</h1>",
        ]

        if chapter.introduction:
            parts.append(f"<p class='intro'>{self._escape(chapter.introduction)}</p>")

        for sec_idx, section in enumerate(chapter.sections):
            parts.append(f"<h2>{self._escape(section.title)}</h2>")

            if plan:
                sec_placements = plan.get_placements_for_section(chapter_idx, sec_idx)

                # Float-top illustrations (exclude FULL_PAGE — they have own pages)
                for p in sec_placements:
                    if (
                        p.layout_mode == LayoutMode.FLOAT_TOP
                        and p.image_id in image_items
                    ):
                        parts.append(self._xhtml_figure(p, image_items))

            # Section content
            for para in section.content.split("\n\n"):
                para = para.strip()
                if para:
                    parts.append(f"<p>{self._escape(para)}</p>")

            # Non-float, non-full-page illustrations
            if plan:
                for p in sec_placements:
                    if (
                        p.layout_mode not in (LayoutMode.FLOAT_TOP, LayoutMode.FULL_PAGE)
                        and p.image_id in image_items
                    ):
                        parts.append(self._xhtml_figure(p, image_items))

        if chapter.summary:
            parts.append("<h3>Summary</h3>")
            parts.append(f"<p>{self._escape(chapter.summary)}</p>")

        if chapter.key_takeaways:
            parts.append("<h3>Key Takeaways</h3>")
            parts.append("<ul>")
            for t in chapter.key_takeaways:
                parts.append(f"<li>{self._escape(t)}</li>")
            parts.append("</ul>")

        parts.extend(["</body>", "</html>"])
        return "\n".join(parts)

    def _build_fullpage_xhtml(
        self, placement: ImagePlacement, image_items: dict
    ) -> str:
        """Build a dedicated XHTML page for a full-page image."""
        epub_path = image_items.get(placement.image_id, "")
        alt = self._escape(placement.alt_text or placement.caption or "")
        caption = ""
        if placement.caption:
            caption = f"<figcaption>{self._escape(placement.caption)}</figcaption>"
        credit = ""
        if placement.credit:
            credit = f'<p class="credit">{self._escape(placement.credit)}</p>'

        return "\n".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html>',
            '<html xmlns="http://www.w3.org/1999/xhtml">',
            "<head>",
            f"<title>{self._escape(placement.caption or 'Image')}</title>",
            '<link rel="stylesheet" type="text/css" href="style/default.css"/>',
            "</head>",
            '<body class="full-page-body">',
            '<figure class="illustration full-page">',
            f'<img src="{epub_path}" alt="{alt}" style="max-width:100%;"/>',
            caption,
            credit,
            "</figure>",
            "</body>",
            "</html>",
        ])

    def _build_gallery_xhtml(
        self, gallery: GalleryGroup, plan: IllustrationPlan, image_items: dict
    ) -> str:
        """Build a gallery page with CSS grid layout."""
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html>',
            '<html xmlns="http://www.w3.org/1999/xhtml">',
            "<head>",
            f"<title>{self._escape(gallery.title or 'Gallery')}</title>",
            '<link rel="stylesheet" type="text/css" href="style/default.css"/>',
            "</head>",
            "<body>",
        ]

        if gallery.title:
            parts.append(f'<h2 class="gallery-title">{self._escape(gallery.title)}</h2>')

        parts.append('<div class="gallery">')
        for img_id in gallery.image_ids:
            epub_path = image_items.get(img_id, "")
            if not epub_path:
                continue

            placement = next(
                (p for p in plan.placements if p.image_id == img_id), None
            )
            alt = ""
            caption = ""
            if placement:
                alt = self._escape(placement.alt_text or placement.caption or "")
                if placement.caption:
                    caption = f"<figcaption>{self._escape(placement.caption)}</figcaption>"

            parts.append('<figure class="gallery-item">')
            parts.append(f'<img src="{epub_path}" alt="{alt}"/>')
            parts.append(caption)
            parts.append("</figure>")

        parts.append("</div>")

        if gallery.caption:
            parts.append(
                f'<p class="gallery-caption">{self._escape(gallery.caption)}</p>'
            )

        parts.extend(["</body>", "</html>"])
        return "\n".join(parts)

    def _embed_images(self, book, plan: IllustrationPlan) -> dict:
        """Embed images into the EPUB and return a map of image_id -> epub filename."""
        from ebooklib import epub

        image_items = {}
        seen_ids = set()

        for placement in plan.placements:
            if placement.image_id in seen_ids:
                continue
            seen_ids.add(placement.image_id)

            image_path = self._resolve_image_path(placement.image_id)
            if not image_path or not os.path.exists(image_path):
                continue

            # Resize if needed
            img_bytes = self._resize_image(image_path)
            if not img_bytes:
                continue

            ext = Path(image_path).suffix.lower()
            media_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_map.get(ext, "image/jpeg")
            epub_filename = f"images/{placement.image_id}{ext}"

            item = epub.EpubImage()
            item.file_name = epub_filename
            item.media_type = media_type
            item.content = img_bytes
            book.add_item(item)

            image_items[placement.image_id] = epub_filename

        return image_items

    def _resize_image(self, path: str) -> Optional[bytes]:
        """Resize image to fit EPUB constraints, return bytes."""
        try:
            from PIL import Image
            import io

            with Image.open(path) as img:
                if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
                    img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)

                buf = io.BytesIO()
                fmt = img.format or "JPEG"
                if fmt.upper() == "WEBP":
                    fmt = "PNG"
                img.save(buf, format=fmt)
                return buf.getvalue()
        except Exception as e:
            logger.warning(f"Image resize failed for {path}: {e}")
            try:
                return Path(path).read_bytes()
            except Exception:
                return None

    def _xhtml_figure(self, placement: ImagePlacement, image_items: dict) -> str:
        """Generate XHTML figure for EPUB with alt text and credit."""
        epub_path = image_items.get(placement.image_id, "")
        if not epub_path:
            return ""

        size_map = {
            ImageSize.SMALL: "25%",
            ImageSize.MEDIUM: "50%",
            ImageSize.LARGE: "75%",
            ImageSize.FULL: "100%",
        }
        width = size_map.get(placement.size, "50%")

        css_class = "illustration"
        if placement.layout_mode == LayoutMode.FULL_PAGE:
            css_class = "illustration full-page"
            width = "100%"
        elif placement.layout_mode == LayoutMode.MARGIN:
            css_class = "illustration margin-img"

        alt = self._escape(placement.alt_text or placement.caption or "")

        caption = ""
        if placement.caption:
            caption = f"<figcaption>{self._escape(placement.caption)}</figcaption>"

        credit = ""
        if placement.credit:
            credit = f'<span class="credit">{self._escape(placement.credit)}</span>'

        return (
            f'<figure class="{css_class}">'
            f'<img src="{epub_path}" alt="{alt}" '
            f'style="max-width:{width};"/>'
            f"{caption}{credit}"
            f"</figure>"
        )

    def _resolve_image_path(self, image_id: str) -> Optional[str]:
        """Resolve image_id to a file path."""
        if os.path.exists(image_id):
            return image_id
        for base in ["data/uploads/books", "data/uploads"]:
            for root, _, files in os.walk(base):
                for f in files:
                    if image_id in f:
                        return os.path.join(root, f)
        return None

    def _default_css(self) -> str:
        return """
body { font-family: Georgia, serif; line-height: 1.6; margin: 1em; }
body.full-page-body { margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
h1 { text-align: center; margin-top: 2em; }
h2 { margin-top: 1.5em; }
h3 { margin-top: 1em; }
p { text-indent: 1.5em; margin: 0.5em 0; }
p.intro { text-indent: 0; font-style: italic; }
figure { margin: 1em 0; text-align: center; }
figure img { max-width: 100%; height: auto; }
figcaption { font-style: italic; color: #666; font-size: 0.9em; margin-top: 0.5em; }
figure.full-page { page-break-before: always; page-break-after: always; }
figure.margin-img { float: right; width: 30%; margin: 0 0 0.5em 1em; }
figure.margin-img img { max-width: 100%; }
.credit { display: block; font-size: 0.75em; color: #999; font-style: italic; margin-top: 0.25em; }
.gallery { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
.gallery-item { flex: 0 0 45%; text-align: center; }
.gallery-item img { max-width: 100%; height: auto; }
.gallery-title { text-align: center; }
.gallery-caption { text-align: center; font-style: italic; color: #666; }
ul { margin: 0.5em 0; padding-left: 1.5em; }
"""

    def _sanitize_filename(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.replace(' ', '_')
        return name[:100]

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML entities."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
