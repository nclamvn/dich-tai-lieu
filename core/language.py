#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Language Support - Multi-language configuration and detection
"""

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class LanguageCode(str, Enum):
    """Supported language codes"""
    ENGLISH = "en"
    VIETNAMESE = "vi"
    CHINESE = "zh"
    CHINESE_SIMPLIFIED = "zh-Hans"
    CHINESE_TRADITIONAL = "zh-Hant"
    JAPANESE = "ja"
    KOREAN = "ko"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"


@dataclass
class LanguageInfo:
    """Language information and characteristics"""
    code: str
    name: str
    native_name: str
    direction: str = "ltr"  # ltr (left-to-right) or rtl (right-to-left)

    # Character sets for detection
    char_range: Optional[str] = None

    # Translation characteristics
    avg_length_ratio: float = 1.0  # Compared to English

    # Quality validation parameters
    requires_diacritics: bool = False
    has_spaces: bool = True
    has_capitalization: bool = True


# Language database
LANGUAGES: Dict[str, LanguageInfo] = {
    "en": LanguageInfo(
        code="en",
        name="English",
        native_name="English",
        char_range="a-zA-Z",
        avg_length_ratio=1.0,
        requires_diacritics=False,
        has_spaces=True,
        has_capitalization=True
    ),
    "vi": LanguageInfo(
        code="vi",
        name="Vietnamese",
        native_name="Tiếng Việt",
        char_range="a-zA-ZàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ",
        avg_length_ratio=1.3,  # Vietnamese typically 30% longer than English
        requires_diacritics=True,
        has_spaces=True,
        has_capitalization=True
    ),
    "zh": LanguageInfo(
        code="zh",
        name="Chinese",
        native_name="中文",
        char_range="\u4e00-\u9fff",  # CJK Unified Ideographs
        avg_length_ratio=0.7,  # Chinese typically shorter (characters vs words)
        requires_diacritics=False,
        has_spaces=False,
        has_capitalization=False
    ),
    "zh-Hans": LanguageInfo(
        code="zh-Hans",
        name="Chinese (Simplified)",
        native_name="简体中文",
        char_range="\u4e00-\u9fff",
        avg_length_ratio=0.7,
        requires_diacritics=False,
        has_spaces=False,
        has_capitalization=False
    ),
    "zh-Hant": LanguageInfo(
        code="zh-Hant",
        name="Chinese (Traditional)",
        native_name="繁體中文",
        char_range="\u4e00-\u9fff",
        avg_length_ratio=0.7,
        requires_diacritics=False,
        has_spaces=False,
        has_capitalization=False
    ),
    "ja": LanguageInfo(
        code="ja",
        name="Japanese",
        native_name="日本語",
        char_range="\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff",  # Hiragana + Katakana + Kanji
        avg_length_ratio=0.8,
        requires_diacritics=False,
        has_spaces=False,
        has_capitalization=False
    ),
    "ko": LanguageInfo(
        code="ko",
        name="Korean",
        native_name="한국어",
        char_range="\uac00-\ud7af",  # Hangul
        avg_length_ratio=0.9,
        requires_diacritics=False,
        has_spaces=True,
        has_capitalization=False
    ),
    "fr": LanguageInfo(
        code="fr",
        name="French",
        native_name="Français",
        char_range="a-zA-ZàâäæçéèêëïîôùûüÿœÀÂÄÆÇÉÈÊËÏÎÔÙÛÜŸŒ",
        avg_length_ratio=1.1,
        requires_diacritics=True,
        has_spaces=True,
        has_capitalization=True
    ),
    "es": LanguageInfo(
        code="es",
        name="Spanish",
        native_name="Español",
        char_range="a-zA-ZáéíóúüñÁÉÍÓÚÜÑ",
        avg_length_ratio=1.15,
        requires_diacritics=True,
        has_spaces=True,
        has_capitalization=True
    ),
    "de": LanguageInfo(
        code="de",
        name="German",
        native_name="Deutsch",
        char_range="a-zA-ZäöüßÄÖÜ",
        avg_length_ratio=1.1,
        requires_diacritics=True,
        has_spaces=True,
        has_capitalization=True
    )
}


@dataclass
class LanguagePair:
    """A translation language pair"""
    source: str
    target: str

    # Quality expectations for this pair
    expected_length_ratio_min: float = 0.5
    expected_length_ratio_max: float = 2.0

    # Validation weights (can be customized per pair)
    validation_weights: Optional[Dict[str, float]] = None

    def __post_init__(self):
        # Calculate expected length ratio based on language characteristics
        source_info = LANGUAGES.get(self.source)
        target_info = LANGUAGES.get(self.target)

        if source_info and target_info:
            ratio = target_info.avg_length_ratio / source_info.avg_length_ratio
            self.expected_length_ratio_min = ratio * 0.7
            self.expected_length_ratio_max = ratio * 1.5

    def __str__(self):
        return f"{self.source}→{self.target}"

    def reverse(self) -> 'LanguagePair':
        """Get the reverse language pair"""
        return LanguagePair(source=self.target, target=self.source)


# Predefined common language pairs
COMMON_PAIRS = {
    # English pairs
    "en-vi": LanguagePair("en", "vi"),
    "vi-en": LanguagePair("vi", "en"),
    "en-zh": LanguagePair("en", "zh"),
    "zh-en": LanguagePair("zh", "en"),
    "en-zh-Hans": LanguagePair("en", "zh-Hans"),
    "zh-Hans-en": LanguagePair("zh-Hans", "en"),
    "en-ja": LanguagePair("en", "ja"),
    "ja-en": LanguagePair("ja", "en"),
    "en-ko": LanguagePair("en", "ko"),
    "ko-en": LanguagePair("ko", "en"),
    "en-fr": LanguagePair("en", "fr"),
    "fr-en": LanguagePair("fr", "en"),
    "en-es": LanguagePair("en", "es"),
    "es-en": LanguagePair("es", "en"),
    "en-de": LanguagePair("en", "de"),
    "de-en": LanguagePair("de", "en"),

    # Japanese pairs (PRIMARY: JA→VI flow)
    "ja-vi": LanguagePair("ja", "vi"),  # Primary translation flow
    "vi-ja": LanguagePair("vi", "ja"),  # Reverse translation

    # Other Asian language pairs
    "zh-vi": LanguagePair("zh", "vi"),
    "vi-zh": LanguagePair("vi", "zh"),
    "ko-vi": LanguagePair("ko", "vi"),
    "vi-ko": LanguagePair("vi", "ko"),
}


class LanguageDetector:
    """Simple rule-based language detection"""

    @staticmethod
    def detect(text: str, candidates: Optional[List[str]] = None) -> Tuple[str, float]:
        """
        Detect language from text

        Args:
            text: Text to detect
            candidates: Optional list of candidate language codes

        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or not text.strip():
            return "unknown", 0.0

        # If candidates provided, only check those
        languages_to_check = candidates if candidates else list(LANGUAGES.keys())

        scores = {}

        for lang_code in languages_to_check:
            lang_info = LANGUAGES.get(lang_code)
            if not lang_info or not lang_info.char_range:
                continue

            # Count characters in this language's range
            import re
            pattern = f"[{lang_info.char_range}]"
            matches = re.findall(pattern, text)

            # Calculate score (percentage of text in this language)
            text_chars = [c for c in text if not c.isspace() and not c.isdigit()]
            if text_chars:
                score = len(matches) / len(text_chars)
                scores[lang_code] = score

        if not scores:
            return "unknown", 0.0

        # Get language with highest score
        best_lang = max(scores.items(), key=lambda x: x[1])
        return best_lang[0], best_lang[1]

    @staticmethod
    def is_language(text: str, lang_code: str, threshold: float = 0.7) -> bool:
        """
        Check if text is in specified language

        Args:
            text: Text to check
            lang_code: Expected language code
            threshold: Minimum confidence threshold

        Returns:
            True if text appears to be in specified language
        """
        detected_lang, confidence = LanguageDetector.detect(text, [lang_code])
        return detected_lang == lang_code and confidence >= threshold


