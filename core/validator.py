#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
QualityValidator - Translation quality assessment with domain-specific rules.

This module provides comprehensive quality validation for translations,
including:
- Length ratio validation (source vs translated)
- Completeness checks (sentence count preservation)
- Language quality assessment (diacritics, artifacts)
- Domain-specific validation (finance, medical, literature, technology)
- Glossary term verification
- Punctuation and capitalization preservation

Usage:
    from core.validator import QualityValidator, TranslationResult

    # Basic validation
    result = QualityValidator.validate(
        source="Hello world",
        translated="Xin chào thế giới",
        domain="default"
    )
    print(f"Quality: {result.quality_score:.2f}")

    # Domain-specific validation
    result = QualityValidator.validate(
        source="The IPO raised $50M",
        translated="Đợt IPO huy động được 50 triệu USD",
        domain="finance"
    )

Classes:
    TranslationResult: Data class containing translation and quality metrics.
    QualityValidator: Main validation engine with domain-specific rules.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

try:
    from .language import LanguageValidator, get_language_pair
except ImportError:
    # Fallback if language module not available
    LanguageValidator = None
    get_language_pair = None


@dataclass
class TranslationResult:
    """
    Translation result with quality metrics and validation details.

    Contains the translated text along with comprehensive quality assessment
    including domain-specific scores and warnings.

    Attributes:
        chunk_id: Identifier of the source chunk (0 for full-text validation).
        source: Original source text that was translated.
        translated: The resulting translated text.
        quality_score: Overall quality score (0.0 to 1.0).
        warnings: List of quality issues detected.
        glossary_matches: Dict mapping glossary terms to their translations.
        domain: Domain used for validation (finance, medical, etc.).
        domain_scores: Individual scores per validation category.

    Example:
        >>> result = TranslationResult(
        ...     chunk_id=1,
        ...     source="Hello",
        ...     translated="Xin chào",
        ...     quality_score=0.95
        ... )
        >>> if result.quality_score < 0.7:
        ...     print(f"Low quality: {result.warnings}")
    """
    chunk_id: int
    source: str
    translated: str
    quality_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    glossary_matches: dict = field(default_factory=dict)
    domain: Optional[str] = None
    domain_scores: Dict[str, float] = field(default_factory=dict)
    overlap_char_count: int = 0  # FIX-002: Số ký tự overlap để merger biết cắt


