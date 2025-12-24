#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Style Engine - Apply professional formatting to documents.

Stage 3 of the Formatting Engine:
- Load style templates
- Apply typography to elements
- Generate StyledDocument for export
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from copy import deepcopy

from .detector import (
    DocumentElement,
    ListElement,
    TableElement,
    ListItem,
    CodeBlockElement,
    BlockquoteElement,
    FigureElement,
    HorizontalRuleElement,
)
from .document_model import DocumentModel, TocEntry
from .utils.constants import (
    HEADING_STYLES,
    FONTS,
    PAGE_LAYOUT,
    ELEMENT_TYPES,
    LIST_STYLES,
    TABLE_STYLES,
    CODE_STYLES,
    BLOCKQUOTE_STYLES,
    FIGURE_STYLES,
    HORIZONTAL_RULE_STYLES,
)

# Import template system (lazy import to avoid circular dependency)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .templates import BaseTemplate, TemplateConfig


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StyledElement:
    """Document element with formatting applied."""

    # Original element reference
    original: DocumentElement

    # Typography
    font_name: str = "Times New Roman"
    font_size_pt: float = 12.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    all_caps: bool = False

    # Color (hex without #)
    font_color: Optional[str] = None  # e.g., "000000" for black
    background_color: Optional[str] = None

    # Spacing (in points)
    space_before_pt: float = 0.0
    space_after_pt: float = 6.0
    line_spacing: float = 1.15

    # Indentation (in inches)
    first_line_indent_inches: float = 0.0
    left_indent_inches: float = 0.0
    right_indent_inches: float = 0.0

    # Page control
    page_break_before: bool = False
    keep_with_next: bool = False
    keep_together: bool = False

    # Alignment
    alignment: str = "left"  # left, center, right, justify

    # Outline level (for TOC)
    outline_level: Optional[int] = None

    @property
    def type(self) -> str:
        """Get element type from original."""
        return self.original.type

    @property
    def content(self) -> str:
        """Get content from original."""
        return self.original.content

    @property
    def level(self) -> Optional[int]:
        """Get heading level from original."""
        return self.original.level


@dataclass
class StyledDocument:
    """Complete document with styling applied."""

    # Styled elements
    elements: List[StyledElement] = field(default_factory=list)

    # Page layout (in inches)
    page_width_inches: float = 8.5
    page_height_inches: float = 11.0
    margin_top_inches: float = 1.0
    margin_bottom_inches: float = 1.0
    margin_left_inches: float = 1.0
    margin_right_inches: float = 1.0

    # Document metadata
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None

    # Table of Contents
    toc: List[TocEntry] = field(default_factory=list)
    include_toc: bool = True
    toc_max_level: int = 3  # Include H1, H2, H3 in TOC

    # Global settings
    default_font: str = "Times New Roman"
    language: str = "en"

    def get_headings(self) -> List[StyledElement]:
        """Get all heading elements."""
        return [e for e in self.elements if e.type == ELEMENT_TYPES["HEADING"]]

    def get_word_count(self) -> int:
        """Calculate total word count."""
        return sum(len(e.content.split()) for e in self.elements)

    def __len__(self) -> int:
        return len(self.elements)


@dataclass
class StyledListItem:
    """List item with styling applied."""
    content: str
    marker: str
    level: int = 0
    font_name: str = "Times New Roman"
    font_size_pt: float = 12.0
    bold: bool = False
    italic: bool = False
    left_indent_inches: float = 0.25
    hanging_indent_inches: float = 0.25


@dataclass
class StyledList(StyledElement):
    """Extended StyledElement for lists with styled items."""
    items: List[StyledListItem] = field(default_factory=list)
    list_type: str = "bullet"  # "bullet" or "numbered"
    markers_by_level: List[str] = field(default_factory=lambda: ["•", "○", "▪", "▫"])
    indent_per_level_inches: float = 0.25

    def __repr__(self):
        return f"<StyledList {self.list_type}: {len(self.items)} items>"


