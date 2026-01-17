#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EPUB Exporter

Exports translated documents to EPUB format.
EPUB is also used as an intermediate format for MOBI conversion.
"""

import os
import zipfile
import uuid
import html
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EpubChapter:
    """Represents a chapter in the EPUB."""
    title: str
    content: str  # HTML content
    filename: str = ""
    order: int = 0

    def __post_init__(self):
        if not self.filename:
            self.filename = f"chapter_{self.order:03d}.xhtml"


@dataclass
class EpubMetadata:
    """EPUB metadata."""
    title: str = "Untitled"
    author: str = "AI Publisher Pro"
    language: str = "vi"
    identifier: str = ""  # UUID or ISBN
    publisher: str = "AI Publisher Pro"
    description: str = ""
    subject: str = ""
    date: str = ""
    rights: str = ""
    cover_image: Optional[Path] = None

    def __post_init__(self):
        if not self.identifier:
            self.identifier = f"urn:uuid:{uuid.uuid4()}"
        if not self.date:
            self.date = datetime.utcnow().strftime("%Y-%m-%d")


class EpubExporter:
    """
    Exports content to EPUB format.

    EPUB structure:
    - mimetype
    - META-INF/container.xml
    - OEBPS/
        - content.opf (package document)
        - toc.ncx (navigation)
        - nav.xhtml (EPUB3 navigation)
        - style.css
        - chapter_001.xhtml, ...
        - images/
    """

    def __init__(self):
        """Initialize exporter."""
        pass

    def export(
        self,
        chapters: List[EpubChapter],
        output_path: Path,
        metadata: Optional[EpubMetadata] = None
    ) -> Path:
        """
        Export chapters to EPUB.

        Args:
            chapters: List of chapters
            output_path: Output file path
            metadata: Book metadata

        Returns:
            Path to generated EPUB
        """
        metadata = metadata or EpubMetadata()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype must be first and uncompressed
            epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

            # Container
            epub.writestr('META-INF/container.xml', self._generate_container())

            # Content
            epub.writestr('OEBPS/content.opf', self._generate_opf(chapters, metadata))
            epub.writestr('OEBPS/toc.ncx', self._generate_ncx(chapters, metadata))
            epub.writestr('OEBPS/nav.xhtml', self._generate_nav(chapters, metadata))
            epub.writestr('OEBPS/style.css', self._generate_css())

            # Chapters
            for chapter in chapters:
                epub.writestr(
                    f'OEBPS/{chapter.filename}',
                    self._generate_chapter_xhtml(chapter, metadata)
                )

            # Cover image
            if metadata.cover_image and metadata.cover_image.exists():
                cover_data = metadata.cover_image.read_bytes()
                suffix = metadata.cover_image.suffix.lower()
                media_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                }.get(suffix, 'image/jpeg')
                epub.writestr(f'OEBPS/images/cover{suffix}', cover_data)

        logger.info(f"EPUB created: {output_path}")
        return output_path

    def export_from_html(
        self,
        html_content: str,
        output_path: Path,
        title: str = "Untitled",
        author: str = "AI Publisher Pro",
        language: str = "vi"
    ) -> Path:
        """
        Export HTML content to EPUB.

        Automatically splits content into chapters based on h1/h2 tags.
        """
        chapters = self._split_into_chapters(html_content)
        metadata = EpubMetadata(title=title, author=author, language=language)
        return self.export(chapters, output_path, metadata)

    def export_from_markdown(
        self,
        markdown_content: str,
        output_path: Path,
        title: str = "Untitled",
        author: str = "AI Publisher Pro",
        language: str = "vi"
    ) -> Path:
        """Export Markdown content to EPUB."""
        # Convert markdown to HTML
        try:
            import markdown
            html_content = markdown.markdown(
                markdown_content,
                extensions=['extra', 'toc', 'meta']
            )
        except ImportError:
            # Basic markdown conversion
            html_content = self._basic_markdown_to_html(markdown_content)

        return self.export_from_html(html_content, output_path, title, author, language)

    def _split_into_chapters(self, html_content: str) -> List[EpubChapter]:
        """Split HTML content into chapters based on headings."""
        import re

        # Find all h1 or h2 tags and split
        pattern = r'(<h[12][^>]*>.*?</h[12]>)'
        parts = re.split(pattern, html_content, flags=re.IGNORECASE | re.DOTALL)

        chapters = []
        current_title = "Introduction"
        current_content = []

        for i, part in enumerate(parts):
            if re.match(r'<h[12]', part, re.IGNORECASE):
                # Save previous chapter
                if current_content:
                    chapters.append(EpubChapter(
                        title=current_title,
                        content=''.join(current_content),
                        order=len(chapters)
                    ))
                    current_content = []

                # Extract title from heading
                title_match = re.search(r'>(.+?)<', part, re.DOTALL)
                current_title = title_match.group(1).strip() if title_match else f"Chapter {len(chapters) + 1}"
                current_content.append(part)
            else:
                current_content.append(part)

        # Add final chapter
        if current_content:
            chapters.append(EpubChapter(
                title=current_title,
                content=''.join(current_content),
                order=len(chapters)
            ))

        # If no chapters found, create one
        if not chapters:
            chapters.append(EpubChapter(
                title="Content",
                content=html_content,
                order=0
            ))

        return chapters

    def _basic_markdown_to_html(self, md: str) -> str:
        """Basic markdown to HTML conversion."""
        import re

        html = md

        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Paragraphs
        paragraphs = html.split('\n\n')
        html = '\n'.join(f'<p>{p}</p>' if not p.startswith('<') else p for p in paragraphs)

        return html

    def _generate_container(self) -> str:
        """Generate META-INF/container.xml."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''

    def _generate_opf(self, chapters: List[EpubChapter], meta: EpubMetadata) -> str:
        """Generate OEBPS/content.opf."""
        items = []
        spine = []

        # Add nav and style
        items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        items.append('<item id="style" href="style.css" media-type="text/css"/>')

        # Add chapters
        for chapter in chapters:
            item_id = f"chapter_{chapter.order:03d}"
            items.append(f'<item id="{item_id}" href="{chapter.filename}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="{item_id}"/>')

        # Add cover if present
        cover_item = ""
        cover_meta = ""
        if meta.cover_image and meta.cover_image.exists():
            suffix = meta.cover_image.suffix.lower()
            media_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"
            items.append(f'<item id="cover-image" href="images/cover{suffix}" media-type="{media_type}" properties="cover-image"/>')
            cover_meta = '<meta name="cover" content="cover-image"/>'

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">{html.escape(meta.identifier)}</dc:identifier>
    <dc:title>{html.escape(meta.title)}</dc:title>
    <dc:creator>{html.escape(meta.author)}</dc:creator>
    <dc:language>{meta.language}</dc:language>
    <dc:publisher>{html.escape(meta.publisher)}</dc:publisher>
    <dc:date>{meta.date}</dc:date>
    <meta property="dcterms:modified">{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
    {cover_meta}
  </metadata>
  <manifest>
    {chr(10).join(items)}
  </manifest>
  <spine toc="ncx">
    {chr(10).join(spine)}
  </spine>
</package>'''

    def _generate_ncx(self, chapters: List[EpubChapter], meta: EpubMetadata) -> str:
        """Generate OEBPS/toc.ncx (EPUB2 navigation)."""
        nav_points = []
        for chapter in chapters:
            nav_points.append(f'''
    <navPoint id="navPoint-{chapter.order}" playOrder="{chapter.order + 1}">
      <navLabel><text>{html.escape(chapter.title)}</text></navLabel>
      <content src="{chapter.filename}"/>
    </navPoint>''')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{html.escape(meta.identifier)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(meta.title)}</text></docTitle>
  <navMap>
    {''.join(nav_points)}
  </navMap>
</ncx>'''

    def _generate_nav(self, chapters: List[EpubChapter], meta: EpubMetadata) -> str:
        """Generate OEBPS/nav.xhtml (EPUB3 navigation)."""
        toc_items = []
        for chapter in chapters:
            toc_items.append(f'<li><a href="{chapter.filename}">{html.escape(chapter.title)}</a></li>')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{meta.language}">
<head>
  <title>Mục Lục</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Mục Lục</h1>
    <ol>
      {''.join(toc_items)}
    </ol>
  </nav>
</body>
</html>'''

    def _generate_chapter_xhtml(self, chapter: EpubChapter, meta: EpubMetadata) -> str:
        """Generate chapter XHTML file."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{meta.language}">
<head>
  <title>{html.escape(chapter.title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <section>
    {chapter.content}
  </section>
</body>
</html>'''

    def _generate_css(self) -> str:
        """Generate stylesheet."""
        return '''
/* EPUB Stylesheet - AI Publisher Pro */

body {
  font-family: serif;
  font-size: 1em;
  line-height: 1.6;
  margin: 1em;
  padding: 0;
}

h1, h2, h3, h4, h5, h6 {
  font-family: sans-serif;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

h1 { font-size: 1.8em; text-align: center; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.3em; }

p {
  margin: 0.5em 0;
  text-align: justify;
  text-indent: 1.5em;
}

p:first-of-type {
  text-indent: 0;
}

blockquote {
  margin: 1em 2em;
  font-style: italic;
}

ul, ol {
  margin: 1em 0;
  padding-left: 2em;
}

img {
  max-width: 100%;
  height: auto;
}

.chapter-title {
  page-break-before: always;
}

/* Vietnamese typography */
:lang(vi) {
  font-family: "Noto Serif", serif;
}
'''
