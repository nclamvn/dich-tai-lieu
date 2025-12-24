#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structure Detector - Detect document structure from raw text.

Stage 1 of the Formatting Engine:
- Detect headings (H1-H4)
- Detect lists (bullet, numbered)
- Detect code blocks
- Detect quotes
- Detect tables
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from .utils.constants import ELEMENT_TYPES, HEURISTIC_THRESHOLDS
from .utils.heading_patterns import (
    H1_PATTERNS_EN, H1_PATTERNS_VI,
    H2_PATTERNS_EN, H2_PATTERNS_VI,
    H3_PATTERNS_EN, H3_PATTERNS_VI,
    H4_PATTERNS,
    match_heading_pattern,
    get_heading_level,
    is_likely_heading_heuristic,
    detect_language,
)
from .utils.list_patterns import (
    is_bullet_item,
    is_numbered_item,
    is_list_item,
    is_list_continuation,
    calculate_indent_level,
    detect_list_type,
)
from .utils.table_patterns import (
    is_markdown_table_row,
    is_markdown_separator,
    detect_markdown_table,
    detect_ascii_table,
    is_ascii_border,
    DetectedTable,
)
from .utils.advanced_patterns import (
    is_fenced_code_start,
    is_fenced_code_end,
    is_indented_code,
    is_blockquote_line,
    is_horizontal_rule,
    detect_code_language,
    extract_quote_attribution,
    find_footnote_refs,
    find_footnote_defs,
    parse_markdown_image,
    parse_figure_caption,
    FENCED_CODE_START,
    FOOTNOTE_REF_PATTERN,
    FOOTNOTE_DEF_PATTERN,
    MARKDOWN_IMAGE,
    FIGURE_REF_PATTERN,
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LineContext:
    """Context information for a line during analysis."""
    prev_line: Optional[str] = None
    next_line: Optional[str] = None
    prev_element_type: Optional[str] = None
    line_number: int = 0
    is_after_blank: bool = False
    is_before_blank: bool = False


@dataclass
class DocumentElement:
    """
    Represents a structural element in the document.

    Types: heading, paragraph, list_bullet, list_numbered,
           table, code_block, quote, image, footnote, etc.
    """
    type: str
    content: str
    level: Optional[int] = None  # For headings: 1-4, for lists: nesting level
    element_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    line_start: int = 0
    line_end: int = 0
    confidence: float = 1.0  # Confidence score (1.0 = pattern match, <1.0 = heuristic)

    def __repr__(self):
        if self.type == "heading":
            return f"<H{self.level}: {self.content[:50]}...>" if len(self.content) > 50 else f"<H{self.level}: {self.content}>"
        return f"<{self.type}: {self.content[:30]}...>" if len(self.content) > 30 else f"<{self.type}: {self.content}>"


@dataclass
class ListItem:
    """Represents a single list item within a list element."""
    content: str
    marker: str  # The bullet or number marker (e.g., "•", "1.", "a)")
    level: int = 0  # Nesting level (0 = top level)
    children: List["ListItem"] = field(default_factory=list)

    def __repr__(self):
        return f"<ListItem L{self.level}: {self.marker} {self.content[:30]}...>" if len(self.content) > 30 else f"<ListItem L{self.level}: {self.marker} {self.content}>"


@dataclass
class ListElement(DocumentElement):
    """Extended DocumentElement for lists with structured items."""
    items: List[ListItem] = field(default_factory=list)
    list_type: str = "bullet"  # "bullet" or "numbered"

    def __repr__(self):
        return f"<List {self.list_type}: {len(self.items)} items>"


@dataclass
class TableCell:
    """Represents a single cell in a table."""
    content: str
    alignment: str = "left"  # "left", "center", "right"
    is_header: bool = False


@dataclass
class TableRow:
    """Represents a row in a table."""
    cells: List[TableCell] = field(default_factory=list)
    is_header_row: bool = False


@dataclass
class TableElement(DocumentElement):
    """Extended DocumentElement for tables with structured data."""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    alignments: Optional[List[str]] = None
    table_type: str = "markdown"  # "markdown", "ascii", "plain"
    has_header: bool = True

    def __repr__(self):
        cols = len(self.headers) if self.headers else (len(self.rows[0]) if self.rows else 0)
        return f"<Table {self.table_type}: {cols} cols, {len(self.rows)} rows>"


@dataclass
class CodeBlockElement(DocumentElement):
    """Extended DocumentElement for code blocks."""
    language: str = ""           # python, javascript, sql, etc.
    code: str = ""               # Code content without fences
    is_fenced: bool = True       # True if ```, False if indented

    def __repr__(self):
        lang = self.language or "plain"
        return f"<CodeBlock {lang}: {len(self.code)} chars>"


@dataclass
class FormulaElement(DocumentElement):
    """Extended DocumentElement for mathematical formulas."""
    formula_type: str = ""       # LATEX_DISPLAY, LATEX_INLINE, CHEMICAL, etc.
    is_block: bool = False       # True for display math, False for inline
    placeholder: str = ""        # STEM placeholder if any (⟪STEM_*⟫)
    environment_name: str = ""   # For LaTeX environments (equation, align, etc.)

    def __repr__(self):
        ftype = self.formula_type or "math"
        mode = "block" if self.is_block else "inline"
        return f"<Formula {ftype} ({mode}): {self.content[:30]}...>" if len(self.content) > 30 else f"<Formula {ftype} ({mode}): {self.content}>"


@dataclass
class BlockquoteElement(DocumentElement):
    """Extended DocumentElement for blockquotes."""
    quote_text: str = ""
    attribution: str = ""        # Author name
    citation: str = ""           # (Year) or source
    is_multi_paragraph: bool = False

    def __repr__(self):
        attr = f" — {self.attribution}" if self.attribution else ""
        return f"<Blockquote: {self.quote_text[:40]}...{attr}>" if len(self.quote_text) > 40 else f"<Blockquote: {self.quote_text}{attr}>"


@dataclass
class FootnoteRef:
    """Footnote reference in text."""
    marker: str                  # "1" or "note-1"
    position: int                # Character position in text

    def __repr__(self):
        return f"<FootnoteRef [{self.marker}] at {self.position}>"


@dataclass
class FootnoteDef:
    """Footnote definition."""
    marker: str
    text: str
    line_number: int = 0

    def __repr__(self):
        return f"<FootnoteDef [{self.marker}]: {self.text[:30]}...>" if len(self.text) > 30 else f"<FootnoteDef [{self.marker}]: {self.text}>"


@dataclass
class FigureElement(DocumentElement):
    """Extended DocumentElement for figures/images."""
    figure_number: int = 0
    caption: str = ""
    image_url: str = ""          # If Markdown image
    alt_text: str = ""

    def __repr__(self):
        return f"<Figure {self.figure_number}: {self.caption[:30]}...>" if len(self.caption) > 30 else f"<Figure {self.figure_number}: {self.caption}>"


@dataclass
class HorizontalRuleElement(DocumentElement):
    """Element representing a horizontal rule/divider."""
    rule_char: str = "-"         # The character used (-, *, _)

    def __repr__(self):
        return f"<HorizontalRule: {self.rule_char * 3}>"


# =============================================================================
# STRUCTURE DETECTOR
# =============================================================================

class StructureDetector:
    """
    Detect document structure from raw text.

    Main entry point for Stage 1 of the Formatting Engine.

    Supports STEM integration for enhanced code and formula detection.
    When use_stem=True, reuses STEM module's detectors for consistency
    with the translation pipeline.
    """

    def __init__(self, language: str = "auto", use_stem: bool = True):
        """
        Initialize detector.

        Args:
            language: "en", "vi", or "auto" (detect automatically)
            use_stem: If True, use STEM module for code/formula detection
        """
        self.language = language
        self.use_stem = use_stem
        self._detected_language = None
        self._stem = None

        # Initialize STEM integration if requested
        if use_stem:
            try:
                from .utils.stem_integration import get_stem_integration
                self._stem = get_stem_integration()
            except ImportError:
                self._stem = None

    def detect(self, text: str) -> List[DocumentElement]:
        """
        Main method - detect all structural elements from text.

        Args:
            text: Raw document text

        Returns:
            List of DocumentElement objects representing document structure
        """
        if not text or not text.strip():
            return []

        # Auto-detect language if needed
        if self.language == "auto":
            self._detected_language = detect_language(text)
        else:
            self._detected_language = self.language

        # Split into lines
        lines = text.split('\n')

        # First pass: Detect all elements
        elements = self._first_pass(lines)

        # Second pass: Apply heuristics for undetected headings
        elements = self._second_pass(elements, lines)

        # Third pass: Validate and fix heading hierarchy
        elements = self._validate_hierarchy(elements)

        return elements

    def _first_pass(self, lines: List[str]) -> List[DocumentElement]:
        """
        First pass: Detect elements using explicit patterns.

        Args:
            lines: List of text lines

        Returns:
            List of DocumentElement objects
        """
        elements = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines (will be handled as paragraph separators)
            if not stripped:
                i += 1
                continue

            # Build context
            context = LineContext(
                prev_line=lines[i-1] if i > 0 else None,
                next_line=lines[i+1] if i < n-1 else None,
                line_number=i,
                is_after_blank=(i > 0 and not lines[i-1].strip()),
                is_before_blank=(i < n-1 and not lines[i+1].strip()),
            )

            # Try to detect element type
            element = None

            # Check for horizontal rule (---, ***, ___)
            if is_horizontal_rule(stripped):
                element = self._detect_horizontal_rule(stripped, i)
                elements.append(element)
                i += 1
                continue

            # Check for code block (```...```)
            if stripped.startswith('```'):
                element, consumed = self._detect_code_block(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Check for indented code block (4 spaces or tab)
            is_indented, _ = is_indented_code(line)
            if is_indented and context.is_after_blank:
                element, consumed = self._detect_indented_code(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Check for markdown image ![alt](url)
            if stripped.startswith('!['):
                element = self._detect_markdown_image(stripped, i)
                if element:
                    elements.append(element)
                    i += 1
                    continue

            # Check for figure caption (Figure 1: ...)
            figure_match = parse_figure_caption(stripped)
            if figure_match:
                element = self._detect_figure_caption(stripped, figure_match, i)
                elements.append(element)
                i += 1
                continue

            # Check for bullet list BEFORE headings (more specific pattern)
            if self._is_bullet_list(stripped):
                element, consumed = self._detect_list(lines, i, "bullet")
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Check for numbered list BEFORE headings (more specific pattern)
            if self._is_numbered_list(stripped):
                element, consumed = self._detect_list(lines, i, "numbered")
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Check for heading (after lists to avoid false positives like "1. Item")
            heading_level = get_heading_level(stripped, self._detected_language)
            if heading_level:
                element = DocumentElement(
                    type=ELEMENT_TYPES["HEADING"],
                    content=stripped,
                    level=heading_level,
                    line_start=i,
                    line_end=i,
                    confidence=1.0,
                )
                elements.append(element)
                i += 1
                continue

            # Check for quote (> prefix)
            if stripped.startswith('>'):
                element, consumed = self._detect_quote(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Check for table (markdown | delimited or ASCII +---+)
            if (('|' in stripped and stripped.count('|') >= 2) or
                is_markdown_table_row(stripped) or
                is_ascii_border(stripped)):
                element, consumed = self._detect_table(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue

            # Default: paragraph
            element, consumed = self._detect_paragraph(lines, i)
            elements.append(element)
            i += consumed

        return elements

    def _second_pass(self, elements: List[DocumentElement], lines: List[str]) -> List[DocumentElement]:
        """
        Second pass: Apply heuristics to paragraphs that might be headings.

        Args:
            elements: Elements from first pass
            lines: Original lines

        Returns:
            Updated elements list
        """
        updated = []

        for i, elem in enumerate(elements):
            # Only check paragraphs
            if elem.type != ELEMENT_TYPES["PARAGRAPH"]:
                updated.append(elem)
                continue

            # Get context
            prev_elem = elements[i-1] if i > 0 else None
            next_elem = elements[i+1] if i < len(elements)-1 else None

            prev_line = lines[elem.line_start - 1] if elem.line_start > 0 else None
            next_line = lines[elem.line_end + 1] if elem.line_end < len(lines) - 1 else None

            # Apply heuristics
            is_heading, suggested_level = is_likely_heading_heuristic(
                elem.content,
                prev_line,
                next_line,
                max_chars=HEURISTIC_THRESHOLDS["max_heading_chars"]
            )

            if is_heading and suggested_level:
                # Convert paragraph to heading
                elem.type = ELEMENT_TYPES["HEADING"]
                elem.level = suggested_level
                elem.confidence = 0.7  # Lower confidence for heuristic detection

            updated.append(elem)

        return updated

    def _validate_hierarchy(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """
        Third pass: Validate and fix heading hierarchy.

        Rules:
        - No skipped levels (H1 → H3 is invalid)
        - First heading should be H1 or H2

        Args:
            elements: Elements to validate

        Returns:
            Validated elements
        """
        headings = [e for e in elements if e.type == ELEMENT_TYPES["HEADING"]]

        if not headings:
            return elements

        # Track last heading level
        last_level = 0

        for heading in headings:
            current_level = heading.level

            # Check for skipped levels
            if current_level > last_level + 1 and last_level > 0:
                # Skipped level - adjust to valid level
                heading.level = last_level + 1
                heading.metadata["adjusted_from"] = current_level
                heading.metadata["adjustment_reason"] = "hierarchy_validation"

            last_level = heading.level

        return elements

    # =========================================================================
    # ELEMENT DETECTION HELPERS
    # =========================================================================

    def _is_bullet_list(self, line: str) -> bool:
        """Check if line starts a bullet list using enhanced patterns."""
        is_bullet, _, _, _ = is_bullet_item(line)
        return is_bullet

    def _is_numbered_list(self, line: str) -> bool:
        """Check if line starts a numbered list using enhanced patterns."""
        is_num, _, _, _ = is_numbered_item(line)
        return is_num

    def _detect_code_block(self, lines: List[str], start: int) -> tuple:
        """Detect a fenced code block (```) and return CodeBlockElement."""
        if not lines[start].strip().startswith('```'):
            return None, 1

        # Extract language from opening fence
        is_start, language = is_fenced_code_start(lines[start])
        if not is_start:
            return None, 1

        code_lines = []
        i = start + 1

        while i < len(lines):
            if is_fenced_code_end(lines[i]):
                break
            code_lines.append(lines[i])
            i += 1

        code_content = '\n'.join(code_lines)

        # Auto-detect language if not specified
        if not language and code_content.strip():
            language = detect_code_language(code_content)

        # Build full content with fences for storage
        full_content = '\n'.join(lines[start:i + 1])

        element = CodeBlockElement(
            type=ELEMENT_TYPES["CODE_BLOCK"],
            content=full_content,
            line_start=start,
            line_end=i,
            language=language or "",
            code=code_content,
            is_fenced=True,
            metadata={"language": language or ""},
        )

        return element, i - start + 1

    def _detect_indented_code(self, lines: List[str], start: int) -> tuple:
        """Detect an indented code block (4 spaces or tab)."""
        code_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            is_code, content = is_indented_code(line)

            if is_code:
                code_lines.append(content)
                i += 1
            elif not line.strip():
                # Empty line might be part of code block
                if i + 1 < len(lines):
                    next_is_code, _ = is_indented_code(lines[i + 1])
                    if next_is_code:
                        code_lines.append("")
                        i += 1
                        continue
                break
            else:
                break

        if not code_lines:
            return None, 1

        code_content = '\n'.join(code_lines)

        # Auto-detect language
        language = detect_code_language(code_content)

        element = CodeBlockElement(
            type=ELEMENT_TYPES["CODE_BLOCK"],
            content=code_content,
            line_start=start,
            line_end=i - 1,
            language=language,
            code=code_content,
            is_fenced=False,
            metadata={"language": language},
        )

        return element, i - start

    def _detect_horizontal_rule(self, line: str, line_num: int) -> HorizontalRuleElement:
        """Detect a horizontal rule line."""
        # Determine the character used
        rule_char = "-"
        if "*" in line:
            rule_char = "*"
        elif "_" in line:
            rule_char = "_"

        return HorizontalRuleElement(
            type=ELEMENT_TYPES["HORIZONTAL_RULE"],
            content=line,
            line_start=line_num,
            line_end=line_num,
            rule_char=rule_char,
        )

    # =========================================================================
    # STEM Integration Methods
    # =========================================================================

    def detect_stem_elements(self, text: str) -> List[DocumentElement]:
        """
        Detect STEM elements (code + formulas) using STEM integration.

        Uses STEM module's detectors when available for consistency
        with the translation pipeline.

        Args:
            text: Raw text to scan

        Returns:
            List of CodeBlockElement and FormulaElement
        """
        if not self._stem:
            return []

        elements = []
        stem_results = self._stem.detect_all_stem_elements(text)

        for result in stem_results:
            element = self._convert_stem_result(result)
            if element:
                elements.append(element)

        return elements

    def _convert_stem_result(self, result) -> Optional[DocumentElement]:
        """
        Convert STEM DetectionResult to Formatting DocumentElement.

        Args:
            result: DetectionResult from STEM integration

        Returns:
            CodeBlockElement, FormulaElement, or None
        """
        from core.shared.element_types import ElementType

        if result.element_type == ElementType.CODE_BLOCK:
            return CodeBlockElement(
                type=ELEMENT_TYPES["CODE_BLOCK"],
                content=result.content,
                line_start=result.line_number,
                line_end=result.line_number,
                language=result.language or "",
                code=result.metadata.get("code", result.content),
                is_fenced=result.is_fenced if result.is_fenced is not None else True,
                metadata={"source": "stem"},
            )
        elif result.element_type == ElementType.CODE_INLINE:
            return CodeBlockElement(
                type=ELEMENT_TYPES["CODE_BLOCK"],
                content=result.content,
                line_start=result.line_number,
                line_end=result.line_number,
                language="",
                code=result.content,
                is_fenced=False,
                metadata={"source": "stem", "inline": True},
            )
        elif result.element_type in [ElementType.FORMULA_BLOCK, ElementType.FORMULA_INLINE, ElementType.CHEMICAL_FORMULA]:
            return FormulaElement(
                type=ELEMENT_TYPES.get("FORMULA", "formula"),
                content=result.content,
                line_start=result.line_number,
                line_end=result.line_number,
                formula_type=result.formula_type or "",
                is_block=(result.element_type == ElementType.FORMULA_BLOCK),
                placeholder=result.placeholder or "",
                environment_name=result.environment_name or "",
                metadata={"source": "stem"},
            )

        return None

    def has_stem_content(self, text: str) -> bool:
        """
        Quick check if text contains STEM content.

        Args:
            text: Text to check

        Returns:
            True if code or formulas are detected
        """
        if self._stem:
            return self._stem.has_stem_content(text)

        # Fallback quick check
        return '```' in text or '$' in text or '\\[' in text

    def _detect_markdown_image(self, line: str, line_num: int) -> Optional[FigureElement]:
        """Detect a markdown image ![alt](url)."""
        result = parse_markdown_image(line)
        if not result:
            return None

        alt_text, url = result

        return FigureElement(
            type=ELEMENT_TYPES["IMAGE"],
            content=line,
            line_start=line_num,
            line_end=line_num,
            figure_number=0,  # Will be assigned during styling
            caption=alt_text,
            image_url=url,
            alt_text=alt_text,
        )

    def _detect_figure_caption(self, line: str, figure_match: Tuple[int, str], line_num: int) -> FigureElement:
        """Detect a figure caption line (Figure 1: description)."""
        figure_number, caption = figure_match

        return FigureElement(
            type=ELEMENT_TYPES["IMAGE"],
            content=line,
            line_start=line_num,
            line_end=line_num,
            figure_number=figure_number,
            caption=caption,
            image_url="",
            alt_text=caption,
        )

    def _extract_code_language(self, fence_line: str) -> Optional[str]:
        """Extract language from code fence (```python)."""
        match = re.match(r'^```(\w+)?', fence_line.strip())
        if match:
            return match.group(1)
        return None

    def _detect_list(self, lines: List[str], start: int, list_type: str) -> tuple:
        """
        Detect a list (bullet or numbered) with structured items.

        Returns ListElement with parsed ListItem objects.
        """
        list_lines = []
        items = []
        i = start

        check_func = self._is_bullet_list if list_type == "bullet" else self._is_numbered_list
        item_func = is_bullet_item if list_type == "bullet" else is_numbered_item

        current_item = None
        current_content_lines = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                # Empty line might end list or be spacing
                if i + 1 < len(lines) and check_func(lines[i+1].strip()):
                    i += 1
                    continue
                break

            # Check if this is a new list item
            is_item, level, marker, content = item_func(line)

            if is_item:
                # Save previous item if exists
                if current_item:
                    if current_content_lines:
                        current_item.content += ' ' + ' '.join(current_content_lines)
                    items.append(current_item)

                # Start new item
                current_item = ListItem(
                    content=content,
                    marker=marker,
                    level=level,
                )
                current_content_lines = []
                list_lines.append(line)
                i += 1
            elif current_item and is_list_continuation(line, current_item.level):
                # Continuation of current item
                current_content_lines.append(stripped)
                list_lines.append(line)
                i += 1
            else:
                break

        # Save last item
        if current_item:
            if current_content_lines:
                current_item.content += ' ' + ' '.join(current_content_lines)
            items.append(current_item)

        if not items:
            return None, 1

        content = '\n'.join(list_lines)

        # Create ListElement with structured items
        element = ListElement(
            type=ELEMENT_TYPES["LIST_BULLET"] if list_type == "bullet" else ELEMENT_TYPES["LIST_NUMBERED"],
            content=content,
            line_start=start,
            line_end=i - 1,
            items=items,
            list_type=list_type,
        )

        return element, i - start

    def _detect_quote(self, lines: List[str], start: int) -> tuple:
        """Detect a blockquote (> prefix) and return BlockquoteElement."""
        quote_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith('>'):
                quote_lines.append(stripped[1:].strip())
                i += 1
            elif not stripped and quote_lines:
                # Empty line might continue quote
                if i + 1 < len(lines) and lines[i+1].strip().startswith('>'):
                    quote_lines.append('')
                    i += 1
                else:
                    break
            else:
                break

        if not quote_lines:
            return None, 1

        # Join quote content
        quote_text = '\n'.join(quote_lines)

        # Check for attribution in last line (— Author or - Author)
        attribution = ""
        citation = ""
        if quote_lines:
            last_line = quote_lines[-1]
            if last_line.startswith(('—', '–', '-')) and len(last_line) > 2:
                attribution = last_line[1:].strip()
                quote_text = '\n'.join(quote_lines[:-1])

        # Determine if multi-paragraph
        is_multi_paragraph = '\n\n' in quote_text or len(quote_lines) > 3

        content = '\n'.join(quote_lines)
        element = BlockquoteElement(
            type=ELEMENT_TYPES["QUOTE"],
            content=content,
            line_start=start,
            line_end=i - 1,
            quote_text=quote_text.strip(),
            attribution=attribution,
            citation=citation,
            is_multi_paragraph=is_multi_paragraph,
        )

        return element, i - start

    def _detect_table(self, lines: List[str], start: int) -> tuple:
        """
        Detect a table (markdown or ASCII) with structured data.

        Returns TableElement with parsed headers, rows, and alignments.
        """
        # Try markdown table detection first
        detected = detect_markdown_table(lines, start)

        # If not markdown, try ASCII table
        if not detected:
            detected = detect_ascii_table(lines, start)

        if not detected:
            return None, 1

        # Build content string
        content = '\n'.join(lines[detected.start_line:detected.end_line + 1])

        # Create TableElement with structured data
        element = TableElement(
            type=ELEMENT_TYPES["TABLE"],
            content=content,
            line_start=detected.start_line,
            line_end=detected.end_line,
            headers=detected.headers,
            rows=detected.rows,
            alignments=detected.alignments,
            table_type=detected.table_type,
            has_header=detected.has_header,
        )

        return element, detected.end_line - start + 1

    def _detect_paragraph(self, lines: List[str], start: int) -> tuple:
        """Detect a paragraph (consecutive non-empty lines)."""
        para_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                break

            # Stop if this line looks like a different element type
            if (self._is_bullet_list(stripped) or
                self._is_numbered_list(stripped) or
                stripped.startswith('>') or
                stripped.startswith('```') or
                ('|' in stripped and stripped.count('|') >= 2)):
                break

            para_lines.append(stripped)
            i += 1

        content = ' '.join(para_lines)
        element = DocumentElement(
            type=ELEMENT_TYPES["PARAGRAPH"],
            content=content,
            line_start=start,
            line_end=i - 1,
        )

        return element, max(1, i - start)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_detected_language(self) -> str:
        """Return the detected or configured language."""
        return self._detected_language or self.language

    def detect_headings(self, text: str) -> List[DocumentElement]:
        """
        Convenience method: detect only headings.

        Args:
            text: Raw text

        Returns:
            List of heading elements only
        """
        elements = self.detect(text)
        return [e for e in elements if e.type == ELEMENT_TYPES["HEADING"]]

    def get_outline(self, text: str) -> str:
        """
        Generate text outline from document.

        Args:
            text: Raw text

        Returns:
            Indented outline string
        """
        headings = self.detect_headings(text)

        lines = []
        for h in headings:
            indent = "  " * (h.level - 1)
            lines.append(f"{indent}H{h.level}: {h.content}")

        return '\n'.join(lines)

    def detect_lists(self, text: str) -> List[ListElement]:
        """
        Convenience method: detect only lists.

        Args:
            text: Raw text

        Returns:
            List of ListElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, ListElement)]

    def detect_tables(self, text: str) -> List[TableElement]:
        """
        Convenience method: detect only tables.

        Args:
            text: Raw text

        Returns:
            List of TableElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, TableElement)]

    def get_structure_summary(self, text: str) -> Dict[str, Any]:
        """
        Get a summary of document structure.

        Args:
            text: Raw text

        Returns:
            Dict with element counts and statistics
        """
        elements = self.detect(text)

        summary = {
            "total_elements": len(elements),
            "headings": 0,
            "paragraphs": 0,
            "lists": 0,
            "tables": 0,
            "code_blocks": 0,
            "quotes": 0,
            "images": 0,
            "horizontal_rules": 0,
            "list_items_total": 0,
            "table_rows_total": 0,
        }

        for e in elements:
            if e.type == ELEMENT_TYPES["HEADING"]:
                summary["headings"] += 1
            elif e.type == ELEMENT_TYPES["PARAGRAPH"]:
                summary["paragraphs"] += 1
            elif e.type in (ELEMENT_TYPES["LIST_BULLET"], ELEMENT_TYPES["LIST_NUMBERED"]):
                summary["lists"] += 1
                if isinstance(e, ListElement):
                    summary["list_items_total"] += len(e.items)
            elif e.type == ELEMENT_TYPES["TABLE"]:
                summary["tables"] += 1
                if isinstance(e, TableElement):
                    summary["table_rows_total"] += len(e.rows)
            elif e.type == ELEMENT_TYPES["CODE_BLOCK"]:
                summary["code_blocks"] += 1
            elif e.type == ELEMENT_TYPES["QUOTE"]:
                summary["quotes"] += 1
            elif e.type == ELEMENT_TYPES["IMAGE"]:
                summary["images"] += 1
            elif e.type == ELEMENT_TYPES["HORIZONTAL_RULE"]:
                summary["horizontal_rules"] += 1

        return summary

    def detect_code_blocks(self, text: str) -> List[CodeBlockElement]:
        """
        Convenience method: detect only code blocks.

        Args:
            text: Raw text

        Returns:
            List of CodeBlockElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, CodeBlockElement)]

    def detect_blockquotes(self, text: str) -> List[BlockquoteElement]:
        """
        Convenience method: detect only blockquotes.

        Args:
            text: Raw text

        Returns:
            List of BlockquoteElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, BlockquoteElement)]

    def detect_figures(self, text: str) -> List[FigureElement]:
        """
        Convenience method: detect only figures/images.

        Args:
            text: Raw text

        Returns:
            List of FigureElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, FigureElement)]

    def detect_horizontal_rules(self, text: str) -> List[HorizontalRuleElement]:
        """
        Convenience method: detect only horizontal rules.

        Args:
            text: Raw text

        Returns:
            List of HorizontalRuleElement objects
        """
        elements = self.detect(text)
        return [e for e in elements if isinstance(e, HorizontalRuleElement)]
