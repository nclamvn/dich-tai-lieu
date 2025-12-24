#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Table of Contents Generator - Generate TOC from document structure.

Provides:
- TOC generation from headings
- Configurable depth levels
- Markdown anchor link generation
- Multi-language support (EN/VI)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .utils.constants import TOC_STYLES, ELEMENT_TYPES


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TocEntry:
    """Single entry in the Table of Contents."""
    level: int              # Heading level (1, 2, 3, 4)
    title: str              # Heading text
    anchor: str             # URL-safe anchor for links
    page_number: int = 0    # Page number (set during export)
    element_id: str = ""    # Reference to original element

    def __repr__(self):
        indent = "  " * (self.level - 1)
        return f"{indent}[L{self.level}] {self.title}"


@dataclass
class TocElement:
    """
    Table of Contents as a document element.

    Can be inserted into the document model like other elements.
    """
    type: str = "toc"
    title: str = "Table of Contents"
    entries: List[TocEntry] = field(default_factory=list)
    style: str = "default"
    language: str = "en"

    @property
    def content(self) -> str:
        """Generate plain text representation."""
        lines = [self.title, ""]
        for entry in self.entries:
            indent = "  " * (entry.level - 1)
            lines.append(f"{indent}{entry.title}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self):
        return f"<TOC: {len(self.entries)} entries>"


# =============================================================================
# TOC GENERATOR
# =============================================================================

class TocGenerator:
    """
    Generate Table of Contents from document structure.

    Usage:
        generator = TocGenerator(language="vi", style="default")
        toc = generator.generate(document_model)
        markdown = generator.to_markdown(toc)
    """

    def __init__(self, language: str = "en", style: str = "default"):
        """
        Initialize TOC generator.

        Args:
            language: Language for TOC title ("en" or "vi")
            style: TOC style preset ("default", "compact", "detailed")
        """
        self.language = language
        self.style_name = style
        self.style = TOC_STYLES.get(style, TOC_STYLES["default"])

    def generate(self, model) -> TocElement:
        """
        Generate TOC from DocumentModel.

        Args:
            model: DocumentModel with elements

        Returns:
            TocElement containing all TOC entries
        """
        # Get title based on language
        if self.language == "vi":
            title = self.style.get("title_vi", "Mục Lục")
        else:
            title = self.style.get("title", "Table of Contents")

        # Get max levels to include
        max_level = self.style.get("levels_to_show", 3)

        # Collect heading entries
        entries = self._collect_entries(model, max_level)

        return TocElement(
            title=title,
            entries=entries,
            style=self.style_name,
            language=self.language,
        )

    def _collect_entries(self, model, max_level: int) -> List[TocEntry]:
        """
        Collect TOC entries from document headings.

        Args:
            model: DocumentModel
            max_level: Maximum heading level to include

        Returns:
            List of TocEntry objects
        """
        entries = []

        for element in model.elements:
            # Only process headings
            if element.type != ELEMENT_TYPES["HEADING"]:
                continue

            level = getattr(element, 'level', 1) or 1

            # Skip if level exceeds max
            if level > max_level:
                continue

            # Clean the title (strip markdown prefixes)
            title = self._clean_heading_title(element.content)

            # Create entry
            entry = TocEntry(
                level=level,
                title=title,
                anchor=self._heading_to_anchor(title),
                element_id=getattr(element, 'element_id', ''),
            )
            entries.append(entry)

        return entries

    def _clean_heading_title(self, text: str) -> str:
        """
        Clean heading title by removing markdown prefixes.

        Args:
            text: Raw heading text

        Returns:
            Cleaned heading title
        """
        text = text.strip()

        # Remove markdown heading prefixes (# ## ### ####)
        text = re.sub(r'^#{1,6}\s+', '', text)

        return text

    def _heading_to_anchor(self, text: str) -> str:
        """
        Convert heading text to URL-safe anchor.

        GitHub-style anchor generation:
        - Lowercase
        - Replace spaces with hyphens
        - Remove special characters except hyphens
        - Preserve Vietnamese characters

        Args:
            text: Heading text

        Returns:
            URL-safe anchor string
        """
        anchor = text.lower()

        # Replace spaces with hyphens
        anchor = anchor.replace(' ', '-')

        # Remove special characters (keep letters, numbers, hyphens, Vietnamese)
        # Unicode ranges: Latin Extended, Latin Extended Additional
        anchor = re.sub(r'[^\w\-\u00C0-\u024F\u1E00-\u1EFF]', '', anchor, flags=re.UNICODE)

        # Remove multiple consecutive hyphens
        anchor = re.sub(r'-+', '-', anchor)

        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')

        return anchor

    def to_markdown(self, toc: TocElement, include_title: bool = True) -> str:
        """
        Convert TOC to Markdown format with anchor links.

        Args:
            toc: TocElement to convert
            include_title: Whether to include TOC title

        Returns:
            Markdown string with linked entries

        Example output:
            ## Table of Contents

            - [Chapter 1: Introduction](#chapter-1-introduction)
              - [1.1 Background](#11-background)
              - [1.2 Overview](#12-overview)
            - [Chapter 2: Methods](#chapter-2-methods)
        """
        lines = []

        # Add title
        if include_title:
            lines.append(f"## {toc.title}")
            lines.append("")

        # Add entries with proper indentation
        for entry in toc.entries:
            indent = "  " * (entry.level - 1)
            link = f"[{entry.title}](#{entry.anchor})"
            lines.append(f"{indent}- {link}")

        return "\n".join(lines)

    def to_plain_text(self, toc: TocElement, include_title: bool = True,
                      show_page_numbers: bool = False) -> str:
        """
        Convert TOC to plain text format.

        Args:
            toc: TocElement to convert
            include_title: Whether to include TOC title
            show_page_numbers: Whether to show page numbers

        Returns:
            Plain text TOC string
        """
        lines = []

        # Add title
        if include_title:
            lines.append(toc.title)
            lines.append("=" * len(toc.title))
            lines.append("")

        # Add entries with indentation
        for entry in toc.entries:
            indent = "  " * (entry.level - 1)
            if show_page_numbers and entry.page_number > 0:
                # Dot leaders between title and page number
                title_part = f"{indent}{entry.title}"
                page_part = str(entry.page_number)
                # Pad with dots
                total_width = 60
                available = total_width - len(title_part) - len(page_part)
                dots = "." * max(3, available)
                lines.append(f"{title_part}{dots}{page_part}")
            else:
                lines.append(f"{indent}{entry.title}")

        return "\n".join(lines)

    def update_page_numbers(self, toc: TocElement, page_map: dict) -> None:
        """
        Update page numbers in TOC entries.

        Args:
            toc: TocElement to update
            page_map: Dictionary mapping element_id to page number
        """
        for entry in toc.entries:
            if entry.element_id in page_map:
                entry.page_number = page_map[entry.element_id]

    def get_style_config(self) -> dict:
        """Get current style configuration."""
        return self.style.copy()

    def set_max_levels(self, levels: int) -> None:
        """
        Set maximum heading levels to include.

        Args:
            levels: Number of levels (1-4)
        """
        self.style["levels_to_show"] = min(max(levels, 1), 4)


def generate_toc_from_headings(headings: list, language: str = "en") -> TocElement:
    """
    Convenience function to generate TOC from a list of headings.

    Args:
        headings: List of heading elements or dicts with 'level' and 'content'
        language: Language for TOC title

    Returns:
        TocElement with entries for all headings
    """
    generator = TocGenerator(language=language)

    # Get title
    if language == "vi":
        title = "Mục Lục"
    else:
        title = "Table of Contents"

    # Build entries
    entries = []
    for h in headings:
        if hasattr(h, 'level'):
            level = h.level or 1
            content = h.content
            element_id = getattr(h, 'element_id', '')
        else:
            level = h.get('level', 1)
            content = h.get('content', h.get('title', ''))
            element_id = h.get('element_id', '')

        entry = TocEntry(
            level=level,
            title=content,
            anchor=generator._heading_to_anchor(content),
            element_id=element_id,
        )
        entries.append(entry)

    return TocElement(
        title=title,
        entries=entries,
        language=language,
    )
