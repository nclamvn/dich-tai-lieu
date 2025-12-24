#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Element Patterns - Regex patterns for code blocks, quotes, footnotes, figures.

Coverage:
- Code blocks (fenced and indented)
- Block quotes with attribution
- Footnotes (references and definitions)
- Figures and image placeholders
- Horizontal rules
- Math equations (LaTeX)

STEM Integration Note:
----------------------
For enhanced code and formula detection, consider using the STEM integration
bridge at `core.formatting.utils.stem_integration`. The STEM module provides:

- Full-featured code detection with language inference
- LaTeX formula detection (display, inline, environments)
- Chemical formula detection (H2O, CO2, etc.)
- Placeholder-based protection during translation

Usage:
    from core.formatting.utils.stem_integration import get_stem_integration
    stem = get_stem_integration()
    if stem.is_available():
        results = stem.detect_all_stem_elements(text)

The patterns in this file serve as fallbacks when STEM is not available,
and are used by the StructureDetector for basic code/math detection.
"""

import re
from typing import Optional, List, Tuple, Dict


# =============================================================================
# CODE BLOCK PATTERNS
# =============================================================================

# Fenced code blocks (Markdown style)
# ```python
# code here
# ```
FENCED_CODE_START = r"^```(\w+)?$"
FENCED_CODE_END = r"^```$"

# Indented code blocks (4 spaces or 1 tab)
INDENTED_CODE_PATTERN = r"^(    |\t)(.+)$"

# Inline code: `code`
INLINE_CODE_PATTERN = r"`([^`]+)`"

# Language detection hints
CODE_LANGUAGE_HINTS: Dict[str, List[str]] = {
    "python": ["def ", "import ", "class ", "print(", "if __name__", "elif ", "self.", "async def"],
    "javascript": ["function ", "const ", "let ", "var ", "=>", "console.log", "require(", "export "],
    "typescript": ["interface ", "type ", ": string", ": number", ": boolean", "export interface"],
    "sql": ["SELECT ", "FROM ", "WHERE ", "INSERT ", "UPDATE ", "CREATE TABLE", "DROP ", "ALTER "],
    "bash": ["#!/bin/bash", "echo ", "cd ", "ls ", "grep ", "sudo ", "chmod ", "export "],
    "shell": ["$ ", "# ", "pwd", "mkdir ", "rm ", "cp ", "mv "],
    "html": ["<html", "<div", "<span", "<!DOCTYPE", "<head>", "<body>", "<script"],
    "css": ["color:", "margin:", "padding:", "display:", "font-size:", "background:"],
    "json": ['{"', '"}', '":', '[]', 'null', 'true', 'false'],
    "xml": ["<?xml", "<root", "/>", "</"],
    "java": ["public class", "public static void main", "System.out.println", "import java."],
    "c": ["#include", "int main(", "printf(", "scanf(", "void ", "struct "],
    "cpp": ["#include", "std::", "cout", "cin", "namespace ", "class ", "template<"],
    "go": ["package main", "func ", "import (", "fmt.", "go func"],
    "rust": ["fn main()", "let mut", "impl ", "pub fn", "use std::"],
    "ruby": ["def ", "end", "puts ", "require ", "class ", "attr_"],
    "php": ["<?php", "echo ", "function ", "$_", "->", "::"],
    "r": ["<-", "library(", "data.frame", "ggplot", "function("],
    "yaml": ["---", "  -", ": ", "key:", "value:"],
    "markdown": ["# ", "## ", "- ", "* ", "[](", "![]("],
}


# =============================================================================
# QUOTE/CITATION PATTERNS
# =============================================================================

# Markdown blockquote: > quote text
BLOCKQUOTE_PATTERN = r"^>\s*(.*)$"

# Multi-line blockquote (consecutive > lines)
BLOCKQUOTE_CONTINUATION = r"^>\s*(.*)$"

# Quoted text with attribution
# "Quote text" - Author Name
# "Quote text" — Author Name
QUOTE_WITH_ATTRIBUTION = r'^["""](.+?)["""][\s]*[-–—]\s*(.+)$'

# Quoted text with citation
# "Quote text" (Author, Year)
QUOTE_WITH_CITATION = r'^["""](.+?)["""][\s]*\((.+?)\)$'

# Vietnamese quote marks
QUOTE_MARKS_VI = r'^[""«»](.+?)[""«»]'

# Academic citation patterns
# (Author, Year)
# (Author et al., Year)
# [1], [2], [1-3]
CITATION_PATTERNS = [
    r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-z]+)*),?\s*(\d{4})\)',
    r'\[(\d+(?:[-,]\d+)*)\]',
]


# =============================================================================
# FOOTNOTE PATTERNS
# =============================================================================

# Markdown footnote reference: [^1]
FOOTNOTE_REF_PATTERN = r"\[\^(\d+|[\w-]+)\]"

# Footnote definition: [^1]: Footnote text
FOOTNOTE_DEF_PATTERN = r"^\[\^(\d+|[\w-]+)\]:\s*(.+)$"

# Superscript number in text: text¹ or text(1)
SUPERSCRIPT_REF = r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+|\(\d+\)|\[\d+\]"

# Endnote patterns
ENDNOTE_SECTION_HEADERS = [
    r"^Notes?:?\s*$",
    r"^Footnotes?:?\s*$",
    r"^Endnotes?:?\s*$",
    r"^References?:?\s*$",
    r"^Ghi chú:?\s*$",      # Vietnamese
    r"^Chú thích:?\s*$",    # Vietnamese
]


# =============================================================================
# IMAGE/FIGURE PATTERNS
# =============================================================================

# Markdown image: ![alt](url)
MARKDOWN_IMAGE = r"!\[([^\]]*)\]\(([^)]+)\)"

# Figure reference: Figure 1, Fig. 1, Hình 1
FIGURE_REF_PATTERN = r"^(Figure|Fig\.|Hình|Ảnh)\s*(\d+)\.?\s*:?\s*(.*)$"

# Image placeholder in text
IMAGE_PLACEHOLDER = r"\[IMAGE:?\s*([^\]]*)\]|\[FIGURE:?\s*([^\]]*)\]|\[HÌNH:?\s*([^\]]*)\]"

# Common image file extensions
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"]


# =============================================================================
# HORIZONTAL RULE PATTERNS
# =============================================================================

HORIZONTAL_RULE_PATTERNS = [
    r"^[-]{3,}$",              # ---
    r"^[_]{3,}$",              # ___
    r"^[*]{3,}$",              # ***
    r"^[-]\s+[-]\s+[-]",       # - - -
    r"^[*]\s+[*]\s+[*]",       # * * *
    r"^[_]\s+[_]\s+[_]",       # _ _ _
]


# =============================================================================
# MATH/EQUATION PATTERNS
# =============================================================================

# LaTeX inline: $equation$
LATEX_INLINE = r"\$([^$]+)\$"

# LaTeX display: $$equation$$
LATEX_DISPLAY = r"\$\$([^$]+)\$\$"

# Plain text equation indicators
EQUATION_INDICATORS = [
    r"[=<>≤≥≠±×÷∑∫∏√∞αβγδεζηθικλμνξπρστυφχψω]",  # Math symbols
    r"\b(sin|cos|tan|log|ln|exp|lim|max|min|sup|inf)\b",  # Math functions
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def detect_code_language(code: str) -> str:
    """
    Auto-detect programming language from code content.

    Args:
        code: Code block content

    Returns:
        Language name or empty string if unknown
    """
    code_lower = code.lower()

    # Count matches for each language
    scores = {}
    for lang, hints in CODE_LANGUAGE_HINTS.items():
        score = sum(1 for hint in hints if hint.lower() in code_lower)
        if score > 0:
            scores[lang] = score

    if not scores:
        return ""

    # Return language with highest score
    return max(scores.items(), key=lambda x: x[1])[0]


def is_fenced_code_start(line: str) -> Tuple[bool, str]:
    """
    Check if line starts a fenced code block.

    Args:
        line: Line to check

    Returns:
        Tuple of (is_start, language)
    """
    match = re.match(FENCED_CODE_START, line.strip())
    if match:
        lang = match.group(1) or ""
        return True, lang
    return False, ""


def is_fenced_code_end(line: str) -> bool:
    """Check if line ends a fenced code block."""
    return bool(re.match(FENCED_CODE_END, line.strip()))


def is_indented_code(line: str) -> Tuple[bool, str]:
    """
    Check if line is indented code (4 spaces or tab).

    Args:
        line: Line to check

    Returns:
        Tuple of (is_code, code_content)
    """
    match = re.match(INDENTED_CODE_PATTERN, line)
    if match:
        return True, match.group(2)
    return False, ""


def is_blockquote_line(line: str) -> Tuple[bool, str]:
    """
    Check if line is a blockquote.

    Args:
        line: Line to check

    Returns:
        Tuple of (is_quote, quote_content)
    """
    match = re.match(BLOCKQUOTE_PATTERN, line)
    if match:
        return True, match.group(1)
    return False, ""


def extract_quote_attribution(text: str) -> Tuple[str, str, str]:
    """
    Extract quote, attribution, and citation from quoted text.

    Args:
        text: Full quote text

    Returns:
        Tuple of (quote_text, attribution, citation)
    """
    # Try attribution pattern first: "quote" - Author
    match = re.match(QUOTE_WITH_ATTRIBUTION, text)
    if match:
        return match.group(1), match.group(2), ""

    # Try citation pattern: "quote" (Author, Year)
    match = re.match(QUOTE_WITH_CITATION, text)
    if match:
        return match.group(1), "", match.group(2)

    return text, "", ""


def is_horizontal_rule(line: str) -> bool:
    """Check if line is a horizontal rule."""
    line = line.strip()
    for pattern in HORIZONTAL_RULE_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def find_footnote_refs(text: str) -> List[Tuple[str, int]]:
    """
    Find all footnote references in text.

    Args:
        text: Text to search

    Returns:
        List of (marker, position) tuples
    """
    refs = []
    for match in re.finditer(FOOTNOTE_REF_PATTERN, text):
        refs.append((match.group(1), match.start()))
    return refs


def find_footnote_defs(lines: List[str]) -> List[Tuple[str, str, int]]:
    """
    Find all footnote definitions.

    Args:
        lines: Lines to search

    Returns:
        List of (marker, text, line_index) tuples
    """
    defs = []
    for i, line in enumerate(lines):
        match = re.match(FOOTNOTE_DEF_PATTERN, line)
        if match:
            defs.append((match.group(1), match.group(2), i))
    return defs


def parse_markdown_image(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse markdown image syntax.

    Args:
        line: Line to parse

    Returns:
        Tuple of (alt_text, url) or None
    """
    match = re.search(MARKDOWN_IMAGE, line)
    if match:
        return match.group(1), match.group(2)
    return None


def parse_figure_caption(line: str) -> Optional[Tuple[int, str]]:
    """
    Parse figure caption line.

    Args:
        line: Line to parse

    Returns:
        Tuple of (figure_number, caption) or None
    """
    match = re.match(FIGURE_REF_PATTERN, line, re.IGNORECASE)
    if match:
        try:
            num = int(match.group(2))
            caption = match.group(3) or ""
            return num, caption.strip()
        except ValueError:
            pass
    return None


def has_math_content(text: str) -> bool:
    """Check if text contains mathematical content."""
    # Check for LaTeX
    if re.search(LATEX_INLINE, text) or re.search(LATEX_DISPLAY, text):
        return True

    # Check for math indicators
    for pattern in EQUATION_INDICATORS:
        if re.search(pattern, text):
            return True

    return False


def extract_latex_equations(text: str) -> List[Tuple[str, bool]]:
    """
    Extract LaTeX equations from text.

    Args:
        text: Text to search

    Returns:
        List of (equation, is_display) tuples
    """
    equations = []

    # Display equations first ($$...$$)
    for match in re.finditer(LATEX_DISPLAY, text):
        equations.append((match.group(1), True))

    # Remove display equations before searching inline
    text_no_display = re.sub(LATEX_DISPLAY, '', text)

    # Inline equations ($...$)
    for match in re.finditer(LATEX_INLINE, text_no_display):
        equations.append((match.group(1), False))

    return equations
