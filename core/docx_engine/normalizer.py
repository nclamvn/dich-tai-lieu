"""
Document Normalizer - Convert Agent 2 output to NormalizedDocument.

Agent 2 Output Contract:
book_output/
├── manifest.json      # Document DNA + metadata
├── chapters/
│   ├── 001_chapter.md
│   ├── 002_chapter.md
│   └── ...
└── glossary.json      # Optional
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Tuple
import logging

from .models import (
    NormalizedDocument, DocumentMeta, DocumentDNA,
    Chapter, ContentBlock, BlockType, TextRun, InlineStyle,
    FrontMatter, FrontMatterItem, TableOfContents, TocItem,
    Glossary, GlossaryItem, ListItem, ListType, TableData, TableCell
)

logger = logging.getLogger(__name__)


class DocumentNormalizer:
    """
    Converts Agent 2 output folder to NormalizedDocument.

    Usage:
        normalizer = DocumentNormalizer()
        doc = normalizer.from_agent2_output("book_output/")
    """

    def from_agent2_output(self, folder_path: str) -> NormalizedDocument:
        """
        Main entry point - read Agent 2 output folder.

        Args:
            folder_path: Path to Agent 2 output folder

        Returns:
            NormalizedDocument ready for rendering
        """
        folder = Path(folder_path)

        if not folder.exists():
            raise FileNotFoundError(f"Agent 2 output folder not found: {folder}")

        # Read manifest
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {folder}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Extract metadata and DNA
        meta = self._extract_meta(manifest)
        dna = self._extract_dna(manifest)

        # Read chapters
        chapters_dir = folder / "chapters"
        chapters = self._read_chapters(chapters_dir)

        # Read glossary if exists
        glossary = None
        glossary_path = folder / "glossary.json"
        if glossary_path.exists():
            glossary = self._read_glossary(glossary_path)

        # Build TOC from chapters
        toc = self._build_toc(chapters)

        # Extract front matter if present in manifest
        front_matter = self._extract_front_matter(manifest)

        return NormalizedDocument(
            meta=meta,
            dna=dna,
            front_matter=front_matter,
            toc=toc,
            chapters=chapters,
            glossary=glossary
        )

    def from_markdown(self, markdown_content: str, meta: Optional[DocumentMeta] = None) -> NormalizedDocument:
        """
        Alternative: Parse a single markdown string.
        Useful for simpler documents without chapter structure.
        """
        if meta is None:
            meta = DocumentMeta(title="Untitled")

        blocks = self._parse_markdown(markdown_content)

        # Create single chapter
        chapters = [Chapter(
            number=1,
            title=meta.title,
            content=blocks
        )]

        return NormalizedDocument(
            meta=meta,
            dna=DocumentDNA(),
            chapters=chapters,
            toc=self._build_toc(chapters)
        )

    def _extract_meta(self, manifest: dict) -> DocumentMeta:
        """Extract DocumentMeta from manifest"""
        metadata = manifest.get('metadata', {})

        return DocumentMeta(
            title=metadata.get('title', 'Untitled'),
            subtitle=metadata.get('subtitle'),
            author=metadata.get('author', 'Unknown'),
            translator=metadata.get('translator'),
            publisher=metadata.get('publisher'),
            date=metadata.get('date'),
            language=metadata.get('target_language', 'vi'),
            running_title=metadata.get('running_title') or metadata.get('title', '')[:30]
        )

    def _extract_dna(self, manifest: dict) -> DocumentDNA:
        """Extract DocumentDNA from manifest"""
        dna_data = manifest.get('dna', {})

        return DocumentDNA(
            genre=dna_data.get('genre', 'general'),
            tone=dna_data.get('tone', 'neutral'),
            has_formulas=dna_data.get('has_formulas', False),
            has_code=dna_data.get('has_code', False),
            has_tables=dna_data.get('has_tables', False),
            source_language=dna_data.get('source_language', 'en'),
            target_language=dna_data.get('target_language', 'vi'),
            characters=dna_data.get('characters', []),
            key_terms=dna_data.get('key_terms', {})
        )

    def _extract_front_matter(self, manifest: dict) -> FrontMatter:
        """Extract front matter sections from manifest"""
        items = []
        front = manifest.get('front_matter', {})

        for fm_type in ['dedication', 'preface', 'acknowledgments', 'foreword']:
            if fm_type in front:
                content = front[fm_type]
                blocks = self._parse_markdown(content) if isinstance(content, str) else []
                items.append(FrontMatterItem(
                    type=fm_type,
                    title=fm_type.title(),
                    content=blocks
                ))

        return FrontMatter(items=items)

    def _read_chapters(self, chapters_dir: Path) -> List[Chapter]:
        """Read all chapter files from chapters/ directory"""
        chapters = []

        if not chapters_dir.exists():
            logger.warning(f"Chapters directory not found: {chapters_dir}")
            return chapters

        # Sort chapter files by name (001_xxx.md, 002_xxx.md, etc.)
        chapter_files = sorted(chapters_dir.glob("*.md"))

        for i, chapter_file in enumerate(chapter_files, start=1):
            chapter = self._read_chapter(chapter_file, i)
            if chapter:
                chapters.append(chapter)

        return chapters

    def _read_chapter(self, file_path: Path, default_number: int) -> Optional[Chapter]:
        """Read and parse a single chapter file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract chapter number from filename (e.g., 001_chapter.md → 1)
            match = re.match(r'^(\d+)', file_path.stem)
            chapter_num = int(match.group(1)) if match else default_number

            # Parse markdown content
            blocks = self._parse_markdown(content)

            # Extract title from first heading or filename
            title = self._extract_chapter_title(blocks, file_path.stem)

            return Chapter(
                number=chapter_num,
                title=title,
                content=blocks
            )

        except Exception as e:
            logger.error(f"Error reading chapter {file_path}: {e}")
            return None

    def _extract_chapter_title(self, blocks: List[ContentBlock], fallback: str) -> str:
        """Extract title from first H1 heading"""
        for block in blocks:
            if block.type == BlockType.HEADING and block.level == 1:
                return block.content if isinstance(block.content, str) else str(block.content)
        return fallback.replace('_', ' ').title()

    def _parse_markdown(self, content: str) -> List[ContentBlock]:
        """
        Parse markdown content into ContentBlocks.
        Handles: headings, paragraphs, lists, code blocks, quotes, tables.
        """
        blocks = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Heading
            if line.startswith('#'):
                block, consumed = self._parse_heading(lines, i)
                blocks.append(block)
                i += consumed
                continue

            # Code block
            if line.startswith('```'):
                block, consumed = self._parse_code_block(lines, i)
                blocks.append(block)
                i += consumed
                continue

            # Blockquote
            if line.startswith('>'):
                block, consumed = self._parse_blockquote(lines, i)
                blocks.append(block)
                i += consumed
                continue

            # List (bullet or numbered)
            if re.match(r'^[\-\*\+]\s', line) or re.match(r'^\d+\.\s', line):
                block, consumed = self._parse_list(lines, i)
                blocks.append(block)
                i += consumed
                continue

            # Table
            if '|' in line and i + 1 < len(lines) and '---' in lines[i + 1]:
                block, consumed = self._parse_table(lines, i)
                if block:
                    blocks.append(block)
                    i += consumed
                    continue

            # Default: paragraph
            block, consumed = self._parse_paragraph(lines, i)
            blocks.append(block)
            i += consumed

        return blocks

    def _parse_heading(self, lines: List[str], start: int) -> Tuple[ContentBlock, int]:
        """Parse a heading line"""
        line = lines[start]
        match = re.match(r'^(#{1,6})\s+(.+)', line)

        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            return ContentBlock(type=BlockType.HEADING, level=level, content=text), 1

        return ContentBlock(type=BlockType.PARAGRAPH, content=line), 1

    def _parse_code_block(self, lines: List[str], start: int) -> Tuple[ContentBlock, int]:
        """Parse a fenced code block"""
        first_line = lines[start]
        language = first_line[3:].strip()  # Extract language after ```

        code_lines = []
        i = start + 1

        while i < len(lines):
            if lines[i].startswith('```'):
                i += 1
                break
            code_lines.append(lines[i])
            i += 1

        code_content = '\n'.join(code_lines)

        return ContentBlock(
            type=BlockType.CODE,
            content=code_content,
            style_hints={'language': language}
        ), i - start

    def _parse_blockquote(self, lines: List[str], start: int) -> Tuple[ContentBlock, int]:
        """Parse a blockquote"""
        quote_lines = []
        i = start

        while i < len(lines) and lines[i].startswith('>'):
            quote_lines.append(lines[i][1:].strip())
            i += 1

        quote_content = ' '.join(quote_lines)

        return ContentBlock(type=BlockType.QUOTE, content=quote_content), i - start

    def _parse_list(self, lines: List[str], start: int) -> Tuple[ContentBlock, int]:
        """Parse a list (bullet or numbered)"""
        items = []
        i = start

        # Detect list type
        first_line = lines[start]
        is_numbered = bool(re.match(r'^\d+\.\s', first_line))
        list_type = ListType.NUMBERED if is_numbered else ListType.BULLET

        pattern = r'^\d+\.\s' if is_numbered else r'^[\-\*\+]\s'

        while i < len(lines):
            line = lines[i]
            match = re.match(pattern, line)

            if match:
                item_text = line[match.end():].strip()
                text_runs = self._parse_inline(item_text)
                items.append(ListItem(content=text_runs))
                i += 1
            elif line.startswith('  ') and items:
                # Continuation of previous item
                items[-1].content.append(TextRun(text=' ' + line.strip()))
                i += 1
            else:
                break

        return ContentBlock(
            type=BlockType.LIST,
            content=items,
            style_hints={'list_type': list_type.value}
        ), i - start

    def _parse_table(self, lines: List[str], start: int) -> Tuple[Optional[ContentBlock], int]:
        """Parse a markdown table"""
        rows = []
        i = start

        while i < len(lines) and '|' in lines[i]:
            line = lines[i].strip()

            # Skip separator line
            if re.match(r'^[\|\s\-:]+$', line):
                i += 1
                continue

            # Parse cells
            cells = []
            cell_texts = [c.strip() for c in line.split('|')[1:-1]]  # Remove empty first/last

            is_header = (i == start)
            for cell_text in cell_texts:
                text_runs = self._parse_inline(cell_text)
                cells.append(TableCell(content=text_runs, is_header=is_header))

            if cells:
                rows.append(cells)
            i += 1

        if not rows:
            return None, 1

        return ContentBlock(
            type=BlockType.TABLE,
            content=TableData(rows=rows, has_header_row=True)
        ), i - start

    def _parse_paragraph(self, lines: List[str], start: int) -> Tuple[ContentBlock, int]:
        """Parse a paragraph (consecutive non-empty lines)"""
        para_lines = []
        i = start

        while i < len(lines):
            line = lines[i]

            # Stop at empty line or special syntax
            if not line.strip():
                break
            if line.startswith('#') or line.startswith('```') or line.startswith('>'):
                break
            if re.match(r'^[\-\*\+]\s', line) or re.match(r'^\d+\.\s', line):
                break

            para_lines.append(line.strip())
            i += 1

        para_text = ' '.join(para_lines)
        text_runs = self._parse_inline(para_text)

        return ContentBlock(type=BlockType.PARAGRAPH, content=text_runs), max(1, i - start)

    def _parse_inline(self, text: str) -> List[TextRun]:
        """
        Parse inline formatting (bold, italic, code, etc.)
        Returns list of TextRuns with appropriate styles.
        """
        runs = []

        # Regex patterns for inline formatting
        # Order matters: check longer patterns first
        pattern = re.compile(r'''
            (\*\*\*(.+?)\*\*\*)   |  # Bold+Italic ***text***
            (\*\*(.+?)\*\*)       |  # Bold **text**
            (__(.+?)__)           |  # Bold __text__
            (\*(.+?)\*)           |  # Italic *text*
            (_(.+?)_)             |  # Italic _text_
            (`(.+?)`)             |  # Inline code `text`
            (~~(.+?)~~)              # Strikethrough ~~text~~
        ''', re.VERBOSE)

        last_end = 0

        for match in pattern.finditer(text):
            # Add plain text before match
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    runs.append(TextRun(text=plain))

            # Determine which group matched
            if match.group(1):  # Bold+Italic
                runs.append(TextRun(
                    text=match.group(2),
                    style=InlineStyle(bold=True, italic=True)
                ))
            elif match.group(3):  # Bold **
                runs.append(TextRun(
                    text=match.group(4),
                    style=InlineStyle(bold=True)
                ))
            elif match.group(5):  # Bold __
                runs.append(TextRun(
                    text=match.group(6),
                    style=InlineStyle(bold=True)
                ))
            elif match.group(7):  # Italic *
                runs.append(TextRun(
                    text=match.group(8),
                    style=InlineStyle(italic=True)
                ))
            elif match.group(9):  # Italic _
                runs.append(TextRun(
                    text=match.group(10),
                    style=InlineStyle(italic=True)
                ))
            elif match.group(11):  # Code
                runs.append(TextRun(
                    text=match.group(12),
                    style=InlineStyle(code=True)
                ))
            elif match.group(13):  # Strikethrough
                runs.append(TextRun(
                    text=match.group(14),
                    style=InlineStyle(strikethrough=True)
                ))

            last_end = match.end()

        # Add remaining plain text
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                runs.append(TextRun(text=remaining))

        # If no formatting found, return single run
        if not runs:
            runs.append(TextRun(text=text))

        return runs

    def _read_glossary(self, file_path: Path) -> Glossary:
        """Read glossary.json file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = []
        glossary_items = data if isinstance(data, list) else data.get('items', [])

        for item in glossary_items:
            items.append(GlossaryItem(
                term=item.get('term', ''),
                definition=item.get('definition', ''),
                source_term=item.get('source_term')
            ))

        return Glossary(
            title=data.get('title', 'Glossary') if isinstance(data, dict) else 'Glossary',
            items=items
        )

    def _build_toc(self, chapters: List[Chapter]) -> TableOfContents:
        """Build table of contents from chapters"""
        items = []

        for chapter in chapters:
            # Add chapter entry
            items.append(TocItem(
                title=chapter.title,
                level=1,
                chapter_number=chapter.number
            ))

            # Add section entries (H2, H3)
            for block in chapter.content:
                if block.type == BlockType.HEADING and block.level in [2, 3]:
                    title = block.content if isinstance(block.content, str) else ''
                    items.append(TocItem(
                        title=title,
                        level=block.level  # H2 → level 2, H3 → level 3
                    ))

        return TableOfContents(items=items, auto_generate=True)
