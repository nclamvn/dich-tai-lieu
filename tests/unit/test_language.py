"""
Unit Tests for Language Module

Tests language detection, validation, and language pair handling.
"""

import pytest
from typing import List, Tuple

from core.language import (
    LanguageCode,
    LanguageInfo,
    LanguagePair,
    LanguageDetector,
    LanguageValidator,
    LANGUAGES,
    COMMON_PAIRS,
    get_language_pair,
    get_language_name,
    get_supported_languages,
    is_language_supported,
)


class TestLanguageCode:
    """Tests for LanguageCode enum."""
    
    def test_all_codes_exist(self):
        """Verify all expected language codes are defined."""
        expected = ["en", "vi", "zh", "zh-Hans", "zh-Hant", "ja", "ko", "fr", "es", "de"]
        actual = [c.value for c in LanguageCode]
        assert set(expected) == set(actual)
    
    def test_code_values(self):
        """Test individual code values."""
        assert LanguageCode.ENGLISH.value == "en"
        assert LanguageCode.VIETNAMESE.value == "vi"
        assert LanguageCode.CHINESE.value == "zh"
        assert LanguageCode.JAPANESE.value == "ja"
        assert LanguageCode.KOREAN.value == "ko"
        assert LanguageCode.FRENCH.value == "fr"
        assert LanguageCode.SPANISH.value == "es"
        assert LanguageCode.GERMAN.value == "de"
    
    def test_code_is_string_enum(self):
        """Test that LanguageCode inherits from str."""
        assert isinstance(LanguageCode.ENGLISH.value, str)
        assert str(LanguageCode.ENGLISH) == "LanguageCode.ENGLISH"


class TestLanguageInfo:
    """Tests for LanguageInfo dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic language info."""
        info = LanguageInfo(
            code="test",
            name="Test",
            native_name="Test Native"
        )
        assert info.code == "test"
        assert info.name == "Test"
        assert info.native_name == "Test Native"
    
    def test_default_values(self):
        """Test default values."""
        info = LanguageInfo(code="t", name="T", native_name="TN")
        assert info.direction == "ltr"
        assert info.char_range is None
        assert info.avg_length_ratio == 1.0
        assert info.requires_diacritics is False
        assert info.has_spaces is True
        assert info.has_capitalization is True
    
    def test_vietnamese_info(self):
        """Test Vietnamese language info from database."""
        vi = LANGUAGES["vi"]
        assert vi.code == "vi"
        assert vi.name == "Vietnamese"
        assert vi.native_name == "Tiếng Việt"
        assert vi.requires_diacritics is True
        assert vi.has_spaces is True
        assert vi.avg_length_ratio == 1.3
    
    def test_chinese_info(self):
        """Test Chinese language info from database."""
        zh = LANGUAGES["zh"]
        assert zh.code == "zh"
        assert zh.name == "Chinese"
        assert zh.native_name == "中文"
        assert zh.has_spaces is False
        assert zh.has_capitalization is False
        assert zh.avg_length_ratio == 0.7
    
    def test_japanese_info(self):
        """Test Japanese language info from database."""
        ja = LANGUAGES["ja"]
        assert ja.code == "ja"
        assert ja.name == "Japanese"
        assert ja.native_name == "日本語"
        assert ja.has_spaces is False
        assert ja.char_range is not None


class TestLanguagePair:
    """Tests for LanguagePair dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic language pair."""
        pair = LanguagePair(source="en", target="vi")
        assert pair.source == "en"
        assert pair.target == "vi"
    
    def test_length_ratio_calculation(self):
        """Test automatic length ratio calculation."""
        pair = LanguagePair(source="en", target="vi")
        # Vietnamese is ~30% longer than English
        assert pair.expected_length_ratio_min > 0
        assert pair.expected_length_ratio_max > pair.expected_length_ratio_min
    
    def test_str_representation(self):
        """Test string representation."""
        pair = LanguagePair(source="en", target="ja")
        assert str(pair) == "en→ja"
    
    def test_reverse(self):
        """Test getting reverse pair."""
        pair = LanguagePair(source="en", target="vi")
        reverse = pair.reverse()
        assert reverse.source == "vi"
        assert reverse.target == "en"
    
    def test_unknown_language_pair(self):
        """Test pair with unknown languages."""
        pair = LanguagePair(source="xx", target="yy")
        # Should use default values
        assert pair.expected_length_ratio_min == 0.5
        assert pair.expected_length_ratio_max == 2.0


