#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Section Manager

Manages document sections:
- Cover
- Front matter (TOC, preface, etc.)
- Main body (chapters)
- Back matter (appendix, index, etc.)

Version: 1.0.0
"""

from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import logging

from core.contracts import (
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionDefinition,
    SectionType,
)

if TYPE_CHECKING:
    from ..executor.block_flow import FlowedBlock

logger = logging.getLogger(__name__)


class NumberingStyle(Enum):
    """Page numbering styles"""
    ARABIC = "arabic"      # 1, 2, 3...
    ROMAN_LOWER = "roman"  # i, ii, iii...
    ROMAN_UPPER = "ROMAN"  # I, II, III...
    ALPHA_LOWER = "alpha"  # a, b, c...
    ALPHA_UPPER = "ALPHA"  # A, B, C...
    NONE = "none"          # No numbering


@dataclass
class SectionConfig:
    """Configuration for a section"""
    type: SectionType
    numbering_style: NumberingStyle = NumberingStyle.ARABIC
    numbering_start: int = 1
    header_text: str = ""
    footer_text: str = ""
    show_header: bool = True
    show_footer: bool = True
    different_first_page: bool = False
    start_on_odd_page: bool = False


@dataclass
class PageInfo:
    """Information about a specific page"""
    page_number: int
    section: SectionType
    display_number: str  # Formatted page number
    header: str
    footer: str
    is_first_in_section: bool = False
    is_blank: bool = False


class SectionManager:
    """
    Manages document sections and their properties.

    Usage:
        manager = SectionManager()
        manager.configure_sections(lip)
        page_info = manager.get_page_info(page_number)
    """

    # Default section configurations
    DEFAULT_CONFIGS = {
        SectionType.COVER: SectionConfig(
            type=SectionType.COVER,
            numbering_style=NumberingStyle.NONE,
            show_header=False,
            show_footer=False,
        ),
        SectionType.TITLE_PAGE: SectionConfig(
            type=SectionType.TITLE_PAGE,
            numbering_style=NumberingStyle.NONE,
            show_header=False,
            show_footer=False,
        ),
        SectionType.COPYRIGHT: SectionConfig(
            type=SectionType.COPYRIGHT,
            numbering_style=NumberingStyle.NONE,
            show_header=False,
            show_footer=False,
        ),
        SectionType.TABLE_OF_CONTENTS: SectionConfig(
            type=SectionType.TABLE_OF_CONTENTS,
            numbering_style=NumberingStyle.ROMAN_LOWER,
            numbering_start=1,
        ),
        SectionType.FOREWORD: SectionConfig(
            type=SectionType.FOREWORD,
            numbering_style=NumberingStyle.ROMAN_LOWER,
        ),
        SectionType.PREFACE: SectionConfig(
            type=SectionType.PREFACE,
            numbering_style=NumberingStyle.ROMAN_LOWER,
        ),
        SectionType.MAIN_BODY: SectionConfig(
            type=SectionType.MAIN_BODY,
            numbering_style=NumberingStyle.ARABIC,
            numbering_start=1,
        ),
        SectionType.CHAPTER: SectionConfig(
            type=SectionType.CHAPTER,
            numbering_style=NumberingStyle.ARABIC,
            start_on_odd_page=True,
            different_first_page=True,
        ),
        SectionType.APPENDIX: SectionConfig(
            type=SectionType.APPENDIX,
            numbering_style=NumberingStyle.ARABIC,
        ),
        SectionType.BIBLIOGRAPHY: SectionConfig(
            type=SectionType.BIBLIOGRAPHY,
            numbering_style=NumberingStyle.ARABIC,
        ),
        SectionType.INDEX: SectionConfig(
            type=SectionType.INDEX,
            numbering_style=NumberingStyle.ARABIC,
        ),
    }

    def __init__(self):
        """Initialize section manager"""
        self.configs: Dict[SectionType, SectionConfig] = {}
        self.section_pages: Dict[SectionType, Tuple[int, int]] = {}  # section -> (start, end)
        self.page_sections: Dict[int, SectionType] = {}  # page -> section

    def configure_sections(self, lip: LayoutIntentPackage):
        """
        Configure sections from LayoutIntentPackage.

        Args:
            lip: LayoutIntentPackage from Agent #2
        """
        logger.info(f"Configuring {len(lip.sections)} sections...")

        # Start with defaults
        self.configs = {k: SectionConfig(
            type=v.type,
            numbering_style=v.numbering_style,
            numbering_start=v.numbering_start,
            header_text=v.header_text,
            footer_text=v.footer_text,
            show_header=v.show_header,
            show_footer=v.show_footer,
            different_first_page=v.different_first_page,
            start_on_odd_page=v.start_on_odd_page,
        ) for k, v in self.DEFAULT_CONFIGS.items()}

        # Apply LIP section definitions
        for section_def in lip.sections:
            if section_def.type in self.configs:
                config = self.configs[section_def.type]

                # Override with LIP values
                if section_def.numbering_style:
                    try:
                        config.numbering_style = NumberingStyle(section_def.numbering_style)
                    except ValueError:
                        pass
                if section_def.numbering_start:
                    config.numbering_start = section_def.numbering_start
                if section_def.header_text:
                    config.header_text = section_def.header_text
                if section_def.footer_text:
                    config.footer_text = section_def.footer_text
                config.start_on_odd_page = section_def.start_on_odd_page
                config.different_first_page = section_def.different_first_page

        logger.info(f"Configured {len(self.configs)} section types")

    def assign_pages(
        self,
        flowed_blocks: List,  # List[FlowedBlock]
    ):
        """
        Assign pages to sections based on flowed blocks.

        Args:
            flowed_blocks: Flowed blocks from BlockFlowExecutor
        """
        if not flowed_blocks:
            return

        current_section: Optional[SectionType] = None
        section_start = 1

        for fb in flowed_blocks:
            page = fb.page_number
            section = fb.block.section

            self.page_sections[page] = section

            if section != current_section:
                if current_section is not None:
                    self.section_pages[current_section] = (section_start, page - 1)
                current_section = section
                section_start = page

        # Close last section
        if current_section is not None:
            last_page = max(fb.page_number for fb in flowed_blocks)
            self.section_pages[current_section] = (section_start, last_page)

    def get_page_info(self, page_number: int) -> PageInfo:
        """
        Get information for a specific page.

        Args:
            page_number: Page number

        Returns:
            PageInfo with numbering and header/footer
        """
        section = self.page_sections.get(page_number, SectionType.MAIN_BODY)
        config = self.configs.get(section, self.DEFAULT_CONFIGS[SectionType.MAIN_BODY])

        # Calculate display number
        display_number = self._format_page_number(page_number, section, config)

        # Determine if first in section
        section_range = self.section_pages.get(section, (page_number, page_number))
        is_first = page_number == section_range[0]

        # Build header/footer
        header = self._build_header(page_number, section, config, is_first)
        footer = self._build_footer(page_number, section, config, display_number, is_first)

        return PageInfo(
            page_number=page_number,
            section=section,
            display_number=display_number,
            header=header,
            footer=footer,
            is_first_in_section=is_first,
        )

    def _format_page_number(
        self,
        page_number: int,
        section: SectionType,
        config: SectionConfig,
    ) -> str:
        """Format page number according to section style"""
        if config.numbering_style == NumberingStyle.NONE:
            return ""

        # Calculate relative page number within section
        section_range = self.section_pages.get(section)
        if section_range:
            relative_page = page_number - section_range[0] + config.numbering_start
        else:
            relative_page = page_number

        if config.numbering_style == NumberingStyle.ARABIC:
            return str(relative_page)
        elif config.numbering_style == NumberingStyle.ROMAN_LOWER:
            return self._to_roman(relative_page).lower()
        elif config.numbering_style == NumberingStyle.ROMAN_UPPER:
            return self._to_roman(relative_page)
        elif config.numbering_style == NumberingStyle.ALPHA_LOWER:
            return chr(ord('a') + relative_page - 1) if relative_page <= 26 else str(relative_page)
        elif config.numbering_style == NumberingStyle.ALPHA_UPPER:
            return chr(ord('A') + relative_page - 1) if relative_page <= 26 else str(relative_page)

        return str(relative_page)

    def _to_roman(self, num: int) -> str:
        """Convert number to Roman numerals"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4, 1
        ]
        syms = [
            'M', 'CM', 'D', 'CD',
            'C', 'XC', 'L', 'XL',
            'X', 'IX', 'V', 'IV', 'I'
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1
        return roman_num

    def _build_header(
        self,
        page_number: int,
        section: SectionType,
        config: SectionConfig,
        is_first: bool,
    ) -> str:
        """Build header text for page"""
        if not config.show_header:
            return ""
        if is_first and config.different_first_page:
            return ""

        return config.header_text

    def _build_footer(
        self,
        page_number: int,
        section: SectionType,
        config: SectionConfig,
        display_number: str,
        is_first: bool,
    ) -> str:
        """Build footer text for page"""
        if not config.show_footer:
            return ""
        if is_first and config.different_first_page:
            return ""

        if config.footer_text:
            return config.footer_text.replace("{page}", display_number)

        return display_number
