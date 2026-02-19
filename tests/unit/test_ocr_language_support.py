"""
Unit tests for api/services/ocr_language_support.py — Multi-language OCR support.

Target: 90%+ coverage.
"""

import pytest

from api.services.ocr_language_support import (
    OcrLanguageSupport,
    OcrConfig,
    ScriptInfo,
    LANGUAGE_CONFIGS,
    SUPPORTED_LANGUAGES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def support():
    return OcrLanguageSupport()


# ---------------------------------------------------------------------------
# ScriptInfo / OcrConfig data classes
# ---------------------------------------------------------------------------

class TestDataClasses:
    def test_script_info(self):
        info = ScriptInfo(script="latin", language="en", confidence=0.95)
        assert info.script == "latin"
        assert info.language == "en"
        assert info.confidence == 0.95

    def test_ocr_config(self):
        config = OcrConfig(
            language="ja", lang_code="jpn", script="cjk",
            engine="paddleocr", supports_vertical=True,
        )
        assert config.language == "ja"
        assert config.lang_code == "jpn"
        assert config.supports_vertical is True
        assert config.requires_preprocessing is False


# ---------------------------------------------------------------------------
# Language configs
# ---------------------------------------------------------------------------

class TestLanguageConfigs:
    def test_nine_languages(self):
        assert len(LANGUAGE_CONFIGS) >= 9

    def test_supported_list(self):
        assert "en" in SUPPORTED_LANGUAGES
        assert "vi" in SUPPORTED_LANGUAGES
        assert "ja" in SUPPORTED_LANGUAGES
        assert "zh" in SUPPORTED_LANGUAGES
        assert "ko" in SUPPORTED_LANGUAGES
        assert "ar" in SUPPORTED_LANGUAGES
        assert "ru" in SUPPORTED_LANGUAGES
        assert "hi" in SUPPORTED_LANGUAGES
        assert "th" in SUPPORTED_LANGUAGES

    def test_japanese_vertical(self):
        config = LANGUAGE_CONFIGS["ja"]
        assert config.supports_vertical is True

    def test_arabic_rtl(self):
        config = LANGUAGE_CONFIGS["ar"]
        assert config.requires_preprocessing is True

    def test_all_have_engine(self):
        for lang, config in LANGUAGE_CONFIGS.items():
            assert config.engine, f"{lang} missing engine"


# ---------------------------------------------------------------------------
# Script detection
# ---------------------------------------------------------------------------

class TestScriptDetection:
    def test_english(self, support):
        info = support.detect_script("Hello world")
        assert info.script == "latin"
        assert info.confidence > 0.5

    def test_chinese(self, support):
        info = support.detect_script("中华人民共和国")
        assert info.script == "cjk"
        assert info.language == "zh"

    def test_japanese_with_kana(self, support):
        info = support.detect_script("心臓はきんにくです")
        assert info.language == "ja"

    def test_japanese_katakana(self, support):
        info = support.detect_script("コンピュータ")
        assert info.script == "katakana"
        assert info.language == "ja"

    def test_korean(self, support):
        info = support.detect_script("안녕하세요")
        assert info.script == "hangul"
        assert info.language == "ko"

    def test_arabic(self, support):
        info = support.detect_script("مرحبا بالعالم")
        assert info.script == "arabic"
        assert info.language == "ar"

    def test_cyrillic(self, support):
        info = support.detect_script("Привет мир")
        assert info.script == "cyrillic"
        assert info.language == "ru"

    def test_devanagari(self, support):
        info = support.detect_script("नमस्ते दुनिया")
        assert info.script == "devanagari"
        assert info.language == "hi"

    def test_thai(self, support):
        info = support.detect_script("สวัสดีครับ")
        assert info.script == "thai"
        assert info.language == "th"

    def test_empty_text(self, support):
        info = support.detect_script("")
        assert info.script == "unknown"
        assert info.confidence == 0.0

    def test_whitespace_only(self, support):
        info = support.detect_script("   \n  ")
        assert info.script == "unknown"

    def test_punctuation_only(self, support):
        info = support.detect_script("!@#$%...")
        assert info.script == "unknown"


# ---------------------------------------------------------------------------
# Text analysis
# ---------------------------------------------------------------------------

class TestAnalyzeText:
    def test_pure_latin(self, support):
        analysis = support.analyze_text("Hello world test")
        assert "latin" in analysis
        assert analysis["latin"] > 0.9

    def test_mixed_cjk_latin(self, support):
        analysis = support.analyze_text("Hello 世界")
        assert "latin" in analysis
        assert "cjk" in analysis

    def test_empty(self, support):
        assert support.analyze_text("") == {}

    def test_proportions_sum_to_one(self, support):
        analysis = support.analyze_text("Hello 世界 test")
        total = sum(analysis.values())
        assert abs(total - 1.0) < 0.01


# ---------------------------------------------------------------------------
# OCR config lookup
# ---------------------------------------------------------------------------

class TestOcrConfigLookup:
    def test_get_config(self, support):
        config = support.get_ocr_config("vi")
        assert config is not None
        assert config.lang_code == "vie"
        assert config.script == "latin"

    def test_get_config_unknown(self, support):
        assert support.get_ocr_config("xyz") is None

    def test_is_supported(self, support):
        assert support.is_supported("en") is True
        assert support.is_supported("xyz") is False

    def test_get_supported_languages(self, support):
        langs = support.get_supported_languages()
        assert len(langs) >= 9
        assert "en" in langs

    def test_get_config_for_script(self, support):
        config = support.get_config_for_script("arabic")
        assert config is not None
        assert config.language == "ar"

    def test_get_config_for_unknown_script(self, support):
        config = support.get_config_for_script("unknown")
        assert config is not None  # defaults to "en"
        assert config.language == "en"


# ---------------------------------------------------------------------------
# Language properties
# ---------------------------------------------------------------------------

class TestLanguageProperties:
    def test_is_rtl(self, support):
        assert support.is_rtl("ar") is True
        assert support.is_rtl("he") is True
        assert support.is_rtl("fa") is True
        assert support.is_rtl("en") is False

    def test_is_cjk(self, support):
        assert support.is_cjk("zh") is True
        assert support.is_cjk("ja") is True
        assert support.is_cjk("ko") is True
        assert support.is_cjk("en") is False

    def test_needs_preprocessing(self, support):
        assert support.needs_preprocessing("ar") is True
        assert support.needs_preprocessing("hi") is True
        assert support.needs_preprocessing("en") is False
        assert support.needs_preprocessing("xyz") is False


# ---------------------------------------------------------------------------
# Convenience methods
# ---------------------------------------------------------------------------

class TestConvenience:
    def test_detect_language(self, support):
        lang = support.detect_language("안녕하세요")
        assert lang == "ko"

    def test_detect_language_english(self, support):
        lang = support.detect_language("Hello world")
        assert lang == "en"

    def test_detect_language_empty(self, support):
        lang = support.detect_language("")
        assert lang == "en"  # default