class LanguageValidator:
    """Language-specific validation rules"""

    @staticmethod
    def validate_vietnamese(text: str) -> Tuple[float, List[str]]:
        """Validate Vietnamese text quality"""
        score = 1.0
        warnings = []

        # Check for Vietnamese diacritics
        vi_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
        if not any(c in text.lower() for c in vi_chars):
            score -= 0.5
            warnings.append("Missing Vietnamese diacritics")

        # Check for common Vietnamese words
        common_words = ['là', 'của', 'và', 'có', 'được', 'trong', 'một', 'không']
        words_found = sum(1 for word in common_words if word in text.lower())

        if len(text) > 100 and words_found < 2:
            score -= 0.2
            warnings.append("Missing common Vietnamese words")

        return max(0.0, score), warnings

    @staticmethod
    def validate_chinese(text: str) -> Tuple[float, List[str]]:
        """Validate Chinese text quality"""
        score = 1.0
        warnings = []

        # Check for Chinese characters
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)

        if not chinese_chars:
            score -= 0.5
            warnings.append("Missing Chinese characters")

        # Check character to total ratio
        text_chars = [c for c in text if not c.isspace()]
        if text_chars:
            chinese_ratio = len(chinese_chars) / len(text_chars)
            if chinese_ratio < 0.5:
                score -= 0.3
                warnings.append("Low Chinese character ratio")

        # Check for inappropriate spaces (Chinese doesn't use spaces between words)
        space_count = text.count(' ')
        if len(chinese_chars) > 0:
            space_ratio = space_count / len(chinese_chars)
            if space_ratio > 0.3:  # Too many spaces
                score -= 0.2
                warnings.append("Excessive spaces in Chinese text")

        return max(0.0, score), warnings

    @staticmethod
    def validate_english(text: str) -> Tuple[float, List[str]]:
        """Validate English text quality"""
        score = 1.0
        warnings = []

        # Check for basic English characteristics
        import re
        english_words = re.findall(r'\b[a-zA-Z]+\b', text)

        if not english_words:
            score -= 0.5
            warnings.append("Missing English words")

        # Check for common English words
        common_words = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'but']
        words_found = sum(1 for word in common_words if word.lower() in text.lower())

        if len(text) > 100 and words_found < 2:
            score -= 0.2
            warnings.append("Missing common English words")

        return max(0.0, score), warnings

    @staticmethod
    def validate_japanese(text: str) -> Tuple[float, List[str]]:
        """
        Validate Japanese text quality.

        Checks for:
        - Presence of Japanese character types (hiragana, katakana, kanji)
        - Proper mix of character types (pure kanji might be Chinese)
        - Japanese particles and common words

        Args:
            text: Text to validate

        Returns:
            Tuple of (score 0.0-1.0, list of warnings)
        """
        import re
        score = 1.0
        warnings = []

        # Count character types
        hiragana = re.findall(r'[\u3040-\u309f]', text)  # ひらがな
        katakana = re.findall(r'[\u30a0-\u30ff]', text)  # カタカナ
        kanji = re.findall(r'[\u4e00-\u9fff]', text)     # 漢字

        total_japanese = len(hiragana) + len(katakana) + len(kanji)

        # No Japanese characters at all
        if total_japanese == 0:
            score -= 0.6
            warnings.append("No Japanese characters found")
            return max(0.0, score), warnings

        # Pure kanji without hiragana/katakana - might be Chinese
        if len(kanji) > 0 and len(hiragana) == 0 and len(katakana) == 0:
            score -= 0.3
            warnings.append("No hiragana/katakana found - text might be Chinese")

        # Check for Japanese particles (unique to Japanese)
        particles = ['は', 'が', 'を', 'に', 'で', 'から', 'まで', 'へ', 'より', 'と', 'も', 'の']
        particles_found = sum(1 for p in particles if p in text)

        if len(text) > 50 and particles_found == 0:
            score -= 0.2
            warnings.append("No Japanese particles detected")

        # Check hiragana/katakana ratio (Japanese typically has significant hiragana)
        if total_japanese > 0:
            kana_ratio = (len(hiragana) + len(katakana)) / total_japanese
            if kana_ratio < 0.1 and len(text) > 100:
                score -= 0.1
                warnings.append("Very low kana ratio")

        # Check for common Japanese sentence endings
        polite_endings = ['です', 'ます', 'ました', 'ません']
        casual_endings = ['だ', 'である', 'だった']

        has_endings = any(e in text for e in polite_endings + casual_endings)
        if len(text) > 100 and not has_endings:
            score -= 0.1
            warnings.append("No common Japanese sentence endings found")

        return max(0.0, score), warnings

    @staticmethod
    def validate_language(text: str, lang_code: str) -> Tuple[float, List[str]]:
        """
        Validate text for specific language

        Args:
            text: Text to validate
            lang_code: Language code

        Returns:
            Tuple of (score, warnings)
        """
        if lang_code == "vi":
            return LanguageValidator.validate_vietnamese(text)
        elif lang_code in ["zh", "zh-Hans", "zh-Hant"]:
            return LanguageValidator.validate_chinese(text)
        elif lang_code == "en":
            return LanguageValidator.validate_english(text)
        elif lang_code == "ja":
            return LanguageValidator.validate_japanese(text)
        else:
            # Generic validation - just check if text has appropriate characters
            lang_info = LANGUAGES.get(lang_code)
            if lang_info and lang_info.char_range:
                import re
                pattern = f"[{lang_info.char_range}]"
                matches = re.findall(pattern, text)

                text_chars = [c for c in text if not c.isspace()]
                if text_chars:
                    ratio = len(matches) / len(text_chars)
                    if ratio >= 0.5:
                        return 1.0, []
                    else:
                        return ratio, [f"Low {lang_info.name} character ratio"]

            return 1.0, []  # No specific validation


def get_language_pair(source: str, target: str) -> LanguagePair:
    """
    Get or create language pair

    Args:
        source: Source language code
        target: Target language code

    Returns:
        LanguagePair object
    """
    pair_key = f"{source}-{target}"

    if pair_key in COMMON_PAIRS:
        return COMMON_PAIRS[pair_key]

    return LanguagePair(source=source, target=target)


def get_language_name(code: str) -> str:
    """Get language name from code"""
    lang_info = LANGUAGES.get(code)
    return lang_info.name if lang_info else code


def get_supported_languages() -> List[str]:
    """Get list of supported language codes"""
    return list(LANGUAGES.keys())


def is_language_supported(code: str) -> bool:
    """Check if language code is supported"""
    return code in LANGUAGES