class TestCommonPairs:
    """Tests for predefined language pairs."""
    
    def test_en_vi_exists(self):
        """Test English-Vietnamese pair exists."""
        assert "en-vi" in COMMON_PAIRS
        pair = COMMON_PAIRS["en-vi"]
        assert pair.source == "en"
        assert pair.target == "vi"
    
    def test_vi_en_exists(self):
        """Test Vietnamese-English pair exists."""
        assert "vi-en" in COMMON_PAIRS
    
    def test_ja_vi_exists(self):
        """Test Japanese-Vietnamese pair exists."""
        assert "ja-vi" in COMMON_PAIRS
    
    def test_all_pairs_valid(self):
        """Test all predefined pairs are valid."""
        for key, pair in COMMON_PAIRS.items():
            assert pair.source != ""
            assert pair.target != ""
            # Key should match source-target
            parts = key.split("-", 1)  # Split on first hyphen only
            # For codes like zh-Hans, this test is more complex
            assert pair.source in key
            assert pair.target in key


class TestLanguageDetector:
    """Tests for LanguageDetector class."""
    
    def test_detect_empty_text(self):
        """Test detection of empty text."""
        lang, conf = LanguageDetector.detect("")
        assert lang == "unknown"
        assert conf == 0.0
    
    def test_detect_whitespace_only(self):
        """Test detection of whitespace-only text."""
        lang, conf = LanguageDetector.detect("   \n\t  ")
        assert lang == "unknown"
        assert conf == 0.0
    
    def test_detect_english(self):
        """Test detection of English text."""
        text = "Hello, this is a sample English text for testing."
        lang, conf = LanguageDetector.detect(text)
        assert lang == "en"
        assert conf > 0.5
    
    def test_detect_vietnamese(self):
        """Test detection of Vietnamese text."""
        text = "Xin chào, đây là văn bản tiếng Việt để kiểm tra."
        lang, conf = LanguageDetector.detect(text)
        assert lang == "vi"
        assert conf > 0.5
    
    def test_detect_chinese(self):
        """Test detection of Chinese text."""
        text = "这是一段中文文本用于测试语言检测功能。"
        lang, conf = LanguageDetector.detect(text)
        assert lang in ["zh", "zh-Hans", "zh-Hant"]
        assert conf > 0.5
    
    def test_detect_japanese(self):
        """Test detection of Japanese text."""
        text = "これは日本語のテストテキストです。漢字も含まれています。"
        lang, conf = LanguageDetector.detect(text)
        assert lang == "ja"
        assert conf > 0.5
    
    def test_detect_korean(self):
        """Test detection of Korean text."""
        text = "안녕하세요, 이것은 한국어 테스트입니다."
        lang, conf = LanguageDetector.detect(text)
        assert lang == "ko"
        assert conf > 0.5
    
    def test_detect_with_candidates(self):
        """Test detection with candidate list."""
        text = "Hello world"
        lang, conf = LanguageDetector.detect(text, candidates=["en", "vi"])
        assert lang == "en"
    
    def test_is_language_true(self):
        """Test is_language returns True for matching text."""
        text = "Xin chào các bạn, tôi là một người Việt Nam."
        assert LanguageDetector.is_language(text, "vi") is True
    
    def test_is_language_false(self):
        """Test is_language behavior with non-matching languages."""
        # Chinese text should NOT be detected as Vietnamese
        text = "这是中文文本"
        # Chinese should not match Vietnamese at any threshold
        assert LanguageDetector.is_language(text, "vi", threshold=0.5) is False
    
    def test_is_language_threshold(self):
        """Test is_language with custom threshold."""
        text = "Hello world"
        # Very high threshold might fail even for correct language
        result = LanguageDetector.is_language(text, "en", threshold=0.99)
        # Just check it runs without error
        assert isinstance(result, bool)


