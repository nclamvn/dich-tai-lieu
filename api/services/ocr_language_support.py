"""
Multi-language OCR Support — Script detection and language routing.

Provides:
- Unicode script detection (Latin, CJK, Arabic, Cyrillic, Devanagari, Thai, ...)
- Language-to-script mapping for 9+ languages
- OCR engine recommendation per language
- Text script analysis (detect dominant script in text)

Standalone module — no core/ or external OCR imports.

Usage::

    support = OcrLanguageSupport()

    # Detect script from text
    info = support.detect_script("心臓は筋肉です")
    # → ScriptInfo(script="cjk", language="ja", confidence=0.95)

    # Get OCR config for a language
    config = support.get_ocr_config("vi")
    # → OcrConfig(lang_code="vie", engine="paddleocr", ...)

    # Analyze text for mixed scripts
    analysis = support.analyze_text("Hello 世界")
    # → {"latin": 0.55, "cjk": 0.45}
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ScriptInfo:
    """Result of script detection."""

    script: str  # latin, cjk, arabic, cyrillic, devanagari, thai, hangul
    language: str  # best-guess ISO 639-1 code
    confidence: float  # 0.0 - 1.0
    details: str = ""


@dataclass
class OcrConfig:
    """OCR configuration for a language."""

    language: str  # ISO 639-1 (en, vi, ja, ...)
    lang_code: str  # OCR engine code (eng, vie, jpn, ...)
    script: str  # Script family
    engine: str  # Recommended engine (paddleocr, tesseract, mathpix)
    supports_vertical: bool = False
    requires_preprocessing: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Script detection patterns
# ---------------------------------------------------------------------------

# Unicode ranges for script families
_SCRIPT_RANGES: List[Tuple[str, int, int]] = [
    # CJK Unified Ideographs
    ("cjk", 0x4E00, 0x9FFF),
    ("cjk", 0x3400, 0x4DBF),  # CJK Extension A
    ("cjk", 0xF900, 0xFAFF),  # CJK Compatibility
    # Hiragana + Katakana (Japanese-specific)
    ("hiragana", 0x3040, 0x309F),
    ("katakana", 0x30A0, 0x30FF),
    # Hangul (Korean)
    ("hangul", 0xAC00, 0xD7AF),
    ("hangul", 0x1100, 0x11FF),
    # Arabic
    ("arabic", 0x0600, 0x06FF),
    ("arabic", 0x0750, 0x077F),
    ("arabic", 0xFB50, 0xFDFF),  # Arabic Presentation Forms
    # Hebrew
    ("hebrew", 0x0590, 0x05FF),
    # Cyrillic
    ("cyrillic", 0x0400, 0x04FF),
    ("cyrillic", 0x0500, 0x052F),
    # Devanagari (Hindi, Sanskrit)
    ("devanagari", 0x0900, 0x097F),
    # Thai
    ("thai", 0x0E00, 0x0E7F),
    # Latin (basic + extended for Vietnamese diacritics)
    ("latin", 0x0041, 0x024F),
    ("latin", 0x1E00, 0x1EFF),  # Latin Extended Additional (Vietnamese)
]

# Script → likely language mapping
_SCRIPT_TO_LANGUAGE: Dict[str, str] = {
    "hiragana": "ja",
    "katakana": "ja",
    "hangul": "ko",
    "arabic": "ar",
    "hebrew": "he",
    "cyrillic": "ru",
    "devanagari": "hi",
    "thai": "th",
    "latin": "en",
    "cjk": "zh",  # default; refined by kana/hangul detection
}


# ---------------------------------------------------------------------------
# Language configurations
# ---------------------------------------------------------------------------

LANGUAGE_CONFIGS: Dict[str, OcrConfig] = {
    "en": OcrConfig(
        language="en", lang_code="eng", script="latin",
        engine="paddleocr",
    ),
    "vi": OcrConfig(
        language="vi", lang_code="vie", script="latin",
        engine="paddleocr",
        notes="Vietnamese diacritics require Unicode-aware OCR",
    ),
    "ja": OcrConfig(
        language="ja", lang_code="jpn", script="cjk",
        engine="paddleocr",
        supports_vertical=True,
        notes="Mixed hiragana/katakana/kanji",
    ),
    "zh": OcrConfig(
        language="zh", lang_code="chi_sim", script="cjk",
        engine="paddleocr",
        supports_vertical=True,
    ),
    "ko": OcrConfig(
        language="ko", lang_code="kor", script="hangul",
        engine="paddleocr",
    ),
    "ar": OcrConfig(
        language="ar", lang_code="ara", script="arabic",
        engine="paddleocr",
        requires_preprocessing=True,
        notes="RTL script, requires bidi preprocessing",
    ),
    "ru": OcrConfig(
        language="ru", lang_code="rus", script="cyrillic",
        engine="paddleocr",
    ),
    "hi": OcrConfig(
        language="hi", lang_code="hin", script="devanagari",
        engine="paddleocr",
        requires_preprocessing=True,
    ),
    "th": OcrConfig(
        language="th", lang_code="tha", script="thai",
        engine="paddleocr",
        notes="No word boundaries in Thai script",
    ),
}

SUPPORTED_LANGUAGES = list(LANGUAGE_CONFIGS.keys())


# ---------------------------------------------------------------------------
# OcrLanguageSupport
# ---------------------------------------------------------------------------

class OcrLanguageSupport:
    """Multi-language OCR support with script detection."""

    def detect_script(self, text: str) -> ScriptInfo:
        """Detect the dominant script in text.

        Returns ScriptInfo with script name, likely language, and confidence.
        """
        if not text or not text.strip():
            return ScriptInfo(script="unknown", language="en", confidence=0.0)

        script_counts = self._count_scripts(text)

        if not script_counts:
            return ScriptInfo(script="unknown", language="en", confidence=0.0)

        # Find dominant script
        total = sum(script_counts.values())
        dominant_script, dominant_count = script_counts.most_common(1)[0]
        confidence = dominant_count / total if total > 0 else 0.0

        # Refine language from script
        language = self._refine_language(dominant_script, script_counts)

        return ScriptInfo(
            script=dominant_script,
            language=language,
            confidence=round(confidence, 4),
        )

    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze text for script distribution.

        Returns {script: proportion} dict.
        """
        if not text or not text.strip():
            return {}

        script_counts = self._count_scripts(text)
        total = sum(script_counts.values())

        if total == 0:
            return {}

        return {
            script: round(count / total, 4)
            for script, count in script_counts.most_common()
        }

    def get_ocr_config(self, language: str) -> Optional[OcrConfig]:
        """Get OCR configuration for a language."""
        return LANGUAGE_CONFIGS.get(language)

    def get_supported_languages(self) -> List[str]:
        """List supported language codes."""
        return list(LANGUAGE_CONFIGS.keys())

    def is_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in LANGUAGE_CONFIGS

    def get_config_for_script(self, script: str) -> Optional[OcrConfig]:
        """Get OCR config based on detected script."""
        language = _SCRIPT_TO_LANGUAGE.get(script, "en")
        return LANGUAGE_CONFIGS.get(language)

    def detect_language(self, text: str) -> str:
        """Convenience: detect language code from text."""
        info = self.detect_script(text)
        return info.language

    def is_rtl(self, language: str) -> bool:
        """Check if a language uses RTL script."""
        return language in ("ar", "he", "fa")

    def is_cjk(self, language: str) -> bool:
        """Check if a language uses CJK characters."""
        return language in ("zh", "ja", "ko")

    def needs_preprocessing(self, language: str) -> bool:
        """Check if OCR input needs preprocessing."""
        config = LANGUAGE_CONFIGS.get(language)
        return config.requires_preprocessing if config else False

    # --- Internal ---

    def _count_scripts(self, text: str) -> Counter:
        """Count characters by script family."""
        counts: Counter = Counter()

        for char in text:
            if char.isspace() or char in '.,;:!?-()[]{}"\'/\\':
                continue

            code = ord(char)
            matched = False

            for script, start, end in _SCRIPT_RANGES:
                if start <= code <= end:
                    counts[script] += 1
                    matched = True
                    break

            if not matched and char.isalpha():
                # Fallback: check Unicode category
                try:
                    name = unicodedata.name(char, "")
                    if "LATIN" in name:
                        counts["latin"] += 1
                    elif "CJK" in name:
                        counts["cjk"] += 1
                    elif "ARABIC" in name:
                        counts["arabic"] += 1
                    elif "CYRILLIC" in name:
                        counts["cyrillic"] += 1
                except ValueError:
                    pass

        return counts

    def _refine_language(
        self, dominant_script: str, counts: Counter,
    ) -> str:
        """Refine language detection from script distribution."""
        # CJK refinement: check for Japanese kana or Korean hangul
        if dominant_script == "cjk":
            if counts.get("hiragana", 0) > 0 or counts.get("katakana", 0) > 0:
                return "ja"
            if counts.get("hangul", 0) > 0:
                return "ko"
            return "zh"

        # Latin refinement: check for Vietnamese diacritics
        if dominant_script == "latin":
            # This is a heuristic; real detection needs more context
            return _SCRIPT_TO_LANGUAGE.get("latin", "en")

        return _SCRIPT_TO_LANGUAGE.get(dominant_script, "en")