class QualityValidator:
    """
    Translation quality validator with domain-specific rules.

    Provides comprehensive quality assessment using weighted scoring across
    multiple dimensions: length ratio, completeness, language quality,
    glossary adherence, and domain-specific requirements.

    Supported domains:
    - finance: Preserves numbers, currencies, financial abbreviations
    - medical: Validates dosage info, medical terms (safety-critical)
    - literature: Checks dialogue formatting, paragraph structure
    - technology: Preserves code blocks, technical abbreviations
    - default: General-purpose validation

    Attributes:
        DOMAIN_WEIGHTS: Dict mapping domains to category weights.

    Example:
        >>> result = QualityValidator.validate(
        ...     source="Take 500mg twice daily",
        ...     translated="Uống 500mg hai lần mỗi ngày",
        ...     domain="medical"
        ... )
        >>> print(f"Score: {result.quality_score}")
        >>> print(f"Warnings: {result.warnings}")
    """

    # Domain-specific validation weights
    DOMAIN_WEIGHTS = {
        'finance': {
            'length': 0.15,
            'completeness': 0.25,
            'vietnamese': 0.25,
            'glossary': 0.25,
            'domain_specific': 0.10
        },
        'literature': {
            'length': 0.10,
            'completeness': 0.30,
            'vietnamese': 0.30,
            'glossary': 0.15,
            'domain_specific': 0.15
        },
        'medical': {
            'length': 0.15,
            'completeness': 0.30,
            'vietnamese': 0.20,
            'glossary': 0.30,  # Critical for medical terms
            'domain_specific': 0.05
        },
        'technology': {
            'length': 0.15,
            'completeness': 0.25,
            'vietnamese': 0.25,
            'glossary': 0.20,
            'domain_specific': 0.15
        },
        'default': {
            'length': 0.20,
            'completeness': 0.30,
            'vietnamese': 0.30,
            'glossary': 0.20,
            'domain_specific': 0.00
        }
    }

    @staticmethod
    def calculate_length_ratio(source: str, translated: str) -> float:
        """
        Calculate length ratio score between source and translation.

        Vietnamese translations are typically 20-40% longer than English.
        Scores based on how well the ratio matches expected range.

        Args:
            source: Original source text.
            translated: Translated text.

        Returns:
            Score from 0.0 to 1.0:
            - 1.0: Ratio in optimal range (1.1 to 1.5)
            - 0.7: Ratio in acceptable range (0.9 to 1.7)
            - 0.3: Ratio outside acceptable range
        """
        if not source or not translated:
            return 0.0

        ratio = len(translated) / len(source)
        # Optimal range for EN->VI is 1.2 to 1.4
        if 1.1 <= ratio <= 1.5:
            return 1.0
        elif 0.9 <= ratio <= 1.7:
            return 0.7
        else:
            return 0.3

    @staticmethod
    def check_completeness(source: str, translated: str) -> float:
        """
        Check if translation is complete by comparing sentence counts.

        Args:
            source: Original source text.
            translated: Translated text.

        Returns:
            Score from 0.0 to 1.0 based on sentence ratio.
        """
        # Check số lượng câu (approximate)
        source_sentences = len(re.split(r'[.!?]', source))
        trans_sentences = len(re.split(r'[.!?]', translated))

        ratio = trans_sentences / max(source_sentences, 1)
        if 0.8 <= ratio <= 1.2:
            return 1.0
        elif 0.6 <= ratio <= 1.4:
            return 0.7
        else:
            return 0.3

    @staticmethod
    def check_vietnamese_quality(text: str) -> float:
        """
        Check Vietnamese language quality (legacy fallback method).

        Validates Vietnamese text by checking for:
        - Translation artifacts (brackets, TODO markers)
        - Vietnamese diacritics presence

        Args:
            text: Text to validate.

        Returns:
            Score from 0.0 to 1.0 based on quality indicators.
        """
        score = 1.0

        # Check for common translation artifacts
        artifacts = [
            r'\[\[.*?\]\]',  # brackets từ prompt
            r'Note:',         # chú thích không dịch
            r'TODO:',
            r'\[CHUNK \d+\]', # chunk markers không xử lý đúng
        ]

        for pattern in artifacts:
            if re.search(pattern, text):
                score -= 0.2

        # Check Vietnamese diacritics
        viet_chars = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
        if not any(c in text.lower() for c in viet_chars):
            score -= 0.5  # Có thể không phải tiếng Việt

        return max(0.0, score)

    @staticmethod
    def validate_finance_domain(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Validate finance domain translation requirements.

        Checks preservation of:
        - Numeric values and percentages
        - Currency symbols ($, €, £, ¥, ₫)
        - Financial abbreviations (P/E, IPO, CEO, etc.)

        Args:
            source: Original financial text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.
        """
        score = 1.0
        warnings = []

        # Check numeric format preservation (percentages, currencies)
        source_numbers = re.findall(r'\d+\.?\d*%?', source)
        trans_numbers = re.findall(r'\d+\.?\d*%?', translated)

        if len(source_numbers) != len(trans_numbers):
            score -= 0.3
            warnings.append("Number count mismatch (finance)")

        # Check currency symbols preserved
        currency_symbols = ['$', '€', '£', '¥', '₫']
        for symbol in currency_symbols:
            if source.count(symbol) != translated.count(symbol):
                score -= 0.2
                warnings.append(f"Currency symbol '{symbol}' count mismatch")
                break

        # Check financial abbreviations preserved
        fin_abbrevs = ['P/E', 'IPO', 'CEO', 'CFO', 'ETF', 'ROI', 'GDP']
        for abbrev in fin_abbrevs:
            if abbrev in source and abbrev not in translated:
                score -= 0.1
                warnings.append(f"Financial abbreviation '{abbrev}' missing")

        return max(0.0, score), warnings

    @staticmethod
    def validate_literature_domain(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Validate literature domain translation requirements.

        Checks preservation of:
        - Dialogue formatting (quotation marks)
        - Paragraph structure
        - Temporal markers for narrative tense

        Args:
            source: Original literary text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.
        """
        score = 1.0
        warnings = []

        # Check dialogue formatting preserved
        source_quotes = source.count('"') + source.count("'")
        trans_quotes = translated.count('"') + translated.count('"') + translated.count('"')

        if abs(source_quotes - trans_quotes) > 2:
            score -= 0.2
            warnings.append("Dialogue formatting may be inconsistent")

        # Check paragraph structure (line breaks)
        source_paras = len(source.split('\n\n'))
        trans_paras = len(translated.split('\n\n'))

        if abs(source_paras - trans_paras) > 1:
            score -= 0.15
            warnings.append("Paragraph structure differs significantly")

        # Check narrative tense consistency (past tense indicators)
        past_indicators_en = len(re.findall(r'\b(was|were|had|did)\b', source.lower()))
        past_indicators_vi = len(re.findall(r'\b(đã|đang|sẽ)\b', translated.lower()))

        # Vietnamese should have temporal markers
        if past_indicators_en > 5 and past_indicators_vi < 2:
            score -= 0.1
            warnings.append("Temporal markers may be missing")

        return max(0.0, score), warnings

    @staticmethod
    def validate_medical_domain(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Validate medical domain translation requirements (safety-critical).

        Checks preservation of:
        - Dosage information (mg, ml, frequency) - CRITICAL
        - Medical abbreviations (ICU, MRI, HIV, etc.)
        - Safety-critical terms (contraindication, adverse, toxic)

        Args:
            source: Original medical text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.

        Note:
            Medical translations are safety-critical. This validator
            flags content for human review when safety terms are present.
        """
        score = 1.0
        warnings = []

        # Check dosage information preserved (critical!)
        dosage_patterns = [
            r'\d+\s*(mg|ml|g|mcg|IU)',
            r'\d+\s*times?\s*(daily|per day)',
            r'every\s+\d+\s*hours?'
        ]

        for pattern in dosage_patterns:
            source_matches = len(re.findall(pattern, source, re.IGNORECASE))
            if source_matches > 0:
                # Dosage info exists - check translation has numbers
                trans_numbers = re.findall(r'\d+', translated)
                if len(trans_numbers) == 0:
                    score -= 0.4
                    warnings.append("CRITICAL: Dosage information may be missing")
                    break

        # Check medical abbreviations preserved or explained
        medical_abbrevs = ['ICU', 'MRI', 'CT', 'X-ray', 'DNA', 'RNA', 'HIV', 'AIDS']
        for abbrev in medical_abbrevs:
            if abbrev in source and abbrev not in translated:
                # Check if it's explained instead
                if abbrev.lower() not in translated.lower():
                    score -= 0.15
                    warnings.append(f"Medical abbreviation '{abbrev}' not preserved")

        # Warning for safety-critical terms
        critical_terms = ['contraindication', 'adverse', 'fatal', 'emergency', 'toxic']
        for term in critical_terms:
            if term in source.lower():
                warnings.append(f"REVIEW REQUIRED: Safety-critical term '{term}' present")

        return max(0.0, score), warnings

    @staticmethod
    def validate_technology_domain(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Validate technology domain translation requirements.

        Checks preservation of:
        - Code blocks (triple backticks)
        - Inline code formatting (single backticks)
        - Technical abbreviations (API, SQL, HTTP, etc.)
        - Code identifiers (camelCase, snake_case)

        Args:
            source: Original technical text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.
        """
        score = 1.0
        warnings = []

        # Check code blocks preserved
        source_code_blocks = re.findall(r'```[\s\S]*?```', source)
        trans_code_blocks = re.findall(r'```[\s\S]*?```', translated)

        if len(source_code_blocks) != len(trans_code_blocks):
            score -= 0.3
            warnings.append("Code block count mismatch")

        # Check inline code preserved
        source_inline = source.count('`')
        trans_inline = translated.count('`')

        if abs(source_inline - trans_inline) > 2:
            score -= 0.2
            warnings.append("Inline code formatting may be inconsistent")

        # Check technical abbreviations preserved
        tech_abbrevs = ['API', 'SQL', 'HTTP', 'HTTPS', 'JSON', 'XML', 'CSS', 'HTML', 'URL']
        for abbrev in tech_abbrevs:
            if abbrev in source and abbrev not in translated:
                score -= 0.1
                warnings.append(f"Technical abbreviation '{abbrev}' missing")

        # Check command/function names preserved (camelCase, snake_case)
        source_identifiers = re.findall(r'\b[a-z][a-zA-Z0-9_]*\b', source)
        for identifier in source_identifiers:
            if '_' in identifier or (identifier[0].islower() and any(c.isupper() for c in identifier)):
                # This looks like a code identifier
                if identifier in source and identifier not in translated:
                    score -= 0.05
                    warnings.append(f"Code identifier '{identifier}' may be translated incorrectly")
                    break  # Don't spam warnings

        return max(0.0, score), warnings

    @staticmethod
    def check_punctuation_consistency(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Check if punctuation marks are consistently preserved.

        Validates that important punctuation (., !, ?, :, ;) appears
        in similar quantities in source and translation.

        Args:
            source: Original text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.
        """
        score = 1.0
        warnings = []

        # Check important punctuation marks
        important_marks = ['.', '!', '?', ':', ';']
        for mark in important_marks:
            source_count = source.count(mark)
            trans_count = translated.count(mark)

            # Allow some flexibility but flag major differences
            if source_count > 0 and abs(source_count - trans_count) > max(2, source_count * 0.3):
                score -= 0.1
                warnings.append(f"Punctuation '{mark}' count differs significantly")

        return max(0.0, score), warnings

    @staticmethod
    def check_capitalization_preservation(source: str, translated: str) -> tuple[float, List[str]]:
        """
        Check if proper nouns and acronyms are preserved.

        Validates that capitalized words (potential proper nouns) and
        acronyms (all-caps words) appear in the translation.

        Args:
            source: Original text.
            translated: Translated text.

        Returns:
            Tuple of (score, warnings) where score is 0.0-1.0.
        """
        score = 1.0
        warnings = []

        # Find capitalized words (potential proper nouns)
        source_caps = re.findall(r'\b[A-Z][a-z]+\b', source)

        # Check if these appear in translation
        missing_caps = []
        for cap_word in set(source_caps):
            if cap_word not in translated and cap_word.lower() not in translated.lower():
                missing_caps.append(cap_word)

        if len(missing_caps) > 3:
            score -= 0.2
            warnings.append(f"Multiple proper nouns may be missing: {', '.join(missing_caps[:3])}...")

        # Find acronyms (all caps, 2+ letters)
        source_acronyms = re.findall(r'\b[A-Z]{2,}\b', source)
        for acronym in set(source_acronyms):
            if acronym not in translated:
                score -= 0.15
                warnings.append(f"Acronym '{acronym}' not preserved")

        return max(0.0, score), warnings

    @classmethod
    def validate(cls, source: str, translated: str,
                glossary_mgr: Optional['GlossaryManager'] = None,
                domain: Optional[str] = None,
                source_lang: str = "en",
                target_lang: str = "vi") -> TranslationResult:
        """
        Perform comprehensive translation validation.

        Main validation entry point that runs all quality checks with
        domain-specific weighting. Combines scores from:
        - Length ratio (source vs translation)
        - Completeness (sentence count)
        - Language quality (target language validation)
        - Glossary adherence
        - Domain-specific rules
        - Punctuation consistency
        - Capitalization preservation

        Args:
            source: Original source text.
            translated: Translated text to validate.
            glossary_mgr: Optional GlossaryManager for term validation.
            domain: Domain for specialized validation. If None, uses
                glossary_mgr's domain or defaults to 'default'.
            source_lang: Source language code (default: 'en').
            target_lang: Target language code (default: 'vi').

        Returns:
            TranslationResult with quality_score (0.0-1.0), warnings,
            and detailed domain_scores breakdown.

        Example:
            >>> result = QualityValidator.validate(
            ...     source="The API returns JSON",
            ...     translated="API trả về JSON",
            ...     domain="technology"
            ... )
            >>> print(f"Quality: {result.quality_score:.2f}")
            >>> print(f"Domain scores: {result.domain_scores}")
        """

        # Initialize warnings list
        warnings = []

        # Detect domain if not provided
        if domain is None and glossary_mgr:
            domain = getattr(glossary_mgr, 'domain', 'default')
        if domain is None:
            domain = 'default'

        # Get domain-specific weights
        weights = cls.DOMAIN_WEIGHTS.get(domain, cls.DOMAIN_WEIGHTS['default'])

        # Basic quality checks
        length_score = cls.calculate_length_ratio(source, translated)
        complete_score = cls.check_completeness(source, translated)

        # Language-specific validation (replaces old viet_score)
        if LanguageValidator:
            lang_score, lang_warnings = LanguageValidator.validate_language(translated, target_lang)
        else:
            # Fallback to old Vietnamese validation
            lang_score = cls.check_vietnamese_quality(translated)
            lang_warnings = []

        warnings.extend(lang_warnings)

        # Additional quality checks
        punct_score, punct_warnings = cls.check_punctuation_consistency(source, translated)
        cap_score, cap_warnings = cls.check_capitalization_preservation(source, translated)

        # Glossary check
        glossary_score = 1.0
        glossary_matches = {}

        if glossary_mgr:
            glossary_score, term_warnings = glossary_mgr.validate_translation(source, translated)
            warnings.extend(term_warnings)

        # Domain-specific validation
        domain_score = 1.0
        domain_warnings = []

        if domain == 'finance':
            domain_score, domain_warnings = cls.validate_finance_domain(source, translated)
        elif domain == 'literature':
            domain_score, domain_warnings = cls.validate_literature_domain(source, translated)
        elif domain == 'medical':
            domain_score, domain_warnings = cls.validate_medical_domain(source, translated)
        elif domain == 'technology':
            domain_score, domain_warnings = cls.validate_technology_domain(source, translated)

        warnings.extend(domain_warnings)
        warnings.extend(punct_warnings)
        warnings.extend(cap_warnings)

        # Store individual scores for analytics
        domain_scores = {
            'length': length_score,
            'completeness': complete_score,
            'language': lang_score,
            'glossary': glossary_score,
            'domain_specific': domain_score,
            'punctuation': punct_score,
            'capitalization': cap_score
        }

        # Calculate final score using domain-specific weights
        quality_score = (
            length_score * weights['length'] +
            complete_score * weights['completeness'] +
            lang_score * weights['vietnamese'] +
            glossary_score * weights['glossary'] +
            domain_score * weights['domain_specific']
        )

        # Add warnings based on scores
        if length_score < 0.7:
            warnings.append("Abnormal length ratio")
        if complete_score < 0.7:
            warnings.append("May be incomplete")
        if lang_score < 0.7:
            target_name = get_language_name(target_lang) if get_language_name else target_lang
            warnings.append(f"{target_name} quality issues")
        if domain_score < 0.7 and domain != 'default':
            warnings.append(f"Domain-specific ({domain}) quality issues")

        return TranslationResult(
            chunk_id=0,
            source=source,
            translated=translated,
            quality_score=quality_score,
            warnings=warnings,
            glossary_matches=glossary_matches,
            domain=domain,
            domain_scores=domain_scores
        )
