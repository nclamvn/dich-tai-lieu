#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Template - Professional layout for business documents.

Provides clean, modern typography suitable for business reports,
technical documents, and corporate communications.
"""

from .base_template import BaseTemplate, TemplateConfig


class ReportTemplate(BaseTemplate):
    """
    Template for business reports and technical documents.

    Features:
    - Calibri sans-serif font for modern look
    - Blue color scheme for headings
    - No paragraph indentation
    - Normal margins
    - 1.15 line spacing for compact readability

    Usage:
        template = ReportTemplate()
        config = template.get_config()
    """

    @property
    def name(self) -> str:
        return "report"

    @property
    def display_name(self) -> str:
        return "Business Report"

    @property
    def description(self) -> str:
        return "Professional report layout with executive summary and sections"

    def get_config(self) -> TemplateConfig:
        config = TemplateConfig(
            name="report",
            display_name="Business Report",
            description=self.description,

            heading_styles={
                "H1": {  # Main sections
                    "font_name": "Calibri",
                    "font_size_pt": 18,
                    "bold": True,
                    "italic": False,
                    "color": "1F4E79",  # Dark blue
                    "space_before_pt": 24,
                    "space_after_pt": 12,
                    "page_break_before": True,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H2": {  # Subsections
                    "font_name": "Calibri",
                    "font_size_pt": 14,
                    "bold": True,
                    "italic": False,
                    "color": "2E75B6",  # Medium blue
                    "space_before_pt": 18,
                    "space_after_pt": 6,
                    "page_break_before": False,
                    "alignment": "left",
                    "all_caps": False,
                },
                "H3": {  # Sub-subsections
                    "font_name": "Calibri",
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
                "H4": {  # Minor headings
                    "font_name": "Calibri",
                    "font_size_pt": 11,
                    "bold": True,
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
                "font_name": "Calibri",
                "font_size_pt": 11,
                "line_spacing": 1.15,
                "first_line_indent_inches": 0,
                "space_after_pt": 8,
                "alignment": "left",
                "bold": False,
                "italic": False,
            },

            page_size="A4",
            margins="normal",

            header_footer_style="default",

            toc_config={
                "title": "Table of Contents",
                "title_vi": "Mục Lục",
                "levels_to_show": 3,
                "dot_leaders": True,
                "show_page_numbers": True,
                "indent_per_level_inches": 0.25,
            },

            has_title_page=True,
            has_abstract=True,  # Executive Summary
            has_appendix=True,

            language="en",

            metadata={
                "suitable_for": ["business reports", "technical docs", "proposals", "white papers"],
                "color_scheme": "blue",
            },
        )

        return self._apply_overrides(config)
