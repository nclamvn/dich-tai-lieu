#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Model - Abstract Syntax Tree for document structure.

Stage 2 of the Formatting Engine:
- Build document AST from detected elements
- Validate document structure
- Generate Table of Contents
- Provide document outline
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from .detector import DocumentElement, StructureDetector
from .utils.constants import ELEMENT_TYPES


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TocEntry:
    """Table of Contents entry."""
    level: int
    title: str
    element_id: str
    page_number: Optional[int] = None  # Set during export


@dataclass
class ValidationError:
    """Document validation error."""
    severity: str  # "error", "warning", "info"
    message: str
    element_id: Optional[str] = None
    suggestion: Optional[str] = None

    def __repr__(self):
        return f"[{self.severity.upper()}] {self.message}"


class DocumentStats:
    """Document statistics."""
    def __init__(self):
        self.total_elements = 0
        self.heading_count = {1: 0, 2: 0, 3: 0, 4: 0}
        self.paragraph_count = 0
        self.list_count = 0
        self.table_count = 0
        self.code_block_count = 0
        self.quote_count = 0
        self.word_count = 0
        self.char_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_elements": self.total_elements,
            "headings": self.heading_count,
            "paragraphs": self.paragraph_count,
            "lists": self.list_count,
            "tables": self.table_count,
            "code_blocks": self.code_block_count,
            "quotes": self.quote_count,
            "word_count": self.word_count,
            "char_count": self.char_count,
        }


# =============================================================================
# DOCUMENT MODEL
# =============================================================================

