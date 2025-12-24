#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heading Detection Patterns - Regex patterns for EN + VI headings.

Coverage:
- English: Chapter, Part, Section, Article, etc.
- Vietnamese: Chương, Phần, Mục, Điều, Bài, etc.
- Numbered: 1., 1.1, 1.1.1, I., II., etc.
- Heuristic patterns for edge cases
"""

import re
from typing import Optional, List, Tuple


# =============================================================================
# H1 PATTERNS - CHAPTER LEVEL (English)
# =============================================================================

H1_PATTERNS_EN = [
    # Markdown-style H1 (# Title)
    r'^#\s+(.+)$',

    # Chapter variations
    r'^(CHAPTER|Chapter)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',
    r'^(CHAPTER|Chapter)\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve)(\s*[:：\-–—]\s*.*)?$',

    # Part variations
    r'^(PART|Part)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',
    r'^(PART|Part)\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(\s*[:：\-–—]\s*.*)?$',

    # Book variations
    r'^(BOOK|Book)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',

    # Common document sections
    r'^(PROLOGUE|Prologue|EPILOGUE|Epilogue)$',
    r'^(INTRODUCTION|Introduction|CONCLUSION|Conclusion)$',
    r'^(PREFACE|Preface|FOREWORD|Foreword)$',
    r'^(APPENDIX|Appendix)\s*([A-Z]|\d+)?(\s*[:：\-–—]\s*.*)?$',
    r'^(ACKNOWLEDGEMENTS?|Acknowledgements?|DEDICATION|Dedication)$',
    r'^(BIBLIOGRAPHY|Bibliography|REFERENCES|References)$',
    r'^(GLOSSARY|Glossary|INDEX|Index)$',
    r'^(ABSTRACT|Abstract|SUMMARY|Summary)$',

    # Standalone numbers as chapter markers
    r'^(\d{1,3})$',  # Single number: 1, 2, 10, etc.
    r'^([IVXLCDM]+)$',  # Roman numerals: I, II, III, IV, V, etc.
]


# =============================================================================
# H1 PATTERNS - CHAPTER LEVEL (Vietnamese)
# =============================================================================

H1_PATTERNS_VI = [
    # Chương variations
    r'^(CHƯƠNG|Chương)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',
    r'^(CHƯƠNG|Chương)\s+(Một|Hai|Ba|Bốn|Năm|Sáu|Bảy|Tám|Chín|Mười)(\s*[:：\-–—]\s*.*)?$',

    # Phần variations
    r'^(PHẦN|Phần)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',
    r'^(PHẦN|Phần)\s+(Một|Hai|Ba|Bốn|Năm|Sáu|Bảy|Tám|Chín|Mười)(\s*[:：\-–—]\s*.*)?$',

    # Quyển (Book/Volume)
    r'^(QUYỂN|Quyển|TẬP|Tập)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',

    # Common document sections
    r'^(LỜI MỞ ĐẦU|Lời mở đầu|LỜI NÓI ĐẦU|Lời nói đầu)$',
    r'^(LỜI KẾT|Lời kết|KẾT LUẬN|Kết luận)$',
    r'^(LỜI TỰA|Lời tựa|LỜI GIỚI THIỆU|Lời giới thiệu)$',
    r'^(PHỤ LỤC|Phụ lục)\s*([A-Z]|\d+)?(\s*[:：\-–—]\s*.*)?$',
    r'^(LỜI CẢM ƠN|Lời cảm ơn)$',
    r'^(TÀI LIỆU THAM KHẢO|Tài liệu tham khảo)$',
    r'^(MỤC LỤC|Mục lục|DANH MỤC|Danh mục)$',
    r'^(TÓM TẮT|Tóm tắt)$',
]


# =============================================================================
# H2 PATTERNS - SECTION LEVEL (English)
# =============================================================================

H2_PATTERNS_EN = [
    # Markdown-style H2 (## Title)
    r'^##\s+(.+)$',

    # Section variations
    r'^(SECTION|Section)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',
    r'^(SECTION|Section)\s+(\d+\.\d+)(\s*[:：\-–—]\s*.*)?$',

    # Article variations (legal/academic)
    r'^(ARTICLE|Article)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',

    # Roman numeral sections
    r'^([IVXLCDM]+)\.\s+(.+)$',  # I. Title, II. Title

    # Numbered sections (single level)
    r'^(\d+)\.\s+([A-Z][^.]*?)$',  # 1. Title (capital start, no period at end)

    # Lettered sections
    r'^([A-Z])\.\s+(.+)$',  # A. Title, B. Title
]


# =============================================================================
# H2 PATTERNS - SECTION LEVEL (Vietnamese)
# =============================================================================

H2_PATTERNS_VI = [
    # Mục variations
    r'^(MỤC|Mục)\s+(\d+|[IVXLCDM]+)(\s*[:：\-–—]\s*.*)?$',

    # Điều (Article - legal)
    r'^(ĐIỀU|Điều)\s+(\d+)(\s*[:：\-–—\.]?\s*.*)?$',

    # Bài (Lesson/Article)
    r'^(BÀI|Bài)\s+(\d+)(\s*[:：\-–—]\s*.*)?$',

    # Tiết (Section in legal documents)
    r'^(TIẾT|Tiết)\s+(\d+)(\s*[:：\-–—]\s*.*)?$',

    # Numbered Vietnamese sections
    r'^(\d+)\.\s+([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][^.]*?)$',
]


# =============================================================================
# H3 PATTERNS - SUBSECTION LEVEL (English)
# =============================================================================

H3_PATTERNS_EN = [
    # Markdown-style H3 (### Title)
    r'^###\s+(.+)$',

    # Numbered subsections (two levels)
    r'^(\d+\.\d+)\s+(.+)$',  # 1.1 Title, 2.3 Title

    # Lettered subsections under numbers
    r'^(\d+)([a-z])\.\s+(.+)$',  # 1a. Title
    r'^\(([a-z])\)\s+(.+)$',  # (a) Title
    r'^\((\d+)\)\s+(.+)$',  # (1) Title

    # Lower roman numerals
    r'^([ivx]+)\.\s+(.+)$',  # i. Title, ii. Title
]


# =============================================================================
# H3 PATTERNS - SUBSECTION LEVEL (Vietnamese)
# =============================================================================

H3_PATTERNS_VI = [
    # Numbered Vietnamese subsections
    r'^(\d+\.\d+)\s+(.+)$',  # 1.1 Title
    r'^(\d+\.\d+)\.\s+(.+)$',  # 1.1. Title

    # Khoản (Clause - legal)
    r'^(Khoản|KHOẢN)\s+(\d+)(\s*[:：\-–—\.]?\s*.*)?$',

    # Điểm (Point - legal)
    r'^(Điểm|ĐIỂM)\s+([a-zđ])(\s*[:：\-–—\.]?\s*.*)?$',

    # Lettered subsections
    r'^([a-zđ])\)\s+(.+)$',  # a) Title
]


# =============================================================================
# H4 PATTERNS - SUB-SUBSECTION LEVEL
# =============================================================================

H4_PATTERNS = [
    # Markdown-style H4 (#### Title)
    r'^####\s+(.+)$',

    # Three-level numbering
    r'^(\d+\.\d+\.\d+)\s+(.+)$',  # 1.1.1 Title
    r'^(\d+\.\d+\.\d+)\.\s+(.+)$',  # 1.1.1. Title

    # Four-level numbering
    r'^(\d+\.\d+\.\d+\.\d+)\s+(.+)$',  # 1.1.1.1 Title

    # Deeply nested letters
    r'^\(([ivx]+)\)\s+(.+)$',  # (i) Title, (ii) Title
    r'^([a-z]{2})\)\s+(.+)$',  # aa) Title, ab) Title
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def match_heading_pattern(text: str, patterns: List[str]) -> Optional[re.Match]:
    """
    Check if text matches any pattern in the list.

    Args:
        text: Line of text to check
        patterns: List of regex patterns

    Returns:
        Match object if found, None otherwise
    """
    text = text.strip()
    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return match
    return None


def get_heading_level(text: str, language: str = "auto") -> Optional[int]:
    """
    Determine heading level (1-4) from text.

    Args:
        text: Line of text to analyze
        language: "en", "vi", or "auto"

    Returns:
        Heading level (1-4) or None if not a heading
    """
    text = text.strip()

    if not text:
        return None

    # Determine which pattern sets to use
    if language == "auto":
        # Try both English and Vietnamese
        h1_patterns = H1_PATTERNS_EN + H1_PATTERNS_VI
        h2_patterns = H2_PATTERNS_EN + H2_PATTERNS_VI
        h3_patterns = H3_PATTERNS_EN + H3_PATTERNS_VI
    elif language == "vi":
        h1_patterns = H1_PATTERNS_VI + H1_PATTERNS_EN  # VI first
        h2_patterns = H2_PATTERNS_VI + H2_PATTERNS_EN
        h3_patterns = H3_PATTERNS_VI + H3_PATTERNS_EN
    else:  # "en"
        h1_patterns = H1_PATTERNS_EN + H1_PATTERNS_VI
        h2_patterns = H2_PATTERNS_EN + H2_PATTERNS_VI
        h3_patterns = H3_PATTERNS_EN + H3_PATTERNS_VI

    # Check H1 first (most specific)
    if match_heading_pattern(text, h1_patterns):
        return 1

    # Check H2
    if match_heading_pattern(text, h2_patterns):
        return 2

    # Check H3
    if match_heading_pattern(text, h3_patterns):
        return 3

    # Check H4
    if match_heading_pattern(text, H4_PATTERNS):
        return 4

    return None


def is_likely_heading_heuristic(
    text: str,
    prev_line: Optional[str] = None,
    next_line: Optional[str] = None,
    max_chars: int = 100
) -> Tuple[bool, Optional[int]]:
    """
    Apply heuristic rules to detect potential headings.

    Heuristics:
    1. Short line (<100 chars) without ending punctuation
    2. All caps line with few words
    3. Line after blank line and before paragraph
    4. Starts with number but not a numbered list item

    Args:
        text: Line to analyze
        prev_line: Previous line (or None)
        next_line: Next line (or None)
        max_chars: Maximum characters for potential heading

    Returns:
        Tuple of (is_heading, suggested_level)
    """
    text = text.strip()

    if not text:
        return False, None

    # Too long to be a heading
    if len(text) > max_chars:
        return False, None

    # Ends with sentence punctuation - likely not a heading
    if text.endswith(('.', '?', '!', ',', ';', ':')):
        # Exception: colons can end headings like "Chapter 1:"
        if not text.endswith(':'):
            return False, None

    # Check for all caps (strong indicator of H1/H2)
    words = text.split()
    if text.isupper() and len(words) <= 10:
        # All caps, short - likely H1 or H2
        if len(words) <= 5:
            return True, 1
        return True, 2

    # Short line after blank, before long paragraph
    is_after_blank = prev_line is not None and prev_line.strip() == ""
    is_before_para = next_line is not None and len(next_line.strip()) > 100

    if is_after_blank and is_before_para and len(text) < 80:
        # Likely a heading
        if text[0].isupper():
            return True, 2  # Default to H2 for heuristic matches

    # Starts with capital, short, no ending punctuation
    if (text[0].isupper() and
        len(text) < 60 and
        len(words) <= 8 and
        not any(text.endswith(p) for p in '.?!,;')):
        return True, 3  # Default to H3

    return False, None


def detect_language(text: str) -> str:
    """
    Detect if text is primarily Vietnamese or English.

    Args:
        text: Text to analyze

    Returns:
        "vi" for Vietnamese, "en" for English
    """
    # Vietnamese-specific characters (lowercase)
    vi_lower = 'àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ'
    # Vietnamese-specific characters (uppercase)
    vi_upper = 'ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ'
    vi_chars = set(vi_lower + vi_upper)

    text_lower = text.lower()
    vi_count = sum(1 for c in text if c in vi_chars)

    # If more than 1% Vietnamese characters, it's Vietnamese
    if len(text) > 0 and vi_count / len(text) > 0.01:
        return "vi"

    # Check for Vietnamese keywords
    vi_keywords = ['chương', 'phần', 'mục', 'điều', 'và', 'của', 'trong', 'là', 'được']
    for kw in vi_keywords:
        if kw in text_lower:
            return "vi"

    return "en"
