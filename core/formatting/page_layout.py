#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Page Layout Manager - Handle page size, margins, headers, footers.

Manages:
- Page sizes (A4, Letter, Legal, etc.)
- Margins (normal, narrow, wide, book, etc.)
- Headers and footers with variable substitution
- Page break rules
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .utils.constants import (
    PAGE_SIZES,
    MARGIN_PRESETS,
    PAGE_BREAK_RULES,
    HEADER_FOOTER_STYLES,
    ELEMENT_TYPES,
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PageDimensions:
    """Page dimensions in inches."""
    width: float
    height: float

    def to_dict(self) -> Dict[str, float]:
        return {"width": self.width, "height": self.height}


@dataclass
class Margins:
    """Page margins in inches."""
    top: float
    bottom: float
    left: float
    right: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
        }


@dataclass
class ContentArea:
    """Usable content area after margins."""
    width: float
    height: float

    def to_dict(self) -> Dict[str, float]:
        return {"width": self.width, "height": self.height}


@dataclass
class HeaderFooterConfig:
    """Header and footer configuration."""
    header_text: str = ""
    footer_text: str = "Page {page}"
    header_font_size_pt: float = 10.0
    footer_font_size_pt: float = 10.0
    header_alignment: str = "center"
    footer_alignment: str = "center"
    header_font_name: str = "Times New Roman"
    footer_font_name: str = "Times New Roman"
    different_first_page: bool = False
    different_odd_even: bool = False
    # For book style
    header_text_odd: Optional[str] = None
    header_text_even: Optional[str] = None


# =============================================================================
# PAGE LAYOUT MANAGER
# =============================================================================