class DocumentModel:
    """
    Abstract Syntax Tree for document structure.

    Provides:
    - Element storage and retrieval
    - Table of Contents generation
    - Structure validation
    - Document statistics
    """

    def __init__(self):
        """Initialize empty document model."""
        self.elements: List[DocumentElement] = []
        self.toc: List[TocEntry] = []
        self.metadata: Dict[str, Any] = {}
        self._stats: Optional[DocumentStats] = None

    @classmethod
    def from_text(cls, text: str, language: str = "auto") -> "DocumentModel":
        """
        Create DocumentModel from raw text.

        Args:
            text: Raw document text
            language: Language hint ("en", "vi", or "auto")

        Returns:
            Populated DocumentModel
        """
        model = cls()
        detector = StructureDetector(language=language)
        elements = detector.detect(text)

        for elem in elements:
            model.add_element(elem)

        model.metadata["language"] = detector.get_detected_language()
        model.build_toc()

        return model

    def add_element(self, element: DocumentElement) -> None:
        """
        Add element to document model.

        Args:
            element: DocumentElement to add
        """
        self.elements.append(element)
        self._stats = None  # Invalidate stats cache

        # Update TOC if heading
        if element.type == ELEMENT_TYPES["HEADING"]:
            self.toc.append(TocEntry(
                level=element.level,
                title=element.content,
                element_id=element.element_id,
            ))

    def build_toc(self) -> List[TocEntry]:
        """
        Build/rebuild Table of Contents from headings.

        Returns:
            List of TocEntry objects
        """
        self.toc = []

        for elem in self.elements:
            if elem.type == ELEMENT_TYPES["HEADING"]:
                self.toc.append(TocEntry(
                    level=elem.level,
                    title=elem.content,
                    element_id=elem.element_id,
                ))

        return self.toc

    def validate(self) -> List[ValidationError]:
        """
        Validate document structure.

        Checks:
        - Has at least one heading
        - No skipped heading levels
        - H1 appears before H2/H3/H4
        - Balanced structure

        Returns:
            List of ValidationError objects
        """
        errors = []
        headings = [e for e in self.elements if e.type == ELEMENT_TYPES["HEADING"]]

        # Check: Has at least one heading
        if not headings:
            errors.append(ValidationError(
                severity="warning",
                message="Document has no headings",
                suggestion="Consider adding a title (H1) to your document",
            ))
            return errors

        # Check: First heading should be H1 or H2
        first_heading = headings[0]
        if first_heading.level > 2:
            errors.append(ValidationError(
                severity="warning",
                message=f"First heading is H{first_heading.level}, expected H1 or H2",
                element_id=first_heading.element_id,
                suggestion="Start document with a top-level heading",
            ))

        # Check: No skipped levels
        last_level = 0
        for h in headings:
            if h.level > last_level + 1 and last_level > 0:
                errors.append(ValidationError(
                    severity="warning",
                    message=f"Skipped heading level: H{last_level} → H{h.level}",
                    element_id=h.element_id,
                    suggestion=f"Consider using H{last_level + 1} instead",
                ))
            last_level = h.level

        # Check: Multiple H1s (usually only one title per document)
        h1_count = sum(1 for h in headings if h.level == 1)
        if h1_count > 1:
            errors.append(ValidationError(
                severity="info",
                message=f"Document has {h1_count} H1 headings (usually 1 is expected)",
                suggestion="If this is a multi-part document, this is fine",
            ))

        # Check: Very deep nesting
        max_level = max(h.level for h in headings)
        if max_level > 4:
            errors.append(ValidationError(
                severity="info",
                message=f"Deep heading nesting detected (H{max_level})",
                suggestion="Consider simplifying document structure",
            ))

        return errors

    def get_outline(self, max_level: int = 4) -> str:
        """
        Generate text outline of document structure.

        Args:
            max_level: Maximum heading level to include

        Returns:
            Indented outline string
        """
        lines = []

        for entry in self.toc:
            if entry.level <= max_level:
                indent = "  " * (entry.level - 1)
                prefix = "├─" if entry.level > 1 else "■"
                lines.append(f"{indent}{prefix} H{entry.level}: {entry.title}")

        return '\n'.join(lines)

    def get_statistics(self) -> DocumentStats:
        """
        Calculate document statistics.

        Returns:
            DocumentStats object
        """
        if self._stats:
            return self._stats

        stats = DocumentStats()
        stats.total_elements = len(self.elements)

        for elem in self.elements:
            if elem.type == ELEMENT_TYPES["HEADING"]:
                if elem.level in stats.heading_count:
                    stats.heading_count[elem.level] += 1
            elif elem.type == ELEMENT_TYPES["PARAGRAPH"]:
                stats.paragraph_count += 1
            elif elem.type in [ELEMENT_TYPES["LIST_BULLET"], ELEMENT_TYPES["LIST_NUMBERED"]]:
                stats.list_count += 1
            elif elem.type == ELEMENT_TYPES["TABLE"]:
                stats.table_count += 1
            elif elem.type == ELEMENT_TYPES["CODE_BLOCK"]:
                stats.code_block_count += 1
            elif elem.type == ELEMENT_TYPES["QUOTE"]:
                stats.quote_count += 1

            # Word and char count
            stats.word_count += len(elem.content.split())
            stats.char_count += len(elem.content)

        self._stats = stats
        return stats

    def get_element_by_id(self, element_id: str) -> Optional[DocumentElement]:
        """
        Find element by ID.

        Args:
            element_id: Element ID to find

        Returns:
            DocumentElement or None
        """
        for elem in self.elements:
            if elem.element_id == element_id:
                return elem
        return None

    def get_headings(self, level: Optional[int] = None) -> List[DocumentElement]:
        """
        Get all headings, optionally filtered by level.

        Args:
            level: Optional heading level filter (1-4)

        Returns:
            List of heading elements
        """
        headings = [e for e in self.elements if e.type == ELEMENT_TYPES["HEADING"]]

        if level is not None:
            headings = [h for h in headings if h.level == level]

        return headings

    def get_elements_by_type(self, element_type: str) -> List[DocumentElement]:
        """
        Get all elements of a specific type.

        Args:
            element_type: Element type from ELEMENT_TYPES

        Returns:
            List of matching elements
        """
        return [e for e in self.elements if e.type == element_type]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "elements": [
                {
                    "type": e.type,
                    "content": e.content,
                    "level": e.level,
                    "element_id": e.element_id,
                    "metadata": e.metadata,
                    "confidence": e.confidence,
                }
                for e in self.elements
            ],
            "toc": [
                {
                    "level": t.level,
                    "title": t.title,
                    "element_id": t.element_id,
                }
                for t in self.toc
            ],
            "metadata": self.metadata,
            "statistics": self.get_statistics().to_dict(),
        }

    def __repr__(self):
        stats = self.get_statistics()
        return (f"<DocumentModel: {stats.total_elements} elements, "
                f"{sum(stats.heading_count.values())} headings, "
                f"{stats.paragraph_count} paragraphs>")

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)