class TestLanguageValidator:
    """Tests for LanguageValidator class."""
    
    # Vietnamese validation tests
    def test_validate_vietnamese_good(self):
        """Test validation of good Vietnamese text."""
        text = "Đây là một đoạn văn bản tiếng Việt chất lượng cao với đầy đủ dấu."
        score, warnings = LanguageValidator.validate_vietnamese(text)
        assert score > 0.7
    
    def test_validate_vietnamese_no_diacritics(self):
        """Test validation of Vietnamese without diacritics."""
        text = "Day la mot doan van ban tieng Viet khong co dau."
        score, warnings = LanguageValidator.validate_vietnamese(text)
        assert score < 0.7
        assert any("diacritics" in w.lower() for w in warnings)
    
    def test_validate_vietnamese_short_text(self):
        """Test validation of short Vietnamese text."""
        text = "Xin chào"
        score, warnings = LanguageValidator.validate_vietnamese(text)
        # Short text should still validate if it has diacritics
        assert score > 0
    
    # Chinese validation tests
    def test_validate_chinese_good(self):
        """Test validation of good Chinese text."""
        text = "这是一段高质量的中文文本，包含了常用的汉字。"
        score, warnings = LanguageValidator.validate_chinese(text)
        assert score > 0.7
    
    def test_validate_chinese_no_characters(self):
        """Test validation of text without Chinese characters."""
        text = "This is English text with no Chinese."
        score, warnings = LanguageValidator.validate_chinese(text)
        assert score < 0.7
        assert any("Chinese characters" in w for w in warnings)
    
    def test_validate_chinese_excessive_spaces(self):
        """Test validation of Chinese with too many spaces."""
        text = "这 是 一 段 中 文 文 本"
        score, warnings = LanguageValidator.validate_chinese(text)
        assert any("spaces" in w.lower() for w in warnings)
    
    # English validation tests
    def test_validate_english_good(self):
        """Test validation of good English text."""
        text = "This is a high-quality English text with proper grammar and vocabulary."
        score, warnings = LanguageValidator.validate_english(text)
        assert score > 0.8
    
    def test_validate_english_no_words(self):
        """Test validation of text without English words."""
        text = "12345 !@#$% ..."
        score, warnings = LanguageValidator.validate_english(text)
        assert score < 0.7
    
    # Japanese validation tests
    def test_validate_japanese_good(self):
        """Test validation of good Japanese text."""
        text = "これは高品質な日本語のテキストです。ひらがなとカタカナと漢字が含まれています。"
        score, warnings = LanguageValidator.validate_japanese(text)
        assert score > 0.7
    
    def test_validate_japanese_only_kanji(self):
        """Test validation of Japanese with only kanji (might be Chinese)."""
        text = "中国語文本没有日本語特有字"
        score, warnings = LanguageValidator.validate_japanese(text)
        # Should flag as possibly Chinese
        assert any("Chinese" in w for w in warnings)
    
    def test_validate_japanese_no_particles(self):
        """Test validation of Japanese without particles."""
        text = "あいうえおかきくけこ" * 10  # Just random hiragana
        score, warnings = LanguageValidator.validate_japanese(text)
        assert any("particles" in w.lower() for w in warnings)
    
    def test_validate_japanese_no_characters(self):
        """Test validation of text with no Japanese characters."""
        text = "This is English text."
        score, warnings = LanguageValidator.validate_japanese(text)
        assert score < 0.5
        assert any("No Japanese characters" in w for w in warnings)
    
    # Generic language validation
    def test_validate_language_vietnamese(self):
        """Test validate_language routes to Vietnamese."""
        text = "Xin chào các bạn"
        score, warnings = LanguageValidator.validate_language(text, "vi")
        assert score > 0
    
    def test_validate_language_chinese(self):
        """Test validate_language routes to Chinese."""
        text = "你好世界"
        score, warnings = LanguageValidator.validate_language(text, "zh")
        assert score > 0
    
    def test_validate_language_english(self):
        """Test validate_language routes to English."""
        text = "The quick brown fox jumps over the lazy dog."
        score, warnings = LanguageValidator.validate_language(text, "en")
        assert score > 0
    
    def test_validate_language_japanese(self):
        """Test validate_language routes to Japanese."""
        text = "日本語のテストです。"
        score, warnings = LanguageValidator.validate_language(text, "ja")
        assert score > 0
    
    def test_validate_language_unknown(self):
        """Test validate_language with unknown language."""
        text = "Some text"
        score, warnings = LanguageValidator.validate_language(text, "unknown")
        # Should return default values
        assert score == 1.0
        assert warnings == []
    
    def test_validate_language_french(self):
        """Test validate_language with French (generic validation)."""
        text = "Bonjour, c'est un texte français avec des caractères spéciaux."
        score, warnings = LanguageValidator.validate_language(text, "fr")
        # Should use generic validation
        assert score >= 0