class PageLayoutManager:
    """
    Manage page layout including size, margins, headers, and footers.

    Usage:
        layout = PageLayoutManager(
            page_size="A4",
            margins="book",
            header_footer_style="default"
        )

        # Get content area
        area = layout.calculate_content_area()

        # Get header text for a page
        header = layout.get_header_text(page_num=5, doc_title="My Book")
    """

    def __init__(
        self,
        page_size: str = "A4",
        margins: str = "normal",
        header_footer_style: str = "default",
    ):
        """
        Initialize page layout manager.

        Args:
            page_size: Page size name ("A4", "Letter", "Legal")
            margins: Margin preset name ("normal", "narrow", "wide", "book")
            header_footer_style: Header/footer style ("default", "book", "academic")
        """
        # Page size
        size_config = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
        self.page_size = PageDimensions(
            width=size_config["width"],
            height=size_config["height"]
        )
        self.page_size_name = page_size

        # Margins
        margin_config = MARGIN_PRESETS.get(margins, MARGIN_PRESETS["normal"])
        self.margins = Margins(
            top=margin_config["top"],
            bottom=margin_config["bottom"],
            left=margin_config["left"],
            right=margin_config["right"]
        )
        self.margin_preset_name = margins

        # Header/footer
        hf_config = HEADER_FOOTER_STYLES.get(header_footer_style, HEADER_FOOTER_STYLES["default"])
        self.header_footer = HeaderFooterConfig(
            header_text=hf_config.get("header_text", ""),
            footer_text=hf_config.get("footer_text", "Page {page}"),
            header_font_size_pt=hf_config.get("header_font_size_pt", 10),
            footer_font_size_pt=hf_config.get("footer_font_size_pt", 10),
            header_alignment=hf_config.get("header_alignment", "center"),
            footer_alignment=hf_config.get("footer_alignment", "center"),
            header_font_name=hf_config.get("header_font_name", "Times New Roman"),
            footer_font_name=hf_config.get("footer_font_name", "Times New Roman"),
            different_first_page=hf_config.get("different_first_page", False),
            different_odd_even=hf_config.get("different_odd_even", False),
            header_text_odd=hf_config.get("header_text_odd"),
            header_text_even=hf_config.get("header_text_even"),
        )
        self.header_footer_style_name = header_footer_style

        # Page break rules
        self.page_break_rules = PAGE_BREAK_RULES.copy()

    def calculate_content_area(self) -> ContentArea:
        """
        Calculate usable content area after margins.

        Returns:
            ContentArea with width and height in inches
        """
        width = self.page_size.width - self.margins.left - self.margins.right
        height = self.page_size.height - self.margins.top - self.margins.bottom
        return ContentArea(width=width, height=height)

    def should_page_break_before(self, element_type: str, level: int = 0,
                                  is_first_content: bool = False) -> bool:
        """
        Determine if page break is needed before an element.

        Args:
            element_type: Element type from ELEMENT_TYPES
            level: Heading level (1-4) if heading
            is_first_content: Whether this is the first content element

        Returns:
            True if page break should be inserted before this element
        """
        # Never break before first content
        if is_first_content:
            return False

        # Check heading levels
        if element_type == ELEMENT_TYPES["HEADING"]:
            if level == 1 and self.page_break_rules.get("before_h1", True):
                return True
            if level == 2 and self.page_break_rules.get("before_h2", False):
                return True

        return False

    def get_header_text(
        self,
        page_num: int,
        doc_title: str = "",
        chapter_title: str = "",
        author: str = "",
        short_title: str = "",
    ) -> str:
        """
        Get header text for a specific page.

        Handles:
        - Variable substitution ({title}, {chapter}, {author}, etc.)
        - Different first page (returns empty if first page)
        - Different odd/even pages

        Args:
            page_num: Page number (1-based)
            doc_title: Document title
            chapter_title: Current chapter title
            author: Author name
            short_title: Short title for headers

        Returns:
            Header text with variables substituted
        """
        # Check different first page
        if self.header_footer.different_first_page and page_num == 1:
            return ""

        # Determine which template to use
        if self.header_footer.different_odd_even:
            if page_num % 2 == 1:  # Odd page
                template = self.header_footer.header_text_odd or self.header_footer.header_text
            else:  # Even page
                template = self.header_footer.header_text_even or self.header_footer.header_text
        else:
            template = self.header_footer.header_text

        # Substitute variables
        return self._substitute_variables(
            template,
            page_num=page_num,
            doc_title=doc_title,
            chapter_title=chapter_title,
            author=author,
            short_title=short_title,
        )

    def get_footer_text(
        self,
        page_num: int,
        total_pages: int = 0,
        doc_title: str = "",
    ) -> str:
        """
        Get footer text for a specific page.

        Args:
            page_num: Page number (1-based)
            total_pages: Total number of pages (0 if unknown)
            doc_title: Document title

        Returns:
            Footer text with variables substituted
        """
        return self._substitute_variables(
            self.header_footer.footer_text,
            page_num=page_num,
            total_pages=total_pages,
            doc_title=doc_title,
        )

    def _substitute_variables(
        self,
        template: str,
        page_num: int = 0,
        total_pages: int = 0,
        doc_title: str = "",
        chapter_title: str = "",
        author: str = "",
        short_title: str = "",
    ) -> str:
        """
        Substitute variables in a template string.

        Variables:
        - {page}: Current page number
        - {total}: Total pages
        - {title}: Document title
        - {chapter}: Chapter title
        - {author}: Author name
        - {short_title}: Short title
        """
        if not template:
            return ""

        result = template
        result = result.replace("{page}", str(page_num))
        result = result.replace("{total}", str(total_pages) if total_pages else "?")
        result = result.replace("{title}", doc_title)
        result = result.replace("{chapter}", chapter_title)
        result = result.replace("{author}", author)
        result = result.replace("{short_title}", short_title or doc_title[:30])

        return result

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get summary of current layout configuration.

        Returns:
            Dictionary with all configuration values
        """
        content_area = self.calculate_content_area()

        return {
            "page_size": {
                "name": self.page_size_name,
                "width_inches": self.page_size.width,
                "height_inches": self.page_size.height,
            },
            "margins": {
                "preset": self.margin_preset_name,
                **self.margins.to_dict(),
            },
            "content_area": content_area.to_dict(),
            "header_footer": {
                "style": self.header_footer_style_name,
                "header_text": self.header_footer.header_text,
                "footer_text": self.header_footer.footer_text,
                "header_alignment": self.header_footer.header_alignment,
                "footer_alignment": self.header_footer.footer_alignment,
            },
            "page_break_rules": self.page_break_rules,
        }

    def set_custom_margins(
        self,
        top: float = None,
        bottom: float = None,
        left: float = None,
        right: float = None,
    ) -> None:
        """
        Set custom margin values.

        Args:
            top: Top margin in inches
            bottom: Bottom margin in inches
            left: Left margin in inches
            right: Right margin in inches
        """
        if top is not None:
            self.margins.top = top
        if bottom is not None:
            self.margins.bottom = bottom
        if left is not None:
            self.margins.left = left
        if right is not None:
            self.margins.right = right

    def set_custom_header_footer(
        self,
        header_text: str = None,
        footer_text: str = None,
        header_alignment: str = None,
        footer_alignment: str = None,
    ) -> None:
        """
        Set custom header/footer text and alignment.

        Args:
            header_text: Custom header text template
            footer_text: Custom footer text template
            header_alignment: "left", "center", or "right"
            footer_alignment: "left", "center", or "right"
        """
        if header_text is not None:
            self.header_footer.header_text = header_text
        if footer_text is not None:
            self.header_footer.footer_text = footer_text
        if header_alignment is not None:
            self.header_footer.header_alignment = header_alignment
        if footer_alignment is not None:
            self.header_footer.footer_alignment = footer_alignment

    def enable_different_first_page(self, enabled: bool = True) -> None:
        """Enable or disable different first page header/footer."""
        self.header_footer.different_first_page = enabled

    def enable_different_odd_even(self, enabled: bool = True) -> None:
        """Enable or disable different odd/even page headers."""
        self.header_footer.different_odd_even = enabled
