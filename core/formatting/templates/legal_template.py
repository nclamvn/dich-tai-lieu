#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legal Template - Formal layout for legal documents.

Provides traditional typography suitable for contracts, agreements,
legal briefs, and regulatory documents.
"""

from .base_template import BaseTemplate, TemplateConfig


class LegalTemplate(BaseTemplate):
    """
    Template for legal documents and contracts.

    Features:
    - Times New Roman serif font for formality
    - Centered, all-caps article headings
    - Wide margins for annotations
    - 1.5 line spacing (legal standard)
    - First-line paragraph indentation

    Usage:
        template = LegalTemplate()
        config = template.get_config()
    """

    @property
    def name(self) -> str:
        return "legal"

    @property
    def display_name(self) -> str:
        return "Legal Document"

    @property
    def description(self) -> str:
        return "Formal legal document layout with articles and numbered clauses"

    def get_config(self) -> TemplateConfig:
        config = TemplateConfig(
            name="legal",
            display_name="Legal Document",
            description=self.description,

            heading_styles={
                "H1": {  # Article / Điều
                    "font_name": "Times New Roman",
                    "font_size_pt": 14,
                    "bold": True,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 24,
                    "space_after_pt": 12,
                    "page_break_before": False,
                    "alignment": "center",
                    "all_caps": True,
                },
                "H2": {  # Section / Khoản
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
                "H3": {  # Clause / Điểm
                    "font_name": "Times New Roman",
                    "font_size_pt": 12,
                    "bold": False,
                    "italic": False,
                    "color": None,
                    "space_before_pt": 6,
                    "space_after_pt": 3,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H4": {  # Sub-clause
                    "font_name": "Times New Roman",
                    "font_size_pt": 12,
                    "bold": False,
                    "italic": True,
                    "color": None,
                    "space_before_pt": 6,
                    "space_after_pt": 3,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
            },

            body_style={
                "font_name": "Times New Roman",
                "font_size_pt": 12,
                "line_spacing": 1.5,  # Legal standard
                "first_line_indent_inches": 0.5,
                "space_after_pt": 0,
                "alignment": "justify",
                "bold": False,
                "italic": False,
            },

            page_size="A4",
            margins="wide",  # Wider margins for annotations

            header_footer_style="default",

            toc_config={
                "title": "Table of Contents",
                "title_vi": "Mục Lục",
                "levels_to_show": 2,
                "dot_leaders": True,
                "show_page_numbers": True,
                "indent_per_level_inches": 0.25,
            },

            has_title_page=True,
            has_abstract=False,
            has_appendix=True,

            language="en",

            metadata={
                "suitable_for": ["contracts", "agreements", "legal briefs", "regulations"],
                "numbering_style": "legal",
            },
        )

        return self._apply_overrides(config)