@dataclass
class StyledTableCell:
    """Table cell with styling applied."""
    content: str
    alignment: str = "left"  # "left", "center", "right"
    is_header: bool = False
    font_name: str = "Times New Roman"
    font_size_pt: float = 11.0
    bold: bool = False
    background_color: Optional[str] = None
    font_color: Optional[str] = None


@dataclass
class StyledTableRow:
    """Table row with styled cells."""
    cells: List[StyledTableCell] = field(default_factory=list)
    is_header_row: bool = False


@dataclass
class StyledTable(StyledElement):
    """Extended StyledElement for tables with styled rows."""
    header_row: Optional[StyledTableRow] = None
    data_rows: List[StyledTableRow] = field(default_factory=list)
    alignments: Optional[List[str]] = None
    table_type: str = "markdown"
    table_style: str = "default"  # "default", "minimal", "striped"

    # Styling
    border_color: str = "000000"
    border_width_pt: float = 0.5
    cell_padding_inches: float = 0.05

    def __repr__(self):
        cols = len(self.header_row.cells) if self.header_row else 0
        return f"<StyledTable: {cols} cols, {len(self.data_rows)} rows>"


@dataclass
class StyledCodeBlock(StyledElement):
    """Extended StyledElement for code blocks."""
    language: str = ""
    code: str = ""
    is_fenced: bool = True
    code_style: str = "default"  # "default", "minimal", "dark"
    border_color: Optional[str] = "E0E0E0"
    border_width_pt: float = 0.5

    def __repr__(self):
        lang = self.language or "plain"
        return f"<StyledCodeBlock {lang}: {len(self.code)} chars>"


@dataclass
class StyledBlockquote(StyledElement):
    """Extended StyledElement for blockquotes."""
    quote_text: str = ""
    attribution: str = ""
    citation: str = ""
    is_multi_paragraph: bool = False
    quote_style: str = "default"  # "default", "academic", "modern"
    left_border_width_pt: float = 3.0
    left_border_color: str = "CCCCCC"

    def __repr__(self):
        attr = f" — {self.attribution}" if self.attribution else ""
        return f"<StyledBlockquote: {self.quote_text[:30]}...{attr}>"


@dataclass
class StyledFigure(StyledElement):
    """Extended StyledElement for figures/images."""
    figure_number: int = 0
    caption: str = ""
    image_url: str = ""
    alt_text: str = ""
    figure_style: str = "default"  # "default", "academic", "inline"
    caption_font_size_pt: float = 10.0
    caption_style: str = "italic"
    max_width_inches: float = 5.5
    max_height_inches: float = 7.0

    def __repr__(self):
        return f"<StyledFigure {self.figure_number}: {self.caption[:30]}...>"


@dataclass
class StyledHorizontalRule(StyledElement):
    """Extended StyledElement for horizontal rules."""
    rule_char: str = "-"
    rule_style: str = "default"  # "default", "thin", "thick", "decorative"
    line_weight_pt: float = 0.5
    line_color: str = "AAAAAA"
    width_percent: int = 100

    def __repr__(self):
        return f"<StyledHorizontalRule: {self.rule_char * 3}>"


# =============================================================================
# STYLE TEMPLATES
# =============================================================================

TEMPLATES = {
    "default": {
        "description": "Standard professional document",
        "page_size": "letter",
        "margins": "default_margins",
    },
    "book": {
        "description": "Book/novel formatting with gutter margins",
        "page_size": "a4",
        "margins": "book_margins",
        "h1_page_break": True,
    },
    "report": {
        "description": "Technical report formatting",
        "page_size": "letter",
        "margins": "default_margins",
        "include_toc": True,
    },
    "academic": {
        "description": "Academic paper formatting",
        "page_size": "letter",
        "margins": "default_margins",
        "line_spacing": 2.0,  # Double-spaced
    },
    "legal": {
        "description": "Legal document formatting",
        "page_size": "letter",
        "margins": "default_margins",
        "line_spacing": 1.5,
    },
}


# =============================================================================
# STYLE ENGINE
# =============================================================================

