#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Formatting Constants - Professional document styling standards.

Based on industry standards:
- Chicago Manual of Style
- APA 7th Edition
- Microsoft Word defaults
- Vietnamese publishing standards
"""

# =============================================================================
# HEADING STYLES
# =============================================================================

HEADING_STYLES = {
    "H1": {
        "font_size_pt": 20,
        "bold": True,
        "italic": False,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 24,
        "space_after_pt": 12,
        "page_break_before": True,  # New chapter starts on new page
        "keep_with_next": True,
        "outline_level": 1,
        "alignment": "left",  # left, center, right, justify
    },
    "H2": {
        "font_size_pt": 16,
        "bold": True,
        "italic": False,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 18,
        "space_after_pt": 6,
        "page_break_before": False,
        "keep_with_next": True,
        "outline_level": 2,
        "alignment": "left",
    },
    "H3": {
        "font_size_pt": 13,
        "bold": True,
        "italic": False,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 12,
        "space_after_pt": 6,
        "page_break_before": False,
        "keep_with_next": True,
        "outline_level": 3,
        "alignment": "left",
    },
    "H4": {
        "font_size_pt": 12,
        "bold": True,
        "italic": True,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 6,
        "space_after_pt": 3,
        "page_break_before": False,
        "keep_with_next": True,
        "outline_level": 4,
        "alignment": "left",
    },
    "BODY": {
        "font_size_pt": 12,
        "bold": False,
        "italic": False,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 0,
        "space_after_pt": 6,
        "page_break_before": False,
        "keep_with_next": False,
        "outline_level": None,
        "alignment": "justify",
    },
    "QUOTE": {
        "font_size_pt": 11,
        "bold": False,
        "italic": True,
        "underline": False,
        "all_caps": False,
        "space_before_pt": 6,
        "space_after_pt": 6,
        "left_indent_inches": 0.5,
        "right_indent_inches": 0.5,
        "alignment": "justify",
    },
    "CODE": {
        "font_size_pt": 10,
        "font_name": "Consolas",  # Override default font
        "bold": False,
        "italic": False,
        "space_before_pt": 6,
        "space_after_pt": 6,
        "background_color": "F5F5F5",  # Light gray
        "alignment": "left",
    },
}


# =============================================================================
# FONT FAMILIES
# =============================================================================

FONTS = {
    "print": {
        "heading": "Times New Roman",
        "body": "Times New Roman",
        "code": "Courier New",
    },
    "digital": {
        "heading": "Calibri",
        "body": "Calibri",
        "code": "Consolas",
    },
    "modern": {
        "heading": "Arial",
        "body": "Georgia",
        "code": "Monaco",
    },
    "vietnamese": {
        "heading": "Times New Roman",  # Best Vietnamese support
        "body": "Times New Roman",
        "code": "Consolas",
    },
}


# =============================================================================
# PAGE LAYOUT
# =============================================================================

PAGE_LAYOUT = {
    # Page sizes
    "a4": {
        "width_inches": 8.27,
        "height_inches": 11.69,
    },
    "letter": {
        "width_inches": 8.5,
        "height_inches": 11.0,
    },
    # Margin presets
    "default_margins": {
        "top_inches": 1.0,
        "bottom_inches": 1.0,
        "left_inches": 1.0,
        "right_inches": 1.0,
    },
    "normal_margins": {  # Alias for default
        "top_inches": 1.0,
        "bottom_inches": 1.0,
        "left_inches": 1.0,
        "right_inches": 1.0,
    },
    "narrow_margins": {
        "top_inches": 0.5,
        "bottom_inches": 0.5,
        "left_inches": 0.5,
        "right_inches": 0.5,
    },
    "wide_margins": {
        "top_inches": 1.25,
        "bottom_inches": 1.25,
        "left_inches": 1.5,
        "right_inches": 1.5,
    },
    "book_margins": {
        "top_inches": 0.75,
        "bottom_inches": 0.75,
        "left_inches": 0.9,   # Gutter (inside)
        "right_inches": 0.6,  # Outside
    },
    # Global settings
    "line_spacing": 1.15,
    "first_line_indent_inches": 0.0,  # Modern style: no indent
    "paragraph_spacing_pt": 6,
}


# =============================================================================
# ELEMENT TYPES
# =============================================================================

ELEMENT_TYPES = {
    "HEADING": "heading",
    "PARAGRAPH": "paragraph",
    "LIST_BULLET": "list_bullet",
    "LIST_NUMBERED": "list_numbered",
    "TABLE": "table",
    "CODE_BLOCK": "code_block",
    "CODE_INLINE": "code_inline",
    "QUOTE": "quote",
    "IMAGE": "image",
    "FOOTNOTE": "footnote",
    "PAGE_BREAK": "page_break",
    "HORIZONTAL_RULE": "horizontal_rule",
}


# =============================================================================
# LIST STYLES
# =============================================================================

LIST_STYLES = {
    "bullet": {
        "markers": ["•", "-", "*", "●", "○", "▪", "▸", "➤", "➢", "→", "►"],
        "symbols_by_level": ["•", "○", "▪", "▫"],  # Different symbol per nesting level
        "indent_inches": 0.25,
        "hanging_indent_inches": 0.25,
        "space_before_pt": 3,
        "space_after_pt": 3,
        "space_between_items_pt": 2,
    },
    "numbered": {
        "formats_by_level": ["1.", "a.", "i.", "A."],  # Different format per level
        "indent_inches": 0.25,
        "hanging_indent_inches": 0.25,
        "space_before_pt": 3,
        "space_after_pt": 3,
        "space_between_items_pt": 2,
    },
    "nested": {
        "indent_per_level_inches": 0.25,
        "max_levels": 4,
    },
}

# List marker patterns for detection
LIST_MARKERS = {
    "bullet": ["•", "-", "*", "●", "○", "▪", "▸", "➤", "➢", "→", "►", "+"],
    "numbered_arabic": r"\d+[\.\)]",      # 1. or 1)
    "numbered_alpha_lower": r"[a-z][\.\)]",  # a. or a)
    "numbered_alpha_upper": r"[A-Z][\.\)]",  # A. or A)
    "numbered_roman_lower": r"[ivxlcdm]+[\.\)]",  # i. ii. iii.
    "numbered_roman_upper": r"[IVXLCDM]+[\.\)]",  # I. II. III.
    "numbered_paren": r"\([\d\w]+\)",  # (1) or (a)
}


# =============================================================================
# TABLE STYLES
# =============================================================================

TABLE_STYLES = {
    "default": {
        "header_bold": True,
        "header_background": "D9D9D9",  # Light gray
        "header_font_color": "000000",
        "border_color": "000000",
        "border_width_pt": 0.5,
        "cell_padding_inches": 0.05,
        "cell_vertical_alignment": "center",
        "text_alignment": "left",
        "number_alignment": "right",
        "header_alignment": "center",
        "min_column_width_inches": 0.5,
        "font_size_pt": 11,
    },
    "minimal": {
        "header_bold": True,
        "header_background": None,
        "border_color": "CCCCCC",  # Light border
        "border_width_pt": 0.25,
        "cell_padding_inches": 0.08,
        "text_alignment": "left",
    },
    "striped": {
        "header_bold": True,
        "header_background": "4472C4",  # Blue
        "header_font_color": "FFFFFF",  # White
        "border_color": "000000",
        "border_width_pt": 0.5,
        "odd_row_background": "D9E2F3",  # Light blue
        "even_row_background": "FFFFFF",
        "cell_padding_inches": 0.05,
    },
}

# Table detection settings
TABLE_DETECTION = {
    "min_columns": 2,
    "min_rows": 2,
    "column_separator_min_spaces": 2,  # For plain text tables
    "markdown_cell_separator": "|",
}


# =============================================================================
# HEURISTIC THRESHOLDS
# =============================================================================

HEURISTIC_THRESHOLDS = {
    "max_heading_chars": 100,       # Lines longer than this unlikely to be headings
    "min_paragraph_chars": 50,      # Lines shorter might be headings
    "short_line_threshold": 60,     # For heuristic heading detection
    "all_caps_max_words": 10,       # All caps with more words = likely heading
    "numbered_heading_max_depth": 4,  # 1.2.3.4 max
}


# =============================================================================
# PAGE SIZES (inches)
# =============================================================================

PAGE_SIZES = {
    "A4": {"width": 8.27, "height": 11.69},
    "Letter": {"width": 8.5, "height": 11.0},
    "Legal": {"width": 8.5, "height": 14.0},
    "A5": {"width": 5.83, "height": 8.27},
    "B5": {"width": 6.93, "height": 9.84},
}


# =============================================================================
# MARGIN PRESETS (inches)
# =============================================================================

MARGIN_PRESETS = {
    "normal": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
    "narrow": {"top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5},
    "moderate": {"top": 1.0, "bottom": 1.0, "left": 0.75, "right": 0.75},
    "wide": {"top": 1.0, "bottom": 1.0, "left": 1.5, "right": 1.5},
    "book": {"top": 1.0, "bottom": 1.0, "left": 1.25, "right": 1.0},  # Extra gutter
    "academic": {"top": 1.0, "bottom": 1.0, "left": 1.5, "right": 1.0},  # APA style
}


# =============================================================================
# PAGE BREAK RULES
# =============================================================================

PAGE_BREAK_RULES = {
    "before_h1": True,          # New chapter = new page
    "before_h2": False,         # Section stays on same page
    "before_toc": True,         # TOC on its own page
    "after_toc": True,          # Content starts on new page
    "before_appendix": True,    # Appendix starts new page
    "widow_orphan_control": True,  # Prevent single lines at page top/bottom
    "keep_heading_with_content": True,  # Don't leave heading alone at page bottom
}


# =============================================================================
# HEADER/FOOTER STYLES
# =============================================================================

HEADER_FOOTER_STYLES = {
    "default": {
        "header_text": "{title}",           # Document title
        "footer_text": "Page {page}",       # Page number
        "header_font_size_pt": 10,
        "footer_font_size_pt": 10,
        "header_alignment": "center",
        "footer_alignment": "center",
        "header_font_name": "Times New Roman",
        "footer_font_name": "Times New Roman",
        "different_first_page": False,
        "different_odd_even": False,
    },
    "book": {
        "header_text_odd": "{chapter}",     # Chapter name on odd pages
        "header_text_even": "{title}",      # Book title on even pages
        "footer_text": "{page}",
        "header_font_size_pt": 10,
        "footer_font_size_pt": 10,
        "header_alignment": "center",
        "footer_alignment": "center",
        "different_first_page": True,       # No header on chapter first page
        "different_odd_even": True,
    },
    "academic": {
        "header_text": "{author} - {short_title}",
        "footer_text": "{page}",
        "header_font_size_pt": 10,
        "footer_font_size_pt": 10,
        "header_alignment": "right",
        "footer_alignment": "center",
        "different_first_page": True,
    },
    "report": {
        "header_text": "{title}",
        "footer_text": "{page} of {total}",
        "header_font_size_pt": 9,
        "footer_font_size_pt": 9,
        "header_alignment": "left",
        "footer_alignment": "right",
    },
    "minimal": {
        "header_text": "",
        "footer_text": "{page}",
        "footer_font_size_pt": 10,
        "footer_alignment": "center",
    },
}


# =============================================================================
# TABLE OF CONTENTS STYLES
# =============================================================================

TOC_STYLES = {
    "default": {
        "title": "Table of Contents",
        "title_vi": "Mục Lục",
        "title_font_size_pt": 16,
        "title_bold": True,
        "show_page_numbers": True,
        "dot_leaders": True,              # Dots between title and page number
        "indent_per_level_inches": 0.25,
        "levels_to_show": 3,              # H1, H2, H3
        "entry_font_size_pt": 12,
        "entry_line_spacing": 1.5,
        "space_before_pt": 24,
        "space_after_pt": 24,
    },
    "compact": {
        "title": "Contents",
        "title_vi": "Nội Dung",
        "title_font_size_pt": 14,
        "title_bold": True,
        "show_page_numbers": True,
        "dot_leaders": False,
        "indent_per_level_inches": 0.2,
        "levels_to_show": 2,              # H1, H2 only
        "entry_font_size_pt": 11,
        "entry_line_spacing": 1.15,
    },
    "detailed": {
        "title": "Table of Contents",
        "title_vi": "Mục Lục Chi Tiết",
        "title_font_size_pt": 18,
        "title_bold": True,
        "show_page_numbers": True,
        "dot_leaders": True,
        "indent_per_level_inches": 0.3,
        "levels_to_show": 4,              # H1, H2, H3, H4
        "entry_font_size_pt": 11,
        "entry_line_spacing": 1.5,
    },
}


# =============================================================================
# CODE BLOCK STYLES
# =============================================================================

CODE_STYLES = {
    "default": {
        "font_name": "Consolas",
        "font_name_fallback": "Courier New",
        "font_size_pt": 10,
        "background_color": "F5F5F5",     # Light gray
        "border_color": "E0E0E0",
        "border_width_pt": 0.5,
        "line_spacing": 1.0,
        "space_before_pt": 12,
        "space_after_pt": 12,
        "left_indent_inches": 0.25,
        "right_indent_inches": 0.25,
        "preserve_whitespace": True,
    },
    "minimal": {
        "font_name": "Consolas",
        "font_name_fallback": "Courier New",
        "font_size_pt": 10,
        "background_color": None,
        "border_color": None,
        "line_spacing": 1.0,
        "space_before_pt": 6,
        "space_after_pt": 6,
    },
    "dark": {
        "font_name": "Consolas",
        "font_size_pt": 10,
        "background_color": "2D2D2D",     # Dark gray
        "font_color": "E0E0E0",           # Light text
        "border_color": "1A1A1A",
        "border_width_pt": 0.5,
        "line_spacing": 1.0,
    },
}


# =============================================================================
# BLOCKQUOTE STYLES
# =============================================================================

BLOCKQUOTE_STYLES = {
    "default": {
        "font_style": "italic",
        "font_size_pt": 11,
        "left_indent_inches": 0.5,
        "right_indent_inches": 0.5,
        "left_border_width_pt": 3,
        "left_border_color": "CCCCCC",
        "space_before_pt": 12,
        "space_after_pt": 12,
        "line_spacing": 1.15,
        "attribution_font_size_pt": 10,
        "attribution_style": "normal",
    },
    "academic": {
        "font_style": "normal",
        "font_size_pt": 11,
        "left_indent_inches": 0.5,
        "right_indent_inches": 0,
        "left_border_width_pt": 0,
        "left_border_color": None,
        "space_before_pt": 12,
        "space_after_pt": 12,
        "line_spacing": 1.0,
    },
    "modern": {
        "font_style": "normal",
        "font_size_pt": 12,
        "left_indent_inches": 0.75,
        "right_indent_inches": 0.25,
        "left_border_width_pt": 4,
        "left_border_color": "4472C4",    # Blue
        "background_color": "F0F4F8",     # Light blue
        "space_before_pt": 16,
        "space_after_pt": 16,
    },
}


# =============================================================================
# FIGURE/IMAGE STYLES
# =============================================================================

FIGURE_STYLES = {
    "default": {
        "alignment": "center",
        "caption_font_size_pt": 10,
        "caption_style": "italic",
        "caption_alignment": "center",
        "number_style": "bold",           # "Figure 1:" in bold
        "number_format": "Figure {n}:",   # English
        "number_format_vi": "Hình {n}:",  # Vietnamese
        "space_before_pt": 12,
        "space_after_pt": 12,
        "space_between_image_caption_pt": 6,
        "max_width_inches": 5.5,
        "max_height_inches": 7.0,
    },
    "academic": {
        "alignment": "center",
        "caption_font_size_pt": 10,
        "caption_style": "normal",
        "caption_alignment": "left",
        "number_style": "bold",
        "number_format": "Fig. {n}.",
        "caption_position": "below",
        "space_before_pt": 12,
        "space_after_pt": 12,
    },
    "inline": {
        "alignment": "left",
        "caption_font_size_pt": 9,
        "caption_style": "italic",
        "max_width_inches": 3.0,
        "wrap_text": True,
    },
}


# =============================================================================
# FOOTNOTE STYLES
# =============================================================================

FOOTNOTE_STYLES = {
    "default": {
        "font_size_pt": 10,
        "superscript": True,
        "separator_line": True,
        "separator_width_inches": 2.0,
        "space_between_pt": 3,
        "indent_inches": 0.25,
        "number_format": "{n}",           # 1, 2, 3
    },
    "academic": {
        "font_size_pt": 10,
        "superscript": True,
        "separator_line": True,
        "separator_width_inches": 1.5,
        "space_between_pt": 6,
        "indent_inches": 0.25,
        "number_format": "[{n}]",         # [1], [2], [3]
    },
    "endnotes": {
        "font_size_pt": 11,
        "superscript": False,
        "separator_line": False,
        "number_format": "{n}.",          # 1., 2., 3.
        "section_title": "Notes",
        "section_title_vi": "Ghi Chú",
    },
}


# =============================================================================
# HORIZONTAL RULE STYLES
# =============================================================================

HORIZONTAL_RULE_STYLES = {
    "default": {
        "line_weight_pt": 0.5,
        "line_color": "AAAAAA",
        "width_percent": 100,
        "space_before_pt": 12,
        "space_after_pt": 12,
    },
    "thin": {
        "line_weight_pt": 0.25,
        "line_color": "CCCCCC",
        "width_percent": 100,
        "space_before_pt": 6,
        "space_after_pt": 6,
    },
    "thick": {
        "line_weight_pt": 1.5,
        "line_color": "666666",
        "width_percent": 80,
        "space_before_pt": 18,
        "space_after_pt": 18,
    },
    "decorative": {
        "line_weight_pt": 1.0,
        "line_color": "4472C4",
        "width_percent": 50,
        "alignment": "center",
        "space_before_pt": 24,
        "space_after_pt": 24,
    },
}


# =============================================================================
# EQUATION/MATH STYLES
# =============================================================================

EQUATION_STYLES = {
    "default": {
        "font_name": "Cambria Math",
        "font_name_fallback": "Times New Roman",
        "font_size_pt": 12,
        "alignment": "center",
        "space_before_pt": 12,
        "space_after_pt": 12,
        "number_equations": True,
        "number_format": "({n})",
        "number_alignment": "right",
    },
    "inline": {
        "font_name": "Cambria Math",
        "font_size_pt": 12,
        "preserve_baseline": True,
    },
}
