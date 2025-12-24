#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Academic Template - Scholarly layout for academic papers.

Provides traditional academic typography suitable for research papers,
theses, dissertations, and journal articles.
"""

from .base_template import BaseTemplate, TemplateConfig


class AcademicTemplate(BaseTemplate):
    """
    Template for academic papers and theses.

    Features:
    - Times New Roman serif font (academic standard)
    - Double line spacing (thesis requirement)
    - First-line paragraph indentation
    - Chapter page breaks
    - Support for abstract and references

    Usage:
        template = AcademicTemplate()
        config = template.get_config()
    """

    @property
    def name(self) -> str:
        return "academic"

    @property
    def display_name(self) -> str:
        return "Academic Paper"

    @property
    def description(self) -> str:
        return "Academic paper layout with abstract, chapters, and references"

    def get_config(self) -> TemplateConfig:
        config = TemplateConfig(
            name="academic",
            display_name="Academic Paper",
            description=self.description,

            heading_styles={
                "H1": {  # Chapter
                    "font_name": "Times New Roman",
                    "font_size_pt": 16,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 36,
                    "space_after_pt": 18,
                    "page_break_before": True,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H2": {  # Section (1.1, 1.2)
                    "font_name": "Times New Roman",
                    "font_size_pt": 14,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 24,
                    "space_after_pt": 12,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H3": {  # Subsection (1.1.1)
                    "font_name": "Times New Roman",
                    "font_size_pt": 12,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 12,
                    "space_after_pt": 6,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H4": {  # Sub-subsection
                    "font_name": "Times New Roman",
                    "font_size_pt": 12,
                    "bold": False,
                    "italic": True,
                    "color": None,
                    "space_before_pt": 6,
                    "space_after_pt": 6,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
            },

            body_style={
                "font_name": "Times New Roman",
                "font_size_pt": 12,
                "line_spacing": 2.0,  # Double-spaced (academic standard)
                "first_line_indent_inches": 0.5,
                "space_after_pt": 0,
                "alignment": "justify",
                "bold": False,
                "italic": False,
            },

            page_size="A4",
            margins="normal",

            header_footer_style="academic",

            toc_config={
                "title": "Table of Contents",
                "title_vi": "Mục Lục",
                "levels_to_show": 3,
                "dot_leaders": True,
                "show_page_numbers": True,
                "indent_per_level_inches": 0.3,
            },

            has_title_page=True,
            has_abstract=True,
            has_appendix=True,

            language="en",

            metadata={
                "suitable_for": ["research papers", "theses", "dissertations", "journal articles"],
                "citation_style": "APA",  # Default, can be overridden
            },
        )

        return self._apply_overrides(config)