class StyleEngine:
    """
    Apply professional formatting styles to documents.

    Usage:
        # Method 1: Use template name
        engine = StyleEngine(template="book", output_type="print")
        styled_doc = engine.apply(document_model)

        # Method 2: Use custom template instance
        from core.formatting.templates import BookTemplate
        engine = StyleEngine(custom_template=BookTemplate())
        styled_doc = engine.apply(document_model)

        # Method 3: Auto-detect template
        from core.formatting.templates import TemplateFactory
        template_name = TemplateFactory.auto_detect(text)
        engine = StyleEngine(template=template_name)
    """

    def __init__(
        self,
        template: str = "default",
        output_type: str = "print",
        custom_template: Optional['BaseTemplate'] = None,
    ):
        """
        Initialize style engine.

        Args:
            template: Style template name ("default", "book", "report", "academic", "legal")
            output_type: Font style ("print" for serif, "digital" for sans-serif)
            custom_template: Optional custom template instance (overrides template name)
        """
        self.output_type = output_type
        self._custom_template = custom_template
        self._template_config = None

        # If custom template provided, use it
        if custom_template is not None:
            self.template_name = custom_template.name
            self._template_config = custom_template.get_config()
            self.template = TEMPLATES.get(self.template_name, TEMPLATES["default"])
            # Use fonts from template config
            self._setup_fonts_from_template()
        elif template in ["book", "report", "legal", "academic"]:
            # Use TemplateFactory for known templates
            from .templates import TemplateFactory
            self.template_name = template
            self._custom_template = TemplateFactory.get_template(template)
            self._template_config = self._custom_template.get_config()
            self.template = TEMPLATES.get(template, TEMPLATES["default"])
            self._setup_fonts_from_template()
        else:
            self.template_name = template
            self.template = TEMPLATES.get(template, TEMPLATES["default"])
            self.fonts = FONTS.get(output_type, FONTS["print"])

        self._heading_styles = deepcopy(HEADING_STYLES)

        # Apply template-specific overrides
        self._apply_template_overrides()

    def _setup_fonts_from_template(self) -> None:
        """Setup fonts based on template configuration."""
        if self._template_config is None:
            self.fonts = FONTS.get(self.output_type, FONTS["print"])
            return

        config = self._template_config

        # Extract font from heading styles (H1) or body style
        heading_font = None
        body_font = None

        if config.heading_styles and "H1" in config.heading_styles:
            heading_font = config.heading_styles["H1"].get("font_name")

        if config.body_style:
            body_font = config.body_style.get("font_name")

        # Build fonts dict
        self.fonts = {
            "heading": heading_font or FONTS.get(self.output_type, FONTS["print"])["heading"],
            "body": body_font or FONTS.get(self.output_type, FONTS["print"])["body"],
            "mono": "Consolas",
        }

    def _apply_template_overrides(self) -> None:
        """Apply template-specific style overrides."""
        template = self.template

        # Line spacing override
        if "line_spacing" in template:
            for style in self._heading_styles.values():
                if "line_spacing" not in style:
                    style["line_spacing"] = template["line_spacing"]

        # H1 page break override
        if template.get("h1_page_break", True):
            self._heading_styles["H1"]["page_break_before"] = True

    def apply(self, model: DocumentModel) -> StyledDocument:
        """
        Apply styles to all elements in DocumentModel.

        Args:
            model: DocumentModel with detected elements

        Returns:
            StyledDocument with formatting applied
        """
        styled_doc = StyledDocument()

        # Set page layout
        self._setup_page_layout(styled_doc)

        # Set document metadata
        styled_doc.title = model.metadata.get("title")
        styled_doc.language = model.metadata.get("language", "en")
        styled_doc.default_font = self.fonts["body"]

        # Copy TOC
        styled_doc.toc = model.toc.copy()
        styled_doc.include_toc = self.template.get("include_toc", True)

        # Style each element
        for element in model.elements:
            styled_element = self._style_element(element)
            styled_doc.elements.append(styled_element)

        return styled_doc

    def _setup_page_layout(self, styled_doc: StyledDocument) -> None:
        """Configure page size and margins."""
        # Get page size and margins from template config if available
        if self._template_config is not None:
            page_size_name = self._template_config.page_size.lower()
            margin_name = self._template_config.margins
        else:
            page_size_name = self.template.get("page_size", "letter")
            margin_name = self.template.get("margins", "default_margins")

        # Page size
        page_size = PAGE_LAYOUT.get(page_size_name, PAGE_LAYOUT["letter"])
        styled_doc.page_width_inches = page_size["width_inches"]
        styled_doc.page_height_inches = page_size["height_inches"]

        # Margins - handle both old format ("default_margins") and new format ("normal")
        margin_key = f"{margin_name}_margins" if not margin_name.endswith("_margins") else margin_name
        margins = PAGE_LAYOUT.get(margin_key, PAGE_LAYOUT.get(margin_name, PAGE_LAYOUT["default_margins"]))
        styled_doc.margin_top_inches = margins["top_inches"]
        styled_doc.margin_bottom_inches = margins["bottom_inches"]
        styled_doc.margin_left_inches = margins["left_inches"]
        styled_doc.margin_right_inches = margins["right_inches"]

    def get_template_config(self) -> Optional['TemplateConfig']:
        """
        Get the current template configuration.

        Returns:
            TemplateConfig if using custom template, None otherwise
        """
        return self._template_config

    def get_custom_template(self) -> Optional['BaseTemplate']:
        """
        Get the custom template instance if set.

        Returns:
            BaseTemplate instance if set, None otherwise
        """
        return self._custom_template

    def _style_element(self, element: DocumentElement) -> StyledElement:
        """
        Style a single element based on its type.

        Args:
            element: DocumentElement to style

        Returns:
            StyledElement with formatting
        """
        if element.type == ELEMENT_TYPES["HEADING"]:
            return self.style_heading(element)
        elif element.type == ELEMENT_TYPES["PARAGRAPH"]:
            return self.style_paragraph(element)
        elif element.type in [ELEMENT_TYPES["LIST_BULLET"], ELEMENT_TYPES["LIST_NUMBERED"]]:
            return self.style_list(element)
        elif element.type == ELEMENT_TYPES["TABLE"]:
            return self.style_table(element)
        elif element.type == ELEMENT_TYPES["CODE_BLOCK"]:
            return self.style_code_block(element)
        elif element.type == ELEMENT_TYPES["QUOTE"]:
            return self.style_quote(element)
        elif element.type == ELEMENT_TYPES["IMAGE"]:
            return self.style_figure(element)
        elif element.type == ELEMENT_TYPES["HORIZONTAL_RULE"]:
            return self.style_horizontal_rule(element)
        else:
            # Default: treat as paragraph
            return self.style_paragraph(element)

    def style_heading(self, element: DocumentElement) -> StyledElement:
        """
        Apply heading styles based on level.

        Args:
            element: Heading element (level 1-4)

        Returns:
            StyledElement with heading formatting
        """
        level = element.level or 1
        style_key = f"H{min(level, 4)}"

        # Try to get style from custom template config first
        if self._template_config is not None and self._template_config.heading_styles:
            style = self._template_config.heading_styles.get(
                style_key,
                self._template_config.heading_styles.get("H4", self._heading_styles["H1"])
            )
            font_name = style.get("font_name", self.fonts["heading"])
        else:
            style = self._heading_styles.get(style_key, self._heading_styles["H1"])
            font_name = self.fonts["heading"]

        # Handle color from template
        font_color = style.get("color") if style.get("color") else None

        return StyledElement(
            original=element,
            font_name=font_name,
            font_size_pt=style.get("font_size_pt", 14),
            bold=style.get("bold", True),
            italic=style.get("italic", False),
            all_caps=style.get("all_caps", False),
            font_color=font_color,
            space_before_pt=style.get("space_before_pt", 12),
            space_after_pt=style.get("space_after_pt", 6),
            line_spacing=style.get("line_spacing", 1.15),
            page_break_before=style.get("page_break_before", False),
            keep_with_next=style.get("keep_with_next", True),
            alignment=style.get("alignment", "left"),
            outline_level=level,
        )

    def style_paragraph(self, element: DocumentElement) -> StyledElement:
        """
        Apply body text styles.

        Args:
            element: Paragraph element

        Returns:
            StyledElement with paragraph formatting
        """
        # Try to get style from custom template config first
        if self._template_config is not None and self._template_config.body_style:
            body_style = self._template_config.body_style
            font_name = body_style.get("font_name", self.fonts["body"])
            line_spacing = body_style.get("line_spacing", 1.15)
            first_line_indent = body_style.get("first_line_indent_inches", 0)
        else:
            body_style = self._heading_styles["BODY"]
            font_name = self.fonts["body"]
            line_spacing = self.template.get("line_spacing", PAGE_LAYOUT["line_spacing"])
            first_line_indent = PAGE_LAYOUT["first_line_indent_inches"]

        return StyledElement(
            original=element,
            font_name=font_name,
            font_size_pt=body_style.get("font_size_pt", 12),
            bold=body_style.get("bold", False),
            italic=body_style.get("italic", False),
            space_before_pt=body_style.get("space_before_pt", 0),
            space_after_pt=body_style.get("space_after_pt", 6),
            line_spacing=line_spacing,
            first_line_indent_inches=first_line_indent,
            alignment=body_style.get("alignment", "justify"),
        )

    def style_list(self, element: DocumentElement) -> StyledElement:
        """
        Apply list formatting with structured items.

        Args:
            element: List element (bullet or numbered)

        Returns:
            StyledList with item formatting
        """
        # Get list style based on type
        list_type = "bullet"
        if element.type == ELEMENT_TYPES["LIST_NUMBERED"]:
            list_type = "numbered"

        list_style = LIST_STYLES.get(list_type, LIST_STYLES["bullet"])
        nested_style = LIST_STYLES.get("nested", {})

        # Create styled items if element is ListElement
        styled_items = []
        if isinstance(element, ListElement) and element.items:
            for item in element.items:
                level = item.level
                indent = list_style["indent_inches"] + (level * nested_style.get("indent_per_level_inches", 0.25))

                # Determine marker
                if list_type == "bullet":
                    symbols = list_style.get("symbols_by_level", ["•", "○", "▪", "▫"])
                    marker = symbols[min(level, len(symbols) - 1)]
                else:
                    formats = list_style.get("formats_by_level", ["1.", "a.", "i.", "A."])
                    marker = item.marker or formats[min(level, len(formats) - 1)]

                styled_item = StyledListItem(
                    content=item.content,
                    marker=marker,
                    level=level,
                    font_name=self.fonts["body"],
                    font_size_pt=12.0,
                    left_indent_inches=indent,
                    hanging_indent_inches=list_style.get("hanging_indent_inches", 0.25),
                )
                styled_items.append(styled_item)

        # Create StyledList
        return StyledList(
            original=element,
            font_name=self.fonts["body"],
            font_size_pt=12.0,
            space_before_pt=list_style.get("space_before_pt", 3.0),
            space_after_pt=list_style.get("space_after_pt", 3.0),
            line_spacing=1.15,
            left_indent_inches=list_style.get("indent_inches", 0.25),
            alignment="left",
            items=styled_items,
            list_type=list_type,
            markers_by_level=list_style.get("symbols_by_level", ["•", "○", "▪", "▫"]),
            indent_per_level_inches=nested_style.get("indent_per_level_inches", 0.25),
        )

    def style_table(self, element: DocumentElement, table_style: str = "default") -> StyledElement:
        """
        Apply table styles with structured rows and cells.

        Args:
            element: Table element
            table_style: Style name ("default", "minimal", "striped")

        Returns:
            StyledTable with row/cell formatting
        """
        style = TABLE_STYLES.get(table_style, TABLE_STYLES["default"])

        # Create styled header row if element is TableElement
        header_row = None
        data_rows = []
        alignments = None

        if isinstance(element, TableElement):
            alignments = element.alignments

            # Style header row
            if element.headers:
                header_cells = []
                for idx, header in enumerate(element.headers):
                    align = alignments[idx] if alignments and idx < len(alignments) else "center"
                    cell = StyledTableCell(
                        content=header,
                        alignment=style.get("header_alignment", align),
                        is_header=True,
                        font_name=self.fonts["body"],
                        font_size_pt=style.get("font_size_pt", 11.0),
                        bold=style.get("header_bold", True),
                        background_color=style.get("header_background"),
                        font_color=style.get("header_font_color"),
                    )
                    header_cells.append(cell)
                header_row = StyledTableRow(cells=header_cells, is_header_row=True)

            # Style data rows
            for row_idx, row in enumerate(element.rows):
                row_cells = []
                for col_idx, cell_content in enumerate(row):
                    align = alignments[col_idx] if alignments and col_idx < len(alignments) else "left"

                    # Handle striped row backgrounds
                    bg_color = None
                    if table_style == "striped":
                        if row_idx % 2 == 0:
                            bg_color = style.get("even_row_background")
                        else:
                            bg_color = style.get("odd_row_background")

                    cell = StyledTableCell(
                        content=cell_content,
                        alignment=align,
                        is_header=False,
                        font_name=self.fonts["body"],
                        font_size_pt=style.get("font_size_pt", 11.0),
                        bold=False,
                        background_color=bg_color,
                    )
                    row_cells.append(cell)
                data_rows.append(StyledTableRow(cells=row_cells, is_header_row=False))

        # Create StyledTable
        return StyledTable(
            original=element,
            font_name=self.fonts["body"],
            font_size_pt=style.get("font_size_pt", 11.0),
            space_before_pt=6.0,
            space_after_pt=6.0,
            alignment="left",
            keep_together=True,
            header_row=header_row,
            data_rows=data_rows,
            alignments=alignments,
            table_type=element.table_type if isinstance(element, TableElement) else "markdown",
            table_style=table_style,
            border_color=style.get("border_color", "000000"),
            border_width_pt=style.get("border_width_pt", 0.5),
            cell_padding_inches=style.get("cell_padding_inches", 0.05),
        )

    def style_code_block(self, element: DocumentElement, code_style_name: str = "default") -> StyledCodeBlock:
        """
        Apply code block styles.

        Args:
            element: Code block element
            code_style_name: Style name ("default", "minimal", "dark")

        Returns:
            StyledCodeBlock with code formatting
        """
        style = CODE_STYLES.get(code_style_name, CODE_STYLES["default"])

        # Extract code and language if CodeBlockElement
        language = ""
        code = element.content
        is_fenced = True

        if isinstance(element, CodeBlockElement):
            language = element.language
            code = element.code
            is_fenced = element.is_fenced

        return StyledCodeBlock(
            original=element,
            font_name=style.get("font_name", "Consolas"),
            font_size_pt=style.get("font_size_pt", 10.0),
            space_before_pt=style.get("space_before_pt", 12.0),
            space_after_pt=style.get("space_after_pt", 12.0),
            line_spacing=style.get("line_spacing", 1.0),
            background_color=style.get("background_color", "F5F5F5"),
            left_indent_inches=style.get("left_indent_inches", 0.25),
            right_indent_inches=style.get("right_indent_inches", 0.25),
            alignment="left",
            keep_together=True,
            language=language,
            code=code,
            is_fenced=is_fenced,
            code_style=code_style_name,
            border_color=style.get("border_color", "E0E0E0"),
            border_width_pt=style.get("border_width_pt", 0.5),
        )

    def style_quote(self, element: DocumentElement, quote_style_name: str = "default") -> StyledBlockquote:
        """
        Apply blockquote styles.

        Args:
            element: Quote element
            quote_style_name: Style name ("default", "academic", "modern")

        Returns:
            StyledBlockquote with quote formatting
        """
        style = BLOCKQUOTE_STYLES.get(quote_style_name, BLOCKQUOTE_STYLES["default"])

        # Extract quote details if BlockquoteElement
        quote_text = element.content
        attribution = ""
        citation = ""
        is_multi_paragraph = False

        if isinstance(element, BlockquoteElement):
            quote_text = element.quote_text
            attribution = element.attribution
            citation = element.citation
            is_multi_paragraph = element.is_multi_paragraph

        return StyledBlockquote(
            original=element,
            font_name=self.fonts["body"],
            font_size_pt=style.get("font_size_pt", 11.0),
            italic=(style.get("font_style") == "italic"),
            space_before_pt=style.get("space_before_pt", 12.0),
            space_after_pt=style.get("space_after_pt", 12.0),
            line_spacing=style.get("line_spacing", 1.15),
            left_indent_inches=style.get("left_indent_inches", 0.5),
            right_indent_inches=style.get("right_indent_inches", 0.5),
            alignment="justify",
            quote_text=quote_text,
            attribution=attribution,
            citation=citation,
            is_multi_paragraph=is_multi_paragraph,
            quote_style=quote_style_name,
            left_border_width_pt=style.get("left_border_width_pt", 3.0),
            left_border_color=style.get("left_border_color", "CCCCCC"),
        )

    def style_figure(self, element: DocumentElement, figure_style_name: str = "default") -> StyledFigure:
        """
        Apply figure/image styles.

        Args:
            element: Figure element
            figure_style_name: Style name ("default", "academic", "inline")

        Returns:
            StyledFigure with figure formatting
        """
        style = FIGURE_STYLES.get(figure_style_name, FIGURE_STYLES["default"])

        # Extract figure details if FigureElement
        figure_number = 0
        caption = ""
        image_url = ""
        alt_text = ""

        if isinstance(element, FigureElement):
            figure_number = element.figure_number
            caption = element.caption
            image_url = element.image_url
            alt_text = element.alt_text

        return StyledFigure(
            original=element,
            font_name=self.fonts["body"],
            font_size_pt=12.0,
            space_before_pt=style.get("space_before_pt", 12.0),
            space_after_pt=style.get("space_after_pt", 12.0),
            alignment=style.get("alignment", "center"),
            keep_together=True,
            figure_number=figure_number,
            caption=caption,
            image_url=image_url,
            alt_text=alt_text,
            figure_style=figure_style_name,
            caption_font_size_pt=style.get("caption_font_size_pt", 10.0),
            caption_style=style.get("caption_style", "italic"),
            max_width_inches=style.get("max_width_inches", 5.5),
            max_height_inches=style.get("max_height_inches", 7.0),
        )

    def style_horizontal_rule(self, element: DocumentElement, rule_style_name: str = "default") -> StyledHorizontalRule:
        """
        Apply horizontal rule styles.

        Args:
            element: Horizontal rule element
            rule_style_name: Style name ("default", "thin", "thick", "decorative")

        Returns:
            StyledHorizontalRule with rule formatting
        """
        style = HORIZONTAL_RULE_STYLES.get(rule_style_name, HORIZONTAL_RULE_STYLES["default"])

        # Extract rule character if HorizontalRuleElement
        rule_char = "-"
        if isinstance(element, HorizontalRuleElement):
            rule_char = element.rule_char

        return StyledHorizontalRule(
            original=element,
            font_name=self.fonts["body"],
            space_before_pt=style.get("space_before_pt", 12.0),
            space_after_pt=style.get("space_after_pt", 12.0),
            alignment=style.get("alignment", "left"),
            rule_char=rule_char,
            rule_style=rule_style_name,
            line_weight_pt=style.get("line_weight_pt", 0.5),
            line_color=style.get("line_color", "AAAAAA"),
            width_percent=style.get("width_percent", 100),
        )

    def get_style_summary(self) -> Dict[str, Any]:
        """
        Get summary of applied styles.

        Returns:
            Dictionary with style information
        """
        return {
            "template": self.template_name,
            "output_type": self.output_type,
            "fonts": self.fonts,
            "heading_styles": {
                k: {
                    "font_size": v["font_size_pt"],
                    "bold": v.get("bold", False),
                    "space_before": v["space_before_pt"],
                    "space_after": v["space_after_pt"],
                }
                for k, v in self._heading_styles.items()
                if k.startswith("H")
            },
        }
