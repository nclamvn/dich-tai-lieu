"""Tests for core.i18n localization module."""

import pytest
from core.i18n import get_string, format_chapter_title, STRINGS


class TestGetString:
    """Tests for get_string()."""

    def test_english_strings(self):
        assert get_string("chapter", "en") == "Chapter"
        assert get_string("table_of_contents", "en") == "Table of Contents"
        assert get_string("glossary", "en") == "Glossary"
        assert get_string("references", "en") == "References"
        assert get_string("translator", "en") == "Translator"
        assert get_string("page", "en") == "Page"

    def test_vietnamese_strings(self):
        assert get_string("chapter", "vi") == "Chương"
        assert get_string("table_of_contents", "vi") == "Mục lục"
        assert get_string("glossary", "vi") == "Thuật ngữ"
        assert get_string("references", "vi") == "Tài liệu tham khảo"
        assert get_string("translator", "vi") == "Dịch giả"
        assert get_string("page", "vi") == "Trang"

    def test_japanese_strings(self):
        assert get_string("chapter", "ja") == "第"
        assert get_string("table_of_contents", "ja") == "目次"
        assert get_string("glossary", "ja") == "用語集"

    def test_french_strings(self):
        assert get_string("chapter", "fr") == "Chapitre"
        assert get_string("table_of_contents", "fr") == "Table des matières"

    def test_fallback_to_english(self):
        """Unknown language falls back to English."""
        assert get_string("chapter", "de") == "Chapter"
        assert get_string("glossary", "ko") == "Glossary"

    def test_unknown_string_id(self):
        """Unknown string_id returns the id itself."""
        assert get_string("nonexistent_key", "en") == "nonexistent_key"

    def test_default_language_is_english(self):
        """No language parameter defaults to English."""
        assert get_string("chapter") == "Chapter"
        assert get_string("glossary") == "Glossary"


class TestFormatChapterTitle:
    """Tests for format_chapter_title()."""

    def test_english_with_title(self):
        assert format_chapter_title(3, "Introduction", "en") == "Chapter 3: Introduction"

    def test_english_without_title(self):
        assert format_chapter_title(5, "", "en") == "Chapter 5"

    def test_vietnamese(self):
        result = format_chapter_title(1, "Giới thiệu", "vi")
        assert result == "Chương 1: Giới thiệu"

    def test_japanese(self):
        result = format_chapter_title(2, "導入", "ja")
        assert result == "第2章: 導入"

    def test_french(self):
        result = format_chapter_title(4, "Introduction", "fr")
        assert result == "Chapitre 4: Introduction"

    def test_none_number_returns_title_only(self):
        assert format_chapter_title(None, "Intro", "en") == "Intro"

    def test_default_language(self):
        assert format_chapter_title(1, "Test") == "Chapter 1: Test"


class TestStringCoverage:
    """Verify all string IDs have at least en and vi translations."""

    def test_all_strings_have_english(self):
        for string_id, table in STRINGS.items():
            assert "en" in table, f"Missing English for '{string_id}'"

    def test_all_strings_have_vietnamese(self):
        for string_id, table in STRINGS.items():
            assert "vi" in table, f"Missing Vietnamese for '{string_id}'"
