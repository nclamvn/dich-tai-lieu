#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Style Exporter - Export StyledDocument to Markdown format.

Supports:
- Heading levels (#, ##, ###, ####)
- Paragraphs with proper spacing
- Lists (bullet and numbered)
- Tables
- Code blocks
- Block quotes
- Table of Contents with anchor links
"""

import re
from pathlib import Path
from typing import Optional, List

from ..style_engine import (
    StyledDocument,
    StyledElement,
    StyledList,
    StyledListItem,
    StyledTable,
    StyledCodeBlock,
    StyledBlockquote,
    StyledFigure,
    StyledHorizontalRule,
)
from ..utils.constants import ELEMENT_TYPES
from ..toc_generator import TocGenerator, TocElement


class MarkdownStyleExporter:
    """
    Export StyledDocument to Markdown format.

    Usage:
        exporter = MarkdownStyleExporter()
        path = exporter.export(styled_doc, "output.md")
    """

    def __init__(
        self,
        include_toc: bool = True,
        toc_title: str = "Table of Contents",
        language: str = "en",
    ):
        """
        Initialize exporter.

        Args:
            include_toc: Whether to include table of contents
            toc_title: Title for TOC section
            language: Language for TOC title ("en" or "vi")
        """
        self.include_toc = include_toc
        self.toc_title = toc_title
        self.language = language
        self.toc_generator = TocGenerator(language=language)

    def export(self, styled_doc: StyledDocument, output_path: str) -> str:
        """
        Export StyledDocument to Markdown file.

        Args:
            styled_doc: StyledDocument with formatting
            output_path: Path for output file

        Returns:
            Absolute path to saved file
        """
        parts = []

        # Add document title if present
        if styled_doc.title:
            parts.append(f"# {styled_doc.title}")
            parts.append("")

        # Add TOC
        if self.include_toc and styled_doc.include_toc and styled_doc.toc:
            toc = self._generate_toc(styled_doc)
            parts.append(toc)
            parts.append("")
            parts.append("---")
            parts.append("")

        # Add all elements
        for element in styled_doc.elements:
            md = self._element_to_markdown(element)
            if md:
                parts.append(md)
                parts.append("")  # Blank line between elements

        # Join and clean up
        content = '\n'.join(parts)
        content = self._clean_markdown(content)

        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')

        return str(output_path.absolute())

    def _generate_toc(self, styled_doc: StyledDocument) -> str:
        """
        Generate Table of Contents with anchor links.

        Args:
            styled_doc: StyledDocument with TOC entries

        Returns:
            Markdown TOC string
        """
        lines = [f"## {self.toc_title}", ""]

        for entry in styled_doc.toc:
            if entry.level > styled_doc.toc_max_level:
                continue

            # Generate anchor from title
            anchor = self._heading_to_anchor(entry.title)

            # Indent based on level
            indent = "  " * (entry.level - 1)
            lines.append(f"{indent}- [{entry.title}](#{anchor})")

        return '\n'.join(lines)

    def _heading_to_anchor(self, title: str) -> str:
        """
        Convert heading text to URL-safe anchor.

        GitHub-style anchor generation:
        - Lowercase
        - Replace spaces with hyphens
        - Remove special characters except hyphens
        - Vietnamese characters preserved

        Args:
            title: Heading text

        Returns:
            URL-safe anchor string
        """
        anchor = title.lower()

        # Replace spaces with hyphens
        anchor = anchor.replace(' ', '-')

        # Remove special characters (keep letters, numbers, hyphens, Vietnamese chars)
        anchor = re.sub(r'[^\w\-\u00C0-\u024F\u1E00-\u1EFF]', '', anchor, flags=re.UNICODE)

        # Remove multiple consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)

        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')

        return anchor

    def _element_to_markdown(self, element: StyledElement) -> str:
        """
        Convert StyledElement to Markdown string.

        Args:
            element: StyledElement to convert

        Returns:
            Markdown string
        """
        element_type = element.type

        if element_type == ELEMENT_TYPES["HEADING"]:
            return self._heading_to_md(element)
        elif element_type == ELEMENT_TYPES["PARAGRAPH"]:
            return self._paragraph_to_md(element)
        elif element_type == ELEMENT_TYPES["LIST_BULLET"]:
            return self._bullet_list_to_md(element)
        elif element_type == ELEMENT_TYPES["LIST_NUMBERED"]:
            return self._numbered_list_to_md(element)
        elif element_type == ELEMENT_TYPES["TABLE"]:
            return self._table_to_md(element)
        elif element_type == ELEMENT_TYPES["CODE_BLOCK"]:
            return self._code_block_to_md(element)
        elif element_type == ELEMENT_TYPES["QUOTE"]:
            return self._quote_to_md(element)
        elif element_type == ELEMENT_TYPES["IMAGE"]:
            return self._figure_to_md(element)
        elif element_type == ELEMENT_TYPES["HORIZONTAL_RULE"]:
            return self._horizontal_rule_to_md()
        else:
            # Default: treat as paragraph
            return self._paragraph_to_md(element)

    def _heading_to_md(self, element: StyledElement) -> str:
        """Convert heading to Markdown."""
        level = element.level or 1
        prefix = '#' * min(level, 6)  # Markdown supports up to 6 levels
        return f"{prefix} {element.content}"

    def _paragraph_to_md(self, element: StyledElement) -> str:
        """Convert paragraph to Markdown."""
        text = element.content

        # Apply inline formatting if specified
        if element.bold and element.italic:
            text = f"***{text}***"
        elif element.bold:
            text = f"**{text}**"
        elif element.italic:
            text = f"*{text}*"

        return text

    def _bullet_list_to_md(self, element: StyledElement) -> str:
        """Convert bullet list to Markdown with proper nesting."""
        # Check if we have structured items
        if isinstance(element, StyledList) and element.items:
            return self._styled_list_to_md(element, "bullet")

        # Fallback: parse content as lines
        lines = element.content.split('\n')
        result = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Normalize bullet markers to -
            for marker in ['* ', '+ ', '• ', '○ ', '● ', '▪ ', '▫ ']:
                if line.startswith(marker):
                    line = '- ' + line[len(marker):]
                    break
            else:
                if not line.startswith('- '):
                    line = '- ' + line

            result.append(line)

        return '\n'.join(result)

    def _numbered_list_to_md(self, element: StyledElement) -> str:
        """Convert numbered list to Markdown with proper nesting."""
        # Check if we have structured items
        if isinstance(element, StyledList) and element.items:
            return self._styled_list_to_md(element, "numbered")

        # Fallback: parse content as lines
        lines = element.content.split('\n')
        result = []
        counter = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove existing numbering and renumber
            line = re.sub(r'^[\d\w]+[\.\)]\s*', '', line)
            line = re.sub(r'^\([^)]+\)\s*', '', line)
            result.append(f"{counter}. {line}")
            counter += 1

        return '\n'.join(result)

    def _styled_list_to_md(self, styled_list: StyledList, list_type: str) -> str:
        """Convert StyledList to Markdown with proper nesting."""
        result = []
        counters = {}  # Track counters per level for numbered lists

        for item in styled_list.items:
            level = item.level
            indent = "  " * level  # 2 spaces per indent level

            if list_type == "bullet":
                # Use different markers for different levels
                markers = ["-", "*", "+", "-"]
                marker = markers[level % len(markers)]
                result.append(f"{indent}{marker} {item.content}")
            else:
                # Numbered list - track counter per level
                if level not in counters:
                    counters[level] = 0
                counters[level] += 1
                # Reset lower level counters
                for l in list(counters.keys()):
                    if l > level:
                        del counters[l]
                result.append(f"{indent}{counters[level]}. {item.content}")

        return '\n'.join(result)

    def _table_to_md(self, element: StyledElement) -> str:
        """Convert table to Markdown with proper alignment."""
        # Check if we have structured table data
        if isinstance(element, StyledTable):
            return self._styled_table_to_md(element)

        # Fallback: process content as markdown
        content = element.content.strip()

        # Ensure proper table format
        lines = content.split('\n')
        result = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Ensure line starts and ends with |
            if not line.startswith('|'):
                line = '| ' + line
            if not line.endswith('|'):
                line = line + ' |'

            result.append(line)

            # Add separator after first row if not present
            if i == 0 and len(lines) > 1:
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if not re.match(r'^[\|\s\-:]+$', next_line):
                    # Count columns
                    cols = line.count('|') - 1
                    separator = '|' + '---|' * cols
                    result.append(separator)

        return '\n'.join(result)

    def _styled_table_to_md(self, table: StyledTable) -> str:
        """Convert StyledTable to Markdown with proper alignment."""
        result = []

        # Build header row
        if table.header_row:
            header_cells = [cell.content for cell in table.header_row.cells]
            result.append('| ' + ' | '.join(header_cells) + ' |')

            # Build separator row with alignment
            separators = []
            for i, cell in enumerate(table.header_row.cells):
                align = table.alignments[i] if table.alignments and i < len(table.alignments) else "left"
                if align == "center":
                    separators.append(':---:')
                elif align == "right":
                    separators.append('---:')
                else:
                    separators.append('---')
            result.append('| ' + ' | '.join(separators) + ' |')

        # Build data rows
        for row in table.data_rows:
            cells = [cell.content for cell in row.cells]
            result.append('| ' + ' | '.join(cells) + ' |')

        return '\n'.join(result)

    def _code_block_to_md(self, element: StyledElement) -> str:
        """Convert code block to Markdown."""
        # Get code and language from StyledCodeBlock
        if isinstance(element, StyledCodeBlock):
            code = element.code
            lang = element.language or ""
        else:
            code = element.content
            # If already has fences, return as-is
            if code.strip().startswith('```'):
                return code
            # Get language from metadata
            lang = element.original.metadata.get('language', '') if element.original.metadata else ''

        return f"```{lang}\n{code}\n```"

    def _quote_to_md(self, element: StyledElement) -> str:
        """Convert block quote to Markdown."""
        # Get quote details from StyledBlockquote
        if isinstance(element, StyledBlockquote):
            quote_text = element.quote_text
            attribution = element.attribution
        else:
            quote_text = element.content
            attribution = ""

        lines = quote_text.split('\n')
        result = []

        for line in lines:
            # Add > prefix if not present
            if not line.startswith('>'):
                line = '> ' + line
            result.append(line)

        # Add attribution if present
        if attribution:
            result.append('>')
            result.append(f'> — {attribution}')

        return '\n'.join(result)

    def _figure_to_md(self, element: StyledElement) -> str:
        """Convert figure to Markdown."""
        if isinstance(element, StyledFigure):
            figure_number = element.figure_number
            caption = element.caption
            image_url = element.image_url
            alt_text = element.alt_text
        else:
            figure_number = 0
            caption = element.content
            image_url = ""
            alt_text = ""

        result = []

        # Add image if URL present
        if image_url:
            result.append(f"![{alt_text or caption}]({image_url})")
            result.append("")

        # Add caption
        if caption or figure_number > 0:
            if figure_number > 0:
                result.append(f"*Figure {figure_number}: {caption}*")
            else:
                result.append(f"*{caption}*")

        return '\n'.join(result)

    def _horizontal_rule_to_md(self) -> str:
        """Convert horizontal rule to Markdown."""
        return "---"

    def _clean_markdown(self, content: str) -> str:
        """
        Clean up markdown content.

        - Remove excessive blank lines
        - Ensure single newline at end

        Args:
            content: Raw markdown content

        Returns:
            Cleaned markdown
        """
        # Replace 3+ newlines with 2
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ensure single newline at end
        content = content.strip() + '\n'

        return content

    def to_string(self, styled_doc: StyledDocument) -> str:
        """
        Convert StyledDocument to Markdown string without saving.

        Args:
            styled_doc: StyledDocument with formatting

        Returns:
            Markdown string
        """
        parts = []

        # Add document title if present
        if styled_doc.title:
            parts.append(f"# {styled_doc.title}")
            parts.append("")

        # Add TOC
        if self.include_toc and styled_doc.include_toc and styled_doc.toc:
            toc = self._generate_toc(styled_doc)
            parts.append(toc)
            parts.append("")
            parts.append("---")
            parts.append("")

        # Add all elements
        for element in styled_doc.elements:
            md = self._element_to_markdown(element)
            if md:
                parts.append(md)
                parts.append("")

        # Join and clean up
        content = '\n'.join(parts)
        return self._clean_markdown(content)
