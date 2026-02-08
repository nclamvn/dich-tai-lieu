"""
PDF Renderer using ReportLab.

Converts NormalizedDocument to professional PDF output.
Reuses DocumentNormalizer and NormalizedDocument from docx_engine.
"""

import logging
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, ListFlowable, ListItem as RLListItem
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# Reuse from docx_engine (DO NOT DUPLICATE)
from core.docx_engine.models import (
    NormalizedDocument, DocumentMeta, DocumentDNA,
    Chapter, ContentBlock, BlockType, TextRun, InlineStyle,
    TableOfContents, TocItem, Glossary, GlossaryItem,
    ListItem, ListType, TableData, TableCell
)
from core.docx_engine.normalizer import DocumentNormalizer

from .templates import PdfTemplate, create_pdf_template
from .style_builder import FontManager, StyleBuilder
from core.i18n import get_string, format_chapter_title


logger = logging.getLogger(__name__)


class PdfRenderer:
    """
    PDF Renderer using ReportLab.

    Takes NormalizedDocument and produces professional PDF output.
    Supports multiple templates (ebook, academic, business).
    """

    def __init__(
        self,
        template: str = "ebook",
        custom_template: Optional[PdfTemplate] = None
    ):
        """
        Initialize PDF renderer.

        Args:
            template: Template name ('ebook', 'academic', 'business')
            custom_template: Optional custom PdfTemplate instance
        """
        if custom_template:
            self.template = custom_template
        else:
            self.template = create_pdf_template(template)

        # Initialize font manager and style builder
        self.font_manager = FontManager()
        self._fonts_registered = False

        self.style_builder: Optional[StyleBuilder] = None
        self._styles: Dict[str, ParagraphStyle] = {}

        # Page tracking
        self._page_number = 0
        self._chapter_pages: Dict[int, int] = {}

    def _ensure_fonts_registered(self):
        """Ensure fonts are registered before rendering."""
        if not self._fonts_registered:
            self.font_manager.register_dejavu_fonts()
            self.font_manager.register_template_fonts(self.template)
            self._fonts_registered = True

    def _ensure_styles_built(self):
        """Ensure styles are built before rendering."""
        if not self._styles:
            self._ensure_fonts_registered()
            # Pass font_manager to StyleBuilder for fallback font resolution
            self.style_builder = StyleBuilder(self.template, self.font_manager)
            self._styles = self.style_builder.build_all_styles()

    def render(
        self,
        document: NormalizedDocument,
        output_path: str,
        include_toc: bool = True,
        include_glossary: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Path:
        """
        Render NormalizedDocument to PDF.

        Args:
            document: Normalized document to render
            output_path: Output PDF file path
            include_toc: Include table of contents
            include_glossary: Include glossary section
            progress_callback: Optional callback(current, total, message)

        Returns:
            Path to generated PDF
        """
        self._ensure_styles_built()

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Get page spec from template
        page_spec = self.template.get_page_spec()

        # Create document
        doc = SimpleDocTemplate(
            str(output),
            pagesize=page_spec.size,
            topMargin=page_spec.top_margin,
            rightMargin=page_spec.right_margin,
            bottomMargin=page_spec.bottom_margin,
            leftMargin=page_spec.left_margin,
            title=document.meta.title,
            author=document.meta.author
        )

        # Build story (content flowables)
        story = []
        total_items = len(document.chapters) + 3  # +3 for title, toc, glossary
        current_item = 0

        # 1. Title page
        if progress_callback:
            progress_callback(current_item, total_items, "Rendering title page...")
        self._add_title_page(story, document.meta)
        current_item += 1

        # 2. Table of contents
        lang = document.meta.language or "en"
        if include_toc and document.toc.items:
            if progress_callback:
                progress_callback(current_item, total_items, "Rendering table of contents...")
            self._add_toc(story, document.toc, lang=lang)
        current_item += 1

        # 3. Chapters
        chapter_break = self.template.get_chapter_break()

        for chapter in document.chapters:
            if progress_callback:
                progress_callback(
                    current_item,
                    total_items,
                    f"Rendering chapter {chapter.number}: {chapter.title[:30]}..."
                )

            self._add_chapter(story, chapter, chapter_break, lang=lang)
            current_item += 1

        # 4. Glossary
        if include_glossary and document.glossary and document.glossary.items:
            if progress_callback:
                progress_callback(current_item, total_items, "Rendering glossary...")
            self._add_glossary(story, document.glossary)

        # Build PDF
        if progress_callback:
            progress_callback(total_items, total_items, "Finalizing PDF...")

        doc.build(
            story,
            onFirstPage=self._make_page_callback(document, is_first=True),
            onLaterPages=self._make_page_callback(document, is_first=False)
        )

        logger.info(f"PDF rendered: {output}")
        return output

    def render_from_folder(
        self,
        source_folder: str,
        output_path: str,
        include_toc: bool = True,
        include_glossary: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Path:
        """
        Render from Agent 2 output folder.

        Args:
            source_folder: Path to folder with manifest.json and chapters/
            output_path: Output PDF file path
            include_toc: Include table of contents
            include_glossary: Include glossary
            progress_callback: Optional progress callback

        Returns:
            Path to generated PDF
        """
        normalizer = DocumentNormalizer()
        document = normalizer.from_agent2_output(source_folder)
        return self.render(document, output_path, include_toc, include_glossary, progress_callback)

    def render_markdown(
        self,
        markdown_content: str,
        output_path: str,
        title: str = "Document",
        author: str = "Unknown",
        include_toc: bool = True
    ) -> Path:
        """
        Render markdown content to PDF.

        Args:
            markdown_content: Markdown string
            output_path: Output PDF path
            title: Document title
            author: Author name
            include_toc: Include table of contents

        Returns:
            Path to generated PDF
        """
        normalizer = DocumentNormalizer()
        meta = DocumentMeta(title=title, author=author)
        document = normalizer.from_markdown(markdown_content, meta)
        return self.render(document, output_path, include_toc, include_glossary=False)

    def _add_title_page(self, story: List, meta: DocumentMeta):
        """Add title page to story."""
        # Spacer at top
        story.append(Spacer(1, 4*cm))

        # Title
        story.append(Paragraph(
            self._escape_html(meta.title),
            self._styles['title']
        ))

        # Subtitle
        if meta.subtitle:
            story.append(Paragraph(
                self._escape_html(meta.subtitle),
                self._styles['subtitle']
            ))

        # Author
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph(
            self._escape_html(meta.author),
            self._styles['author']
        ))

        # Translator
        if meta.translator:
            lang = meta.language or "en"
            translator_label = get_string("translator", lang)
            story.append(Paragraph(
                f"{translator_label}: {self._escape_html(meta.translator)}",
                self._styles['author']
            ))

        # Publisher and date
        if meta.publisher or meta.date:
            story.append(Spacer(1, 2*cm))
            if meta.publisher:
                story.append(Paragraph(
                    self._escape_html(meta.publisher),
                    self._styles['author']
                ))
            if meta.date:
                story.append(Paragraph(
                    self._escape_html(meta.date),
                    self._styles['author']
                ))

        story.append(PageBreak())

    def _add_toc(self, story: List, toc: TableOfContents, lang: str = "en"):
        """Add table of contents."""
        # TOC title
        story.append(Paragraph(
            self._escape_html(toc.title),
            self._styles.get('toc_title', self._styles['heading_1'])
        ))
        story.append(Spacer(1, 0.5*cm))

        # TOC entries
        for item in toc.items:
            style_name = f'toc_{item.level}' if item.level <= 3 else 'toc_3'
            style = self._styles.get(style_name, self._styles['body'])

            # Format entry
            if item.chapter_number:
                text = self._escape_html(format_chapter_title(item.chapter_number, item.title, lang))
            else:
                text = self._escape_html(item.title)

            story.append(Paragraph(text, style))

        story.append(PageBreak())

    def _add_chapter(self, story: List, chapter: Chapter, chapter_break: str, lang: str = "en"):
        """Add chapter to story."""
        # Page break before chapter (if not first and template requires)
        if chapter_break == 'page' and chapter.number > 1:
            story.append(PageBreak())

        # Chapter title
        title_text = chapter.title if chapter.title else format_chapter_title(chapter.number, "", lang)

        story.append(Paragraph(
            self._escape_html(title_text),
            self._styles['heading_1']
        ))

        # Epigraph if present
        if chapter.epigraph:
            story.append(Paragraph(
                self._escape_html(chapter.epigraph),
                self._styles.get('epigraph', self._styles['quote'])
            ))

        # Chapter content
        is_first_para = True
        for block in chapter.content:
            elements = self._render_block(block, is_first_para)
            story.extend(elements)

            # Track first paragraph (for indent handling)
            if block.type == BlockType.PARAGRAPH:
                is_first_para = False
            elif block.type == BlockType.HEADING:
                is_first_para = True

    def _render_block(self, block: ContentBlock, is_first_para: bool = False) -> List:
        """Render a content block to flowables."""
        elements = []

        if block.type == BlockType.HEADING:
            level = min(block.level, 3)
            style = self._styles.get(f'heading_{level}', self._styles['heading_1'])
            text = block.content if isinstance(block.content, str) else self._runs_to_text(block.content)
            elements.append(Paragraph(self._escape_html(text), style))

        elif block.type == BlockType.PARAGRAPH:
            style_name = 'body_first' if is_first_para else 'body'
            style = self._styles.get(style_name, self._styles['body'])
            text = self._format_runs(block.content) if isinstance(block.content, list) else self._escape_html(str(block.content))
            elements.append(Paragraph(text, style))

        elif block.type == BlockType.QUOTE:
            style = self._styles.get('quote', self._styles['body'])
            text = block.content if isinstance(block.content, str) else self._runs_to_text(block.content)
            elements.append(Paragraph(self._escape_html(text), style))

        elif block.type == BlockType.CODE:
            style = self._styles.get('code', self._styles['body'])
            code_text = block.content if isinstance(block.content, str) else str(block.content)
            # Preserve line breaks in code
            for line in code_text.split('\n'):
                elements.append(Paragraph(
                    self._escape_html(line) or '&nbsp;',
                    style
                ))

        elif block.type == BlockType.LIST:
            elements.extend(self._render_list(block))

        elif block.type == BlockType.TABLE:
            elements.extend(self._render_table(block))

        elif block.type == BlockType.PAGE_BREAK:
            elements.append(PageBreak())

        return elements

    def _render_list(self, block: ContentBlock) -> List:
        """Render a list block."""
        elements = []
        items = block.content if isinstance(block.content, list) else []
        list_type = block.style_hints.get('list_type', 'bullet')

        style = self._styles.get('list_item', self._styles['body'])

        for i, item in enumerate(items):
            if isinstance(item, ListItem):
                text = self._format_runs(item.content)
            else:
                text = self._escape_html(str(item))

            # Add bullet/number prefix
            if list_type == 'numbered':
                prefix = f"{i+1}. "
            else:
                prefix = "• "

            elements.append(Paragraph(prefix + text, style))

        return elements

    def _render_table(self, block: ContentBlock) -> List:
        """Render a table block."""
        elements = []

        if not isinstance(block.content, TableData):
            return elements

        table_data = block.content
        data = []

        for row in table_data.rows:
            row_data = []
            for cell in row:
                text = self._format_runs(cell.content) if isinstance(cell.content, list) else str(cell.content)
                style = self._styles.get('table_header' if cell.is_header else 'table_cell', self._styles['body'])
                row_data.append(Paragraph(text, style))
            data.append(row_data)

        if not data:
            return elements

        # Create table
        table = Table(data)

        # Style table
        table_style = [
            ('GRID', (0, 0), (-1, -1), 0.5, black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]

        # Header row styling
        if table_data.has_header_row and data:
            header_bg = self.template.ACCENT_COLOR if hasattr(self.template, 'ACCENT_COLOR') else HexColor('#0070C0')
            table_style.extend([
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), self._get_bold_font()),
            ])

        # Alternate row colors
        for i in range(1, len(data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F5F5F5')))

        table.setStyle(TableStyle(table_style))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        # Caption
        if block.caption:
            caption_style = self._styles.get('caption', self._styles['body'])
            elements.append(Paragraph(self._escape_html(block.caption), caption_style))

        return elements

    def _add_glossary(self, story: List, glossary: Glossary):
        """Add glossary section."""
        story.append(PageBreak())

        # Glossary title
        story.append(Paragraph(
            self._escape_html(glossary.title),
            self._styles.get('heading_1', self._styles['title'])
        ))
        story.append(Spacer(1, 0.5*cm))

        term_style = self._styles.get('glossary_term', self._styles['body'])
        def_style = self._styles.get('glossary_def', self._styles['body'])

        for item in glossary.items:
            # Term
            term_text = self._escape_html(item.term)
            if item.source_term:
                term_text += f" ({self._escape_html(item.source_term)})"
            story.append(Paragraph(term_text, term_style))

            # Definition
            story.append(Paragraph(
                self._escape_html(item.definition),
                def_style
            ))

    def _format_runs(self, runs: List[TextRun]) -> str:
        """Convert TextRuns to formatted HTML for ReportLab."""
        if not runs:
            return ""

        result = []
        for run in runs:
            text = self._escape_html(run.text)

            if run.style:
                if run.style.bold and run.style.italic:
                    text = f"<b><i>{text}</i></b>"
                elif run.style.bold:
                    text = f"<b>{text}</b>"
                elif run.style.italic:
                    text = f"<i>{text}</i>"

                if run.style.code:
                    mono_font = self._get_mono_font()
                    text = f"<font face='{mono_font}'>{text}</font>"
                if run.style.underline:
                    text = f"<u>{text}</u>"
                if run.style.strikethrough:
                    text = f"<strike>{text}</strike>"
                if run.style.superscript:
                    text = f"<super>{text}</super>"
                if run.style.subscript:
                    text = f"<sub>{text}</sub>"

            result.append(text)

        return ''.join(result)

    def _runs_to_text(self, runs: List) -> str:
        """Extract plain text from runs."""
        if isinstance(runs, str):
            return runs
        if isinstance(runs, list):
            return ''.join(r.text if isinstance(r, TextRun) else str(r) for r in runs)
        return str(runs)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))

    def _get_bold_font(self) -> str:
        """Get bold font name for current template."""
        if hasattr(self.template, 'SERIF'):
            font_name = f"{self.template.SERIF}-Bold"
        elif hasattr(self.template, 'SANS'):
            font_name = f"{self.template.SANS}-Bold"
        else:
            font_name = "Helvetica-Bold"
        return self.font_manager.get_font_name(font_name)

    def _get_mono_font(self) -> str:
        """Get monospace font name for current template."""
        if hasattr(self.template, 'MONO'):
            font_name = self.template.MONO
        else:
            font_name = "DejaVuSansMono"
        return self.font_manager.get_font_name(font_name)

    def _make_page_callback(self, document: NormalizedDocument, is_first: bool):
        """Create page callback for header/footer rendering."""
        hf_spec = self.template.get_header_footer()
        hf_style = self.style_builder.get_header_footer_style() if self.style_builder else None

        def callback(canvas, doc):
            # Skip header/footer on first page if configured
            if is_first and hf_spec.different_first_page:
                return

            canvas.saveState()
            page_width, page_height = doc.pagesize
            page_num = doc.page

            # Format placeholders
            def format_text(template: Optional[str]) -> str:
                if not template:
                    return ""
                return (template
                    .replace('{title}', document.meta.running_title or document.meta.title[:30])
                    .replace('{author}', document.meta.author)
                    .replace('{page}', str(page_num))
                    .replace('{date}', datetime.now().strftime('%Y-%m-%d')))

            # Draw header
            if hf_spec.show_header:
                y = page_height - 1*cm

                if hf_spec.header_left:
                    canvas.drawString(doc.leftMargin, y, format_text(hf_spec.header_left))
                if hf_spec.header_center:
                    canvas.drawCentredString(page_width/2, y, format_text(hf_spec.header_center))
                if hf_spec.header_right:
                    canvas.drawRightString(page_width - doc.rightMargin, y, format_text(hf_spec.header_right))

                if hf_spec.header_line:
                    canvas.line(doc.leftMargin, y - 3, page_width - doc.rightMargin, y - 3)

            # Draw footer
            if hf_spec.show_footer:
                y = 1.5*cm

                if hf_spec.footer_left:
                    canvas.drawString(doc.leftMargin, y, format_text(hf_spec.footer_left))
                if hf_spec.footer_center:
                    canvas.drawCentredString(page_width/2, y, format_text(hf_spec.footer_center))
                if hf_spec.footer_right:
                    canvas.drawRightString(page_width - doc.rightMargin, y, format_text(hf_spec.footer_right))

                if hf_spec.footer_line:
                    canvas.line(doc.leftMargin, y + 10, page_width - doc.rightMargin, y + 10)

            canvas.restoreState()

        return callback
