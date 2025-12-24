#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Intent Package Builder

Builds the complete LayoutIntentPackage from mapped blocks and sections.

Version: 1.0.0
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from core.contracts import (
    ManuscriptCoreOutput,
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionDefinition,
    SectionType,
    ConsistencyReport,
)

logger = logging.getLogger(__name__)


class LIPBuilder:
    """
    Builds LayoutIntentPackage from mapped content.

    Usage:
        builder = LIPBuilder()
        lip = builder.build(manuscript, blocks, sections, report)
    """

    def __init__(self, template: str = "default"):
        """
        Initialize LIP builder.

        Args:
            template: Template name to use
        """
        self.template = template

    def build(
        self,
        manuscript: ManuscriptCoreOutput,
        blocks: List[Block],
        sections: List[SectionDefinition],
        consistency_report: ConsistencyReport,
    ) -> LayoutIntentPackage:
        """
        Build complete LayoutIntentPackage.

        Args:
            manuscript: Original manuscript
            blocks: Mapped blocks from IntentMapper
            sections: Section definitions
            consistency_report: Report from ConsistencyEngine

        Returns:
            Complete LayoutIntentPackage
        """
        logger.info("Building Layout Intent Package...")

        # Extract document info
        title, subtitle, author = self._extract_document_info(manuscript, blocks)

        # Generate TOC blocks
        toc_blocks = self._generate_toc_blocks(blocks)

        # Build LIP
        lip = LayoutIntentPackage(
            title=title,
            subtitle=subtitle,
            author=author,
            template=self.template,
            blocks=blocks,
            sections=sections,
            toc_blocks=toc_blocks,
            consistency=consistency_report,
            notes=self._generate_notes(manuscript, blocks),
        )

        # Validate
        errors = lip.validate()
        if errors:
            logger.warning(f"LIP validation warnings: {errors}")

        logger.info(f"Built LIP with {len(blocks)} blocks, {len(sections)} sections")

        return lip

    def _extract_document_info(
        self,
        manuscript: ManuscriptCoreOutput,
        blocks: List[Block],
    ) -> Tuple[str, str, str]:
        """Extract title, subtitle, and author from content"""
        title = ""
        subtitle = ""
        author = ""

        # Look for title in first few blocks
        for block in blocks[:5]:
            if block.type == BlockType.TITLE:
                title = block.content
            elif block.type == BlockType.SUBTITLE:
                subtitle = block.content

        # If no explicit title, use first heading
        if not title:
            for block in blocks:
                if block.type in [BlockType.CHAPTER, BlockType.HEADING_1]:
                    title = block.content
                    break

        # Try to extract author from ADN
        adn = manuscript.adn
        if adn:
            characters = adn.get("characters", [])
            if characters:
                # First character might be author for some document types
                pass  # Author extraction is complex, skip for now

        return title, subtitle, author

    def _generate_toc_blocks(self, blocks: List[Block]) -> List[Block]:
        """Generate table of contents blocks"""
        toc_blocks: List[Block] = []

        # TOC header
        toc_header = Block(
            id="toc_header",
            type=BlockType.HEADING_1,
            content="Table of Contents",
            section=SectionType.TABLE_OF_CONTENTS,
        )
        toc_blocks.append(toc_header)

        # TOC entries
        for block in blocks:
            if block.include_in_toc:
                entry = Block(
                    id=f"toc_entry_{block.id}",
                    type=BlockType.TOC_ENTRY,
                    content=block.content,
                    section=SectionType.TABLE_OF_CONTENTS,
                    level=block.toc_level,
                    references=[block.id],
                )

                # Add chapter number if present
                if block.number:
                    entry.number = block.number

                toc_blocks.append(entry)

        return toc_blocks

    def _generate_notes(
        self,
        manuscript: ManuscriptCoreOutput,
        blocks: List[Block],
    ) -> List[str]:
        """Generate processing notes for Agent #3"""
        notes: List[str] = []

        # Document stats
        notes.append(f"Source: {manuscript.source_file}")
        notes.append(f"Language: {manuscript.source_language} → {manuscript.target_language}")
        notes.append(f"Total blocks: {len(blocks)}")

        # Quality note
        if manuscript.quality.overall_score < 0.7:
            notes.append("Warning: Low translation quality score")

        # Scanned document note
        if manuscript.is_scanned:
            notes.append("Note: Document was scanned (OCR applied)")

        # Template note
        notes.append(f"Template: {self.template}")

        return notes
