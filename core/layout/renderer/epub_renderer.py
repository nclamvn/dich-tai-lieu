#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB Renderer

Renders LayoutIntentPackage to EPUB3 e-book format.
Uses ebooklib for EPUB generation.

Version: 1.0.0
"""

from typing import List, Dict, Optional, Any, Tuple, TYPE_CHECKING
from pathlib import Path
import logging
import uuid
from datetime import datetime

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False

from core.contracts import (
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionType,
)
from .base_renderer import BaseRenderer

if TYPE_CHECKING:
    from ..executor.block_flow import FlowedBlock
    from ..sections.manager import SectionManager

logger = logging.getLogger(__name__)


class EPUBRenderer(BaseRenderer):
    """
    Renders LayoutIntentPackage to EPUB3.

    Features:
    - EPUB3 standard compliance
    - Responsive content
    - Navigation (TOC)
    - Metadata support (title, author, ISBN)
    - Custom CSS styling
    - Chapter-based structure

    Usage:
        renderer = EPUBRenderer(template="book")
        renderer.render(lip, flowed_blocks, "output.epub")
    """

    # Template-specific CSS
    TEMPLATE_CSS = {
        "book": """
            body {
                font-family: Georgia, "Times New Roman", serif;
                font-size: 1em;
                line-height: 1.6;
                margin: 1em;
                text-align: justify;
            }
            h1 {
                font-size: 2em;
                margin-top: 2em;
                margin-bottom: 1em;
                text-align: center;
                page-break-before: always;
            }
            h2 {
                font-size: 1.5em;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            h3 {
                font-size: 1.2em;
                margin-top: 1em;
                margin-bottom: 0.5em;
            }
            p {
                margin: 0.5em 0;
                text-indent: 1.5em;
            }
            p.first {
                text-indent: 0;
            }
            blockquote {
                margin: 1em 2em;
                font-style: italic;
                border-left: 3px solid #ccc;
                padding-left: 1em;
            }
            pre, code {
                font-family: "Courier New", monospace;
                font-size: 0.9em;
                background-color: #f5f5f5;
                padding: 0.5em;
                white-space: pre-wrap;
            }
            .title-page {
                text-align: center;
                margin-top: 30%;
            }
            .title-page h1 {
                font-size: 2.5em;
                margin-bottom: 0.5em;
            }
            .title-page .subtitle {
                font-size: 1.2em;
                color: #666;
            }
            .title-page .author {
                font-size: 1.1em;
                margin-top: 2em;
            }
            .toc-entry {
                margin: 0.3em 0;
            }
            .toc-entry.level-1 {
                font-weight: bold;
            }
            .toc-entry.level-2 {
                margin-left: 1.5em;
            }
            .toc-entry.level-3 {
                margin-left: 3em;
                font-size: 0.9em;
            }
        """,
        "report": """
            body {
                font-family: Arial, Helvetica, sans-serif;
                font-size: 1em;
                line-height: 1.4;
                margin: 1em;
            }
            h1 {
                font-size: 1.8em;
                color: #333;
                border-bottom: 2px solid #333;
                padding-bottom: 0.3em;
                page-break-before: always;
            }
            h2 {
                font-size: 1.4em;
                color: #444;
            }
            p {
                margin: 0.8em 0;
            }
            blockquote {
                margin: 1em 2em;
                padding: 0.5em 1em;
                background-color: #f9f9f9;
                border-left: 3px solid #666;
            }
        """,
        "academic": """
            body {
                font-family: "Times New Roman", Times, serif;
                font-size: 12pt;
                line-height: 2;
                margin: 1in;
            }
            h1 {
                font-size: 14pt;
                font-weight: bold;
                text-align: center;
                margin-top: 1em;
            }
            p {
                text-indent: 0.5in;
                margin: 0;
            }
            blockquote {
                margin: 1em 1in;
                font-size: 11pt;
            }
        """,
        "default": """
            body {
                font-family: Georgia, serif;
                font-size: 1em;
                line-height: 1.5;
                margin: 1em;
            }
            h1 { font-size: 1.8em; margin: 1em 0 0.5em; }
            h2 { font-size: 1.4em; margin: 0.8em 0 0.4em; }
            h3 { font-size: 1.2em; margin: 0.6em 0 0.3em; }
            p { margin: 0.5em 0; }
            blockquote {
                margin: 1em 2em;
                font-style: italic;
            }
        """,
    }

    def __init__(
        self,
        template: str = "default",
        page_size: str = "A4",  # Not used for EPUB but kept for interface
        language: str = "vi",
    ):
        """
        Initialize EPUB renderer.

        Args:
            template: Template name (affects CSS)
            page_size: Not used for EPUB
            language: Book language code
        """
        super().__init__(template, page_size)

        if not HAS_EBOOKLIB:
            logger.warning("ebooklib not installed. EPUB rendering will be simulated.")

        self.language = language
        self.css = self.TEMPLATE_CSS.get(template, self.TEMPLATE_CSS["default"])

        logger.info(f"EPUBRenderer initialized: {template}, {language}")

    def render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List,
        output_path: str,
        section_manager: Optional[Any] = None,
    ) -> Path:
        """
        Render to EPUB file.

        Args:
            lip: LayoutIntentPackage
            flowed_blocks: Flowed blocks from executor
            output_path: Output file path
            section_manager: Optional section manager

        Returns:
            Path to created file
        """
        logger.info(f"Rendering EPUB: {len(flowed_blocks)} blocks")

        output_path = Path(output_path)

        if not HAS_EBOOKLIB:
            return self._simulate_render(lip, flowed_blocks, output_path)

        # Create EPUB book
        book = epub.EpubBook()

        # Set metadata
        self._set_metadata(book, lip)

        # Add CSS
        css_item = self._create_css(book)

        # Create chapters
        chapters: List[epub.EpubHtml] = []
        spine: List[Any] = ['nav']

        # Title page
        title_page = self._create_title_page(book, lip, css_item)
        if title_page:
            chapters.append(title_page)
            spine.append(title_page)

        # Group blocks into chapters
        chapter_groups = self._group_blocks_into_chapters(flowed_blocks)

        # Create chapter files
        for i, (chapter_title, blocks) in enumerate(chapter_groups):
            chapter = self._create_chapter(
                book,
                chapter_title,
                blocks,
                i + 1,
                css_item,
            )
            chapters.append(chapter)
            spine.append(chapter)

        # Create TOC
        book.toc = self._create_toc(chapters, lip)

        # Add navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Set spine
        book.spine = spine

        # Write EPUB
        epub.write_epub(str(output_path), book, {})

        logger.info(f"EPUB saved: {output_path}")

        return output_path

    def _simulate_render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List,
        output_path: Path,
    ) -> Path:
        """Simulate render when ebooklib not available"""
        import zipfile
        import io

        # Create a minimal valid EPUB structure
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first and uncompressed
            zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

            # container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            zf.writestr('META-INF/container.xml', container_xml)

            # Simple content.opf
            content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="uid">urn:uuid:{uuid.uuid4()}</dc:identifier>
        <dc:title>{self._escape_html(lip.title or "Untitled")}</dc:title>
        <dc:language>{self.language}</dc:language>
    </metadata>
    <manifest>
        <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
        <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    </manifest>
    <spine>
        <itemref idref="content"/>
    </spine>
</package>'''
            zf.writestr('OEBPS/content.opf', content_opf)

            # Simple nav.xhtml
            nav_xhtml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
<nav epub:type="toc"><ol><li><a href="content.xhtml">Content</a></li></ol></nav>
</body>
</html>'''
            zf.writestr('OEBPS/nav.xhtml', nav_xhtml)

            # Content
            content_parts = [f'<h1>{self._escape_html(lip.title or "Untitled")}</h1>']
            for fb in flowed_blocks:
                block = fb.block
                content_parts.append(f'<p>[{block.type.value}] {self._escape_html(block.content[:200])}</p>')

            content_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{self._escape_html(lip.title or "Untitled")}</title></head>
<body>
{"".join(content_parts)}
<p>[EPUB SIMULATION - ebooklib not installed]</p>
</body>
</html>'''
            zf.writestr('OEBPS/content.xhtml', content_xhtml)

        logger.info(f"Simulated EPUB saved: {output_path}")

        return output_path

    def _set_metadata(self, book, lip: LayoutIntentPackage):
        """Set EPUB metadata"""
        # Identifier
        book.set_identifier(f"id-{uuid.uuid4().hex[:8]}")

        # Title
        book.set_title(lip.title or "Untitled")

        # Language
        book.set_language(self.language)

        # Author
        if lip.author:
            book.add_author(lip.author)

        # Additional metadata
        book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))
        book.add_metadata('DC', 'publisher', 'AI Publishing System')

        # Description from notes
        if lip.notes:
            book.add_metadata('DC', 'description', ' '.join(lip.notes[:3]))

    def _create_css(self, book) -> Any:
        """Create and add CSS stylesheet"""
        css = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self.css.encode('utf-8'),
        )
        book.add_item(css)
        return css

    def _create_title_page(
        self,
        book,
        lip: LayoutIntentPackage,
        css_item,
    ) -> Optional[Any]:
        """Create title page"""
        if not lip.title:
            return None

        html_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{self._escape_html(lip.title)}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <div class="title-page">
        <h1>{self._escape_html(lip.title)}</h1>
"""

        if lip.subtitle:
            html_content += f'        <p class="subtitle">{self._escape_html(lip.subtitle)}</p>\n'

        if lip.author:
            html_content += f'        <p class="author">{self._escape_html(lip.author)}</p>\n'

        html_content += """    </div>
</body>
</html>"""

        title_page = epub.EpubHtml(
            title="Title Page",
            file_name="title.xhtml",
            lang=self.language,
        )
        title_page.content = html_content.encode('utf-8')
        title_page.add_item(css_item)
        book.add_item(title_page)

        return title_page

    def _group_blocks_into_chapters(
        self,
        flowed_blocks: List,
    ) -> List[Tuple[str, List]]:
        """
        Group blocks into chapters.

        Returns list of (chapter_title, blocks) tuples.
        """
        groups: List[Tuple[str, List]] = []
        current_title = "Introduction"
        current_blocks: List = []

        for fb in flowed_blocks:
            block = fb.block

            # Check if this is a chapter start
            if block.type == BlockType.CHAPTER:
                # Save previous chapter
                if current_blocks:
                    groups.append((current_title, current_blocks))

                # Start new chapter
                current_title = block.content[:50]  # Truncate long titles
                current_blocks = [fb]
            else:
                current_blocks.append(fb)

        # Save last chapter
        if current_blocks:
            groups.append((current_title, current_blocks))

        return groups

    def _create_chapter(
        self,
        book,
        title: str,
        flowed_blocks: List,
        chapter_num: int,
        css_item,
    ) -> Any:
        """Create a chapter XHTML file"""
        # Build HTML content
        html_parts = [
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{self._escape_html(title)}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
"""
        ]

        is_first_para = True

        for fb in flowed_blocks:
            block = fb.block
            html = self._block_to_html(block, is_first_para)
            html_parts.append(html)

            if block.type == BlockType.PARAGRAPH:
                is_first_para = False

        html_parts.append("</body>\n</html>")

        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"chapter_{chapter_num:03d}.xhtml",
            lang=self.language,
        )
        chapter.content = ''.join(html_parts).encode('utf-8')
        chapter.add_item(css_item)
        book.add_item(chapter)

        return chapter

    def _block_to_html(self, block: Block, is_first_para: bool = False) -> str:
        """Convert a block to HTML"""
        content = self._escape_html(block.content)

        # Map block type to HTML
        type_map = {
            BlockType.TITLE: f"<h1>{content}</h1>\n",
            BlockType.SUBTITLE: f'<p class="subtitle">{content}</p>\n',
            BlockType.CHAPTER: f"<h1>{content}</h1>\n",
            BlockType.SECTION: f"<h2>{content}</h2>\n",
            BlockType.HEADING_1: f"<h1>{content}</h1>\n",
            BlockType.HEADING_2: f"<h2>{content}</h2>\n",
            BlockType.HEADING_3: f"<h3>{content}</h3>\n",
            BlockType.QUOTE: f"<blockquote><p>{content}</p></blockquote>\n",
            BlockType.CODE: f"<pre><code>{content}</code></pre>\n",
            BlockType.LIST: f"<p>{content}</p>\n",  # Simplified
            BlockType.FOOTNOTE: f'<p class="footnote">{content}</p>\n',
        }

        if block.type in type_map:
            return type_map[block.type]

        # Default: paragraph
        css_class = "first" if is_first_para else ""
        if css_class:
            return f'<p class="{css_class}">{content}</p>\n'
        return f'<p>{content}</p>\n'

    def _create_toc(
        self,
        chapters: List,
        lip: LayoutIntentPackage,
    ) -> List:
        """Create table of contents"""
        toc = []

        for chapter in chapters:
            if chapter:
                toc.append(epub.Link(
                    chapter.file_name,
                    chapter.title,
                    chapter.file_name.replace('.xhtml', ''),
                ))

        return toc

    def _escape_html(self, text: str) -> str:
        """Escape HTML entities"""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    @classmethod
    def supports_format(cls, format_name: str) -> bool:
        return format_name.lower() == "epub"

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        return ["epub"]
