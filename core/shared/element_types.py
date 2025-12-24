#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Element Types

Provides a single source of truth for element type definitions
used by both STEM module and Formatting Engine.
"""

from enum import Enum, auto
from typing import Dict


class ElementType(Enum):
    """
    Unified element types for both STEM and Formatting modules.

    Categories:
    - Text elements: headings, paragraphs
    - List elements: bullet, numbered
    - Table elements: table, row, cell
    - Code elements: block, inline (shared with STEM)
    - Formula elements: block, inline, chemical (STEM-specific)
    - Quote/Citation elements
    - Media elements: image, figure
    - Document structure: TOC, footnote, etc.
    """

    # Text elements
    HEADING_1 = auto()
    HEADING_2 = auto()
    HEADING_3 = auto()
    HEADING_4 = auto()
    PARAGRAPH = auto()

    # List elements
    BULLET_LIST = auto()
    NUMBERED_LIST = auto()
    LIST_ITEM = auto()

    # Table elements
    TABLE = auto()
    TABLE_ROW = auto()
    TABLE_CELL = auto()

    # Code elements (shared with STEM)
    CODE_BLOCK = auto()
    CODE_INLINE = auto()

    # STEM-specific elements
    FORMULA_BLOCK = auto()       # $$...$$ or \[...\]
    FORMULA_INLINE = auto()      # $...$ or \(...\)
    CHEMICAL_FORMULA = auto()    # H2O, CO2, CH3CH2OH

    # Quote/Citation
    BLOCKQUOTE = auto()
    CITATION = auto()

    # Media
    IMAGE = auto()
    FIGURE = auto()

    # Document structure
    TOC = auto()
    FOOTNOTE = auto()
    FOOTNOTE_DEF = auto()
    HORIZONTAL_RULE = auto()
    PAGE_BREAK = auto()

    # Special
    PLACEHOLDER = auto()         # ⟪STEM_*⟫
    UNKNOWN = auto()

    @classmethod
    def get_heading_type(cls, level: int) -> 'ElementType':
        """Get heading type for a given level (1-4)."""
        mapping = {
            1: cls.HEADING_1,
            2: cls.HEADING_2,
            3: cls.HEADING_3,
            4: cls.HEADING_4,
        }
        return mapping.get(level, cls.HEADING_4)

    @classmethod
    def is_heading(cls, element_type: 'ElementType') -> bool:
        """Check if element type is a heading."""
        return element_type in [cls.HEADING_1, cls.HEADING_2, cls.HEADING_3, cls.HEADING_4]

    @classmethod
    def is_code(cls, element_type: 'ElementType') -> bool:
        """Check if element type is code-related."""
        return element_type in [cls.CODE_BLOCK, cls.CODE_INLINE]

    @classmethod
    def is_formula(cls, element_type: 'ElementType') -> bool:
        """Check if element type is formula-related."""
        return element_type in [cls.FORMULA_BLOCK, cls.FORMULA_INLINE, cls.CHEMICAL_FORMULA]

    @classmethod
    def is_list(cls, element_type: 'ElementType') -> bool:
        """Check if element type is list-related."""
        return element_type in [cls.BULLET_LIST, cls.NUMBERED_LIST, cls.LIST_ITEM]


# Mapping from old STEM BlockType to new ElementType
STEM_BLOCKTYPE_MAPPING: Dict[str, ElementType] = {
    "text": ElementType.PARAGRAPH,
    "TEXT": ElementType.PARAGRAPH,
    "title": ElementType.HEADING_1,
    "TITLE": ElementType.HEADING_1,
    "heading": ElementType.HEADING_2,
    "HEADING": ElementType.HEADING_2,
    "caption": ElementType.FIGURE,
    "CAPTION": ElementType.FIGURE,
    "list": ElementType.BULLET_LIST,
    "LIST": ElementType.BULLET_LIST,
    "table": ElementType.TABLE,
    "TABLE": ElementType.TABLE,
    "image": ElementType.IMAGE,
    "IMAGE": ElementType.IMAGE,
    "formula": ElementType.FORMULA_BLOCK,
    "FORMULA": ElementType.FORMULA_BLOCK,
    "code": ElementType.CODE_BLOCK,
    "CODE": ElementType.CODE_BLOCK,
    "footer": ElementType.PARAGRAPH,
    "FOOTER": ElementType.PARAGRAPH,
    "header": ElementType.PARAGRAPH,
    "HEADER": ElementType.PARAGRAPH,
}

# Mapping from old Formatting ELEMENT_TYPES to new ElementType
FORMATTING_TYPE_MAPPING: Dict[str, ElementType] = {
    "heading": ElementType.HEADING_1,  # Will be refined by level
    "paragraph": ElementType.PARAGRAPH,
    "list_bullet": ElementType.BULLET_LIST,
    "list_numbered": ElementType.NUMBERED_LIST,
    "table": ElementType.TABLE,
    "code_block": ElementType.CODE_BLOCK,
    "code_inline": ElementType.CODE_INLINE,
    "quote": ElementType.BLOCKQUOTE,
    "image": ElementType.IMAGE,
    "figure": ElementType.FIGURE,
    "horizontal_rule": ElementType.HORIZONTAL_RULE,
    "footnote_ref": ElementType.FOOTNOTE,
    "footnote_def": ElementType.FOOTNOTE_DEF,
}


def convert_stem_type(stem_type: str, level: int = None) -> ElementType:
    """
    Convert STEM BlockType string to ElementType.

    Args:
        stem_type: STEM BlockType string
        level: Optional heading level for refining heading types

    Returns:
        Corresponding ElementType
    """
    base_type = STEM_BLOCKTYPE_MAPPING.get(stem_type, ElementType.UNKNOWN)

    # Refine heading type if level is provided
    if base_type in [ElementType.HEADING_1, ElementType.HEADING_2] and level:
        return ElementType.get_heading_type(level)

    return base_type


def convert_formatting_type(format_type: str, level: int = None) -> ElementType:
    """
    Convert Formatting ELEMENT_TYPES string to ElementType.

    Args:
        format_type: Formatting element type string
        level: Optional heading level for refining heading types

    Returns:
        Corresponding ElementType
    """
    base_type = FORMATTING_TYPE_MAPPING.get(format_type, ElementType.UNKNOWN)

    # Refine heading type if level is provided
    if base_type == ElementType.HEADING_1 and level:
        return ElementType.get_heading_type(level)

    return base_type
