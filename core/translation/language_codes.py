"""
Language Code Definitions
ISO 639-1 codes for supported languages
"""

# TranslateGemma supported languages (55 languages)
TRANSLATEGEMMA_LANGUAGES = [
    "ar",  # Arabic
    "bg",  # Bulgarian
    "bn",  # Bengali
    "ca",  # Catalan
    "cs",  # Czech
    "da",  # Danish
    "de",  # German
    "el",  # Greek
    "en",  # English
    "es",  # Spanish
    "et",  # Estonian
    "fa",  # Persian
    "fi",  # Finnish
    "fr",  # French
    "gu",  # Gujarati
    "he",  # Hebrew
    "hi",  # Hindi
    "hr",  # Croatian
    "hu",  # Hungarian
    "id",  # Indonesian
    "it",  # Italian
    "ja",  # Japanese
    "kn",  # Kannada
    "ko",  # Korean
    "lt",  # Lithuanian
    "lv",  # Latvian
    "ml",  # Malayalam
    "mr",  # Marathi
    "ms",  # Malay
    "nl",  # Dutch
    "no",  # Norwegian
    "pa",  # Punjabi
    "pl",  # Polish
    "pt",  # Portuguese
    "ro",  # Romanian
    "ru",  # Russian
    "sk",  # Slovak
    "sl",  # Slovenian
    "sr",  # Serbian
    "sv",  # Swedish
    "sw",  # Swahili
    "ta",  # Tamil
    "te",  # Telugu
    "th",  # Thai
    "tl",  # Tagalog
    "tr",  # Turkish
    "uk",  # Ukrainian
    "ur",  # Urdu
    "vi",  # Vietnamese
    "zh",  # Chinese
    "zu",  # Zulu
]

# Cloud API typically supports more languages
CLOUD_API_LANGUAGES = TRANSLATEGEMMA_LANGUAGES + [
    "af",  # Afrikaans
    "am",  # Amharic
    "az",  # Azerbaijani
    "be",  # Belarusian
    "bs",  # Bosnian
    "cy",  # Welsh
    "ga",  # Irish
    "gl",  # Galician
    "is",  # Icelandic
    "ka",  # Georgian
    "km",  # Khmer
    "ky",  # Kyrgyz
    "lo",  # Lao
    "mk",  # Macedonian
    "mn",  # Mongolian
    "my",  # Burmese
    "ne",  # Nepali
    "si",  # Sinhala
    "sq",  # Albanian
    "uz",  # Uzbek
]

# Alias for backward compatibility
LANGUAGE_CODES = TRANSLATEGEMMA_LANGUAGES

# Language names for UI display
LANGUAGE_NAMES = {
    "ar": "Arabic (العربية)",
    "bg": "Bulgarian (Български)",
    "bn": "Bengali (বাংলা)",
    "ca": "Catalan (Català)",
    "cs": "Czech (Čeština)",
    "da": "Danish (Dansk)",
    "de": "German (Deutsch)",
    "el": "Greek (Ελληνικά)",
    "en": "English",
    "es": "Spanish (Español)",
    "et": "Estonian (Eesti)",
    "fa": "Persian (فارسی)",
    "fi": "Finnish (Suomi)",
    "fr": "French (Français)",
    "gu": "Gujarati (ગુજરાતી)",
    "he": "Hebrew (עברית)",
    "hi": "Hindi (हिन्दी)",
    "hr": "Croatian (Hrvatski)",
    "hu": "Hungarian (Magyar)",
    "id": "Indonesian (Bahasa)",
    "it": "Italian (Italiano)",
    "ja": "Japanese (日本語)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ko": "Korean (한국어)",
    "lt": "Lithuanian (Lietuvių)",
    "lv": "Latvian (Latviešu)",
    "ml": "Malayalam (മലയാളം)",
    "mr": "Marathi (मराठी)",
    "ms": "Malay (Bahasa Melayu)",
    "nl": "Dutch (Nederlands)",
    "no": "Norwegian (Norsk)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "pl": "Polish (Polski)",
    "pt": "Portuguese (Português)",
    "ro": "Romanian (Română)",
    "ru": "Russian (Русский)",
    "sk": "Slovak (Slovenčina)",
    "sl": "Slovenian (Slovenščina)",
    "sr": "Serbian (Српски)",
    "sv": "Swedish (Svenska)",
    "sw": "Swahili (Kiswahili)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "th": "Thai (ไทย)",
    "tl": "Tagalog (Filipino)",
    "tr": "Turkish (Türkçe)",
    "uk": "Ukrainian (Українська)",
    "ur": "Urdu (اردو)",
    "vi": "Vietnamese (Tiếng Việt)",
    "zh": "Chinese (中文)",
    "zu": "Zulu (isiZulu)",
}


def get_language_name(code: str) -> str:
    """Get human-readable language name from code"""
    return LANGUAGE_NAMES.get(code.lower(), code)


def get_language_code(name: str) -> str:
    """Get language code from name (reverse lookup)"""
    name_lower = name.lower()
    for code, lang_name in LANGUAGE_NAMES.items():
        if name_lower in lang_name.lower():
            return code
    return name