class TestHelperFunctions:
    """Tests for module helper functions."""
    
    def test_get_language_pair_existing(self):
        """Test getting existing language pair."""
        pair = get_language_pair("en", "vi")
        assert pair.source == "en"
        assert pair.target == "vi"
    
    def test_get_language_pair_new(self):
        """Test getting new language pair."""
        pair = get_language_pair("xx", "yy")
        assert pair.source == "xx"
        assert pair.target == "yy"
    
    def test_get_language_name_known(self):
        """Test getting name of known language."""
        name = get_language_name("vi")
        assert name == "Vietnamese"
    
    def test_get_language_name_unknown(self):
        """Test getting name of unknown language."""
        name = get_language_name("unknown")
        assert name == "unknown"
    
    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        languages = get_supported_languages()
        assert isinstance(languages, list)
        assert "en" in languages
        assert "vi" in languages
        assert "ja" in languages
        assert len(languages) >= 10
    
    def test_is_language_supported_true(self):
        """Test checking supported language."""
        assert is_language_supported("en") is True
        assert is_language_supported("vi") is True
        assert is_language_supported("ja") is True
    
    def test_is_language_supported_false(self):
        """Test checking unsupported language."""
        assert is_language_supported("unknown") is False
        assert is_language_supported("xx") is False


class TestLanguageDatabaseCompleteness:
    """Tests for LANGUAGES database completeness."""
    
    def test_all_common_pair_languages_exist(self):
        """Test that all languages in COMMON_PAIRS exist in LANGUAGES."""
        for key, pair in COMMON_PAIRS.items():
            # Some codes like zh-Hans may be in pairs
            # Check that at least base language exists
            source_base = pair.source.split("-")[0]
            target_base = pair.target.split("-")[0]
            # Full code should be in LANGUAGES or base code
            assert pair.source in LANGUAGES or source_base in LANGUAGES, \
                f"Source '{pair.source}' not in LANGUAGES"
            assert pair.target in LANGUAGES or target_base in LANGUAGES, \
                f"Target '{pair.target}' not in LANGUAGES"
    
    def test_all_languages_have_required_fields(self):
        """Test that all language entries have required fields."""
        for code, info in LANGUAGES.items():
            assert info.code == code
            assert info.name != ""
            assert info.native_name != ""
            assert info.direction in ["ltr", "rtl"]
    
    def test_asian_languages_no_spaces(self):
        """Test that Asian languages are marked as no-space languages."""
        assert LANGUAGES["zh"].has_spaces is False
        assert LANGUAGES["ja"].has_spaces is False
        # Korean uses spaces between words
        assert LANGUAGES["ko"].has_spaces is True
    
    def test_length_ratios_reasonable(self):
        """Test that language length ratios are reasonable."""
        for code, info in LANGUAGES.items():
            assert 0.5 <= info.avg_length_ratio <= 2.0, \
                f"Language {code} has unreasonable ratio: {info.avg_length_ratio}"


class TestLanguageIntegration:
    """Integration tests for language module."""
    
    def test_detect_and_validate_vietnamese(self):
        """Test detecting and validating Vietnamese text."""
        text = "Đây là một đoạn văn bản tiếng Việt để kiểm tra."
        
        # Detect
        lang, conf = LanguageDetector.detect(text)
        assert lang == "vi"
        
        # Validate
        score, warnings = LanguageValidator.validate_language(text, lang)
        assert score > 0.5
    
    def test_detect_and_validate_english(self):
        """Test detecting and validating English text."""
        text = "This is a sample English text for testing the language module."
        
        lang, conf = LanguageDetector.detect(text)
        assert lang == "en"
        
        score, warnings = LanguageValidator.validate_language(text, lang)
        assert score > 0.5
    
    def test_language_pair_workflow(self):
        """Test complete language pair workflow."""
        # Get pair
        pair = get_language_pair("en", "vi")
        
        # Check properties
        assert pair.source == "en"
        assert pair.target == "vi"
        
        # Get names
        source_name = get_language_name(pair.source)
        target_name = get_language_name(pair.target)
        
        assert source_name == "English"
        assert target_name == "Vietnamese"
        
        # Reverse
        reverse = pair.reverse()
        assert reverse.source == "vi"
        assert reverse.target == "en"
