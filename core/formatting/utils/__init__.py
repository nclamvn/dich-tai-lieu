#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Formatting utilities - constants and patterns.
"""

from .constants import (
    HEADING_STYLES,
    FONTS,
    PAGE_LAYOUT,
    ELEMENT_TYPES,
    LIST_STYLES,
    LIST_MARKERS,
    TABLE_STYLES,
    TABLE_DETECTION,
    HEURISTIC_THRESHOLDS,
)
from .heading_patterns import (
    H1_PATTERNS_EN,
    H1_PATTERNS_VI,
    H2_PATTERNS_EN,
    H2_PATTERNS_VI,
    H3_PATTERNS_EN,
    H3_PATTERNS_VI,
    H4_PATTERNS,
    match_heading_pattern,
    get_heading_level,
)
from .list_patterns import (
    is_bullet_item,
    is_numbered_item,
    is_list_item,
    is_list_continuation,
    calculate_indent_level,
    detect_list_type,
)
from .table_patterns import (
    is_markdown_table_row,
    is_markdown_separator,
    parse_markdown_row,
    parse_markdown_alignment,
    detect_markdown_table,
    detect_ascii_table,
    DetectedTable,
)
from .stem_integration import (
    STEMIntegration,
    get_stem_integration,
    reset_stem_integration,
)

__all__ = [
    # Constants
    "HEADING_STYLES",
    "FONTS",
    "PAGE_LAYOUT",
    "ELEMENT_TYPES",
    "LIST_STYLES",
    "LIST_MARKERS",
    "TABLE_STYLES",
    "TABLE_DETECTION",
    "HEURISTIC_THRESHOLDS",
    # Heading patterns
    "H1_PATTERNS_EN",
    "H1_PATTERNS_VI",
    "H2_PATTERNS_EN",
    "H2_PATTERNS_VI",
    "H3_PATTERNS_EN",
    "H3_PATTERNS_VI",
    "H4_PATTERNS",
    "match_heading_pattern",
    "get_heading_level",
    # List patterns
    "is_bullet_item",
    "is_numbered_item",
    "is_list_item",
    "is_list_continuation",
    "calculate_indent_level",
    "detect_list_type",
    # Table patterns
    "is_markdown_table_row",
    "is_markdown_separator",
    "parse_markdown_row",
    "parse_markdown_alignment",
    "detect_markdown_table",
    "detect_ascii_table",
    "DetectedTable",
    # STEM integration
    "STEMIntegration",
    "get_stem_integration",
    "reset_stem_integration",
]
