"""
Internationalization (i18n) for renderer UI strings.

Simple dict-based localization for document rendering labels
(Chapter, TOC, Glossary, etc.). Supports vi, en, ja, fr with English fallback.

Usage:
    from core.i18n import get_string, format_chapter_title
    label = get_string("chapter", "vi")  # "Chương"
    title = format_chapter_title(3, "Introduction", "en")  # "Chapter 3: Introduction"
"""

from typing import Optional

# String tables keyed by (string_id, language_code)
STRINGS = {
    "chapter": {
        "en": "Chapter",
        "vi": "Chương",
        "ja": "第",
        "fr": "Chapitre",
    },
    "table_of_contents": {
        "en": "Table of Contents",
        "vi": "Mục lục",
        "ja": "目次",
        "fr": "Table des matières",
    },
    "glossary": {
        "en": "Glossary",
        "vi": "Thuật ngữ",
        "ja": "用語集",
        "fr": "Glossaire",
    },
    "references": {
        "en": "References",
        "vi": "Tài liệu tham khảo",
        "ja": "参考文献",
        "fr": "Références",
    },
    "translator": {
        "en": "Translator",
        "vi": "Dịch giả",
        "ja": "翻訳者",
        "fr": "Traducteur",
    },
    "page": {
        "en": "Page",
        "vi": "Trang",
        "ja": "ページ",
        "fr": "Page",
    },
}


def get_string(string_id: str, lang: str = "en") -> str:
    """
    Get a localized string by ID and language code.

    Falls back to English if the language is not found,
    then to the string_id itself if no translation exists.
    """
    table = STRINGS.get(string_id)
    if not table:
        return string_id
    return table.get(lang, table.get("en", string_id))


def format_chapter_title(
    number: Optional[int],
    title: str = "",
    lang: str = "en",
) -> str:
    """
    Format a chapter title with localized prefix.

    Examples:
        format_chapter_title(3, "Intro", "en") -> "Chapter 3: Intro"
        format_chapter_title(3, "Giới thiệu", "vi") -> "Chương 3: Giới thiệu"
        format_chapter_title(3, "導入", "ja") -> "第3章: 導入"
        format_chapter_title(None, "Intro", "en") -> "Intro"
    """
    if number is None:
        return title

    chapter_word = get_string("chapter", lang)

    if lang == "ja":
        prefix = f"{chapter_word}{number}章"
    else:
        prefix = f"{chapter_word} {number}"

    if title:
        return f"{prefix}: {title}"
    return prefix
