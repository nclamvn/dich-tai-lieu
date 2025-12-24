#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Template - Professional layout for books and novels.

Provides elegant typography suitable for fiction and non-fiction books,
with centered chapter titles, proper spacing, and book-style margins.
"""

from .base_template import BaseTemplate, TemplateConfig


class BookTemplate(BaseTemplate):
    """
    Template for books, novels, and non-fiction.

    Features:
    - Centered chapter titles with page breaks
    - Georgia serif font for elegant reading
    - First-line paragraph indentation
    - Book margins (extra gutter for binding)
    - 1.5 line spacing for comfortable reading

    Usage:
        template = BookTemplate()
        config = template.get_config()
    """

    @property
    def name(self) -> str:
        return "book"

    @property
    def display_name(self) -> str:
        return "Book / Novel"

    @property
    def description(self) -> str:
        return "Professional book layout with chapters, parts, and elegant typography"

    def get_config(self) -> TemplateConfig:
        config = TemplateConfig(
            name="book",
            display_name="Book / Novel",
            description=self.description,

            heading_styles={
                "H1": {  # Chapter
                    "font_name": "Georgia",
                    "font_size_pt": 24,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 72,  # Extra space for chapter start
                    "space_after_pt": 24,
                    "page_break_before": True,
                    "alignment": "center",  # Centered chapter titles
                    "all_caps": False,
                },
                "H2": {  # Section
                    "font_name": "Georgia",
                    "font_size_pt": 16,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 24,
                    "space_after_pt": 12,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H3": {  # Subsection
                    "font_name": "Georgia",
                    "font_size_pt": 13,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 18,
                    "space_after_pt": 6,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H4": {  # Sub-subsection
                    "font_name": "Georgia",
                    "font_size_pt": 12,
                    "bold": False,
                    "italic": True,
                    "color": None,
                    "space_before_pt": 12,
                    "space_after_pt": 6,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
            },

            body_style={
                "font_name": "Georgia",
                "font_size_pt": 11,
                "line_spacing": 1.5,  # More readable for books
                "first_line_indent_inches": 0.3,  # Indent first line
                "space_after_pt": 0,  # No extra space between paragraphs
                "alignment": "justify",
                "bold": False,
                "italic": False,
            },

            page_size="A4",
            margins="book",  # Extra gutter for binding

            header_footer_style="book",

            toc_config={
                "title": "Contents",
                "title_vi": "Mục Lục",
                "levels_to_show": 2,  # Only chapters and sections
                "dot_leaders": True,
                "show_page_numbers": True,
                "indent_per_level_inches": 0.25,
            },

            has_title_page=True,
            has_abstract=False,
            has_appendix=True,

            language="en",

            metadata={
                "suitable_for": ["novels", "non-fiction", "textbooks", "manuals"],
                "binding_ready": True,
            },
        )

        return self._apply_overrides(config)
