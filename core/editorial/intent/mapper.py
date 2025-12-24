#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intent Mapper

Maps manuscript segments to layout intent:
- Block type classification
- Section assignment
- Transition detection
- Spacing rules

Version: 1.0.0
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
import re

from core.contracts import (
    ManuscriptCoreOutput,
    Segment,
    SegmentType,
    Block,
    BlockType,
    SectionType,
    SectionDefinition,
    SpacingRule,
    TransitionType,
)

logger = logging.getLogger(__name__)


class IntentMapper:
    """
    Maps manuscript segments to layout blocks with intent.

    Usage:
        mapper = IntentMapper(template="book")
        blocks, sections = mapper.map(manuscript_output)
    """

    # Segment type to block type mapping
    SEGMENT_TO_BLOCK = {
        SegmentType.CHAPTER: BlockType.CHAPTER,
        SegmentType.SECTION: BlockType.SECTION,
        SegmentType.PARAGRAPH: BlockType.PARAGRAPH,
        SegmentType.HEADING: BlockType.HEADING_1,
        SegmentType.QUOTE: BlockType.QUOTE,
        SegmentType.LIST: BlockType.LIST,
        SegmentType.TABLE: BlockType.TABLE,
        SegmentType.CODE: BlockType.CODE,
        SegmentType.FORMULA: BlockType.FORMULA,
        SegmentType.FOOTNOTE: BlockType.FOOTNOTE,
        SegmentType.FRONT_MATTER: BlockType.PARAGRAPH,
        SegmentType.BACK_MATTER: BlockType.PARAGRAPH,
    }

    # Default spacing rules by block type (in points)
    DEFAULT_SPACING = {
        BlockType.TITLE: SpacingRule(before=72, after=24, line_spacing=1.0),
        BlockType.SUBTITLE: SpacingRule(before=12, after=36, line_spacing=1.0),
        BlockType.CHAPTER: SpacingRule(before=48, after=24, line_spacing=1.2),
        BlockType.SECTION: SpacingRule(before=24, after=12, line_spacing=1.2),
        BlockType.HEADING_1: SpacingRule(before=24, after=12, line_spacing=1.2),
        BlockType.HEADING_2: SpacingRule(before=18, after=9, line_spacing=1.2),
        BlockType.HEADING_3: SpacingRule(before=12, after=6, line_spacing=1.2),
        BlockType.PARAGRAPH: SpacingRule(before=0, after=12, line_spacing=1.5),
        BlockType.QUOTE: SpacingRule(before=12, after=12, line_spacing=1.4),
        BlockType.LIST: SpacingRule(before=12, after=12, line_spacing=1.3),
        BlockType.TABLE: SpacingRule(before=18, after=18, line_spacing=1.0),
        BlockType.CODE: SpacingRule(before=12, after=12, line_spacing=1.0),
        BlockType.FORMULA: SpacingRule(before=12, after=12, line_spacing=1.0),
        BlockType.FOOTNOTE: SpacingRule(before=6, after=6, line_spacing=1.2),
    }

    def __init__(
        self,
        template: str = "default",
        custom_spacing: Optional[Dict[BlockType, SpacingRule]] = None,
    ):
        """
        Initialize intent mapper.

        Args:
            template: Template name (book, report, academic, legal)
            custom_spacing: Custom spacing rules
        """
        self.template = template
        self.spacing = {**self.DEFAULT_SPACING}

        if custom_spacing:
            self.spacing.update(custom_spacing)

        # Template-specific adjustments
        self._apply_template_spacing()

    def _apply_template_spacing(self):
        """Apply template-specific spacing adjustments"""
        if self.template == "book":
            self.spacing[BlockType.CHAPTER] = SpacingRule(before=72, after=36, line_spacing=1.3)
            self.spacing[BlockType.PARAGRAPH] = SpacingRule(before=0, after=14, line_spacing=1.6)
        elif self.template == "academic":
            self.spacing[BlockType.PARAGRAPH] = SpacingRule(before=0, after=12, line_spacing=2.0)
        elif self.template == "report":
            self.spacing[BlockType.CHAPTER] = SpacingRule(before=36, after=18, line_spacing=1.2)

    def map(
        self,
        manuscript: ManuscriptCoreOutput,
    ) -> Tuple[List[Block], List[SectionDefinition]]:
        """
        Map manuscript segments to blocks with layout intent.

        Args:
            manuscript: ManuscriptCoreOutput from Agent #1

        Returns:
            Tuple of (blocks, sections)
        """
        logger.info(f"Mapping {len(manuscript.segments)} segments to blocks...")

        blocks: List[Block] = []
        sections: List[SectionDefinition] = []

        current_section = SectionType.MAIN_BODY
        section_start_id: Optional[str] = None
        last_section_type: Optional[SectionType] = None

        for idx, segment in enumerate(manuscript.segments):
            # Determine block type
            block_type = self._classify_block(segment)

            # Determine section
            section_type = self._determine_section(segment, idx, len(manuscript.segments))

            # Create block
            block = Block(
                id=f"blk_{idx:04d}",
                type=block_type,
                content=segment.translated_text,
                section=section_type,
                level=segment.level,
                spacing=self._get_spacing(block_type),
                break_before=self._determine_break_before(block_type, section_type, current_section),
                break_after=TransitionType.NONE,
                include_in_toc=self._should_include_in_toc(block_type),
                toc_level=self._get_toc_level(block_type, segment.level),
            )

            # Extract numbering if present
            block.number = self._extract_number(segment.translated_text, block_type)

            blocks.append(block)

            # Track sections
            if section_type != current_section:
                # Close previous section
                if section_start_id is not None and last_section_type is not None:
                    sections.append(SectionDefinition(
                        type=last_section_type,
                        start_block_id=section_start_id,
                        end_block_id=blocks[-2].id if len(blocks) > 1 else section_start_id,
                        start_on_odd_page=last_section_type == SectionType.CHAPTER,
                    ))

                # Start new section
                section_start_id = block.id
                last_section_type = section_type
                current_section = section_type

        # Close final section
        if section_start_id is not None and blocks:
            sections.append(SectionDefinition(
                type=current_section,
                start_block_id=section_start_id,
                end_block_id=blocks[-1].id,
            ))

        logger.info(f"Mapped to {len(blocks)} blocks in {len(sections)} sections")

        return blocks, sections

    def _classify_block(self, segment: Segment) -> BlockType:
        """Classify segment into block type"""
        # Use segment type mapping first
        if segment.type in self.SEGMENT_TO_BLOCK:
            base_type = self.SEGMENT_TO_BLOCK[segment.type]

            # Refine heading levels
            if segment.type == SegmentType.HEADING:
                if segment.level == 1:
                    return BlockType.HEADING_1
                elif segment.level == 2:
                    return BlockType.HEADING_2
                else:
                    return BlockType.HEADING_3

            return base_type

        # Fallback: analyze content
        text = segment.translated_text.strip()

        # Check for chapter
        if re.match(r'^(?:Chapter|Chương|第)\s*\d+', text, re.IGNORECASE):
            return BlockType.CHAPTER

        # Check for heading (short, no ending punctuation)
        if len(text) < 100 and not text.endswith(('.', '。', '!', '?')):
            words = text.split()
            if len(words) <= 10:
                return BlockType.HEADING_1

        return BlockType.PARAGRAPH

    def _determine_section(
        self,
        segment: Segment,
        index: int,
        total: int,
    ) -> SectionType:
        """Determine which section a segment belongs to"""
        text = segment.translated_text.lower()

        # Check for front matter keywords
        front_matter_keywords = [
            'foreword', 'lời nói đầu',
            'preface', 'lời tựa',
            'acknowledgment', 'lời cảm ơn',
            'introduction', 'giới thiệu',
            'contents', 'mục lục',
        ]

        for keyword in front_matter_keywords:
            if keyword in text:
                return SectionType.FOREWORD

        # Check for back matter keywords
        back_matter_keywords = [
            'appendix', 'phụ lục',
            'bibliography', 'tài liệu tham khảo',
            'glossary', 'thuật ngữ',
            'index', 'chỉ mục',
        ]

        for keyword in back_matter_keywords:
            if keyword in text:
                return SectionType.APPENDIX

        # Position-based heuristics
        if index < total * 0.05:  # First 5%
            return SectionType.FOREWORD
        elif index > total * 0.95:  # Last 5%
            return SectionType.APPENDIX

        # Check for chapter
        if re.match(r'^(?:Chapter|Chương|第)\s*\d+', text, re.IGNORECASE):
            return SectionType.CHAPTER

        return SectionType.MAIN_BODY

    def _determine_break_before(
        self,
        block_type: BlockType,
        section_type: SectionType,
        current_section: SectionType,
    ) -> TransitionType:
        """Determine if a break should occur before this block"""
        # Section change
        if section_type != current_section:
            return TransitionType.SECTION_BREAK

        # Chapter always starts new page
        if block_type == BlockType.CHAPTER:
            return TransitionType.CHAPTER_BREAK

        return TransitionType.NONE

    def _get_spacing(self, block_type: BlockType) -> SpacingRule:
        """Get spacing rules for block type"""
        return self.spacing.get(block_type, SpacingRule())

    def _should_include_in_toc(self, block_type: BlockType) -> bool:
        """Determine if block should be in TOC"""
        return block_type in [
            BlockType.CHAPTER,
            BlockType.SECTION,
            BlockType.HEADING_1,
            BlockType.HEADING_2,
        ]

    def _get_toc_level(self, block_type: BlockType, segment_level: int) -> int:
        """Get TOC level for block"""
        toc_levels = {
            BlockType.CHAPTER: 1,
            BlockType.SECTION: 2,
            BlockType.HEADING_1: 2,
            BlockType.HEADING_2: 3,
            BlockType.HEADING_3: 4,
        }
        return toc_levels.get(block_type, segment_level)

    def _extract_number(self, text: str, block_type: BlockType) -> Optional[str]:
        """Extract numbering from text"""
        if block_type == BlockType.CHAPTER:
            match = re.match(r'^(?:Chapter|Chương|第)\s*(\d+)', text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
