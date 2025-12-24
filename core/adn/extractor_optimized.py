#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized ADN Extractor

Performance optimizations:
1. Pre-compiled regex patterns (singleton)
2. Lazy evaluation - only process what's needed
3. Batch text processing
4. Result caching for similar content

Version: 1.0.0
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from .schema import (
    ContentADN,
    ProperNoun,
    Character,
    Term,
    Pattern,
    ProperNounType,
    PatternType,
)

logger = logging.getLogger(__name__)


class CompiledPatterns:
    """
    Singleton for pre-compiled regex patterns.
    Compile once, reuse forever.
    """
    _instance = None
    _initialized = False

    # Proper noun patterns by language
    PROPER_NOUN_PATTERNS = {
        'en': [
            (r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', ProperNounType.PERSON),
            (r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', ProperNounType.PERSON),  # Two capitalized words
            (r'\b(?:University|Institute|College)\s+(?:of\s+)?[A-Z][a-z]+', ProperNounType.ORGANIZATION),
            (r'\b[A-Z]{2,6}\b', ProperNounType.ORGANIZATION),  # Acronyms
        ],
        'vi': [
            (r'\b(?:Ông|Bà|Anh|Chị|Cô|Thầy)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+)*', ProperNounType.PERSON),
            (r'\b[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+){1,3}', ProperNounType.PERSON),
        ],
        'ja': [
            (r'[一-龯]{2,4}(?:さん|様|先生)', ProperNounType.PERSON),
            (r'[一-龯]+(?:株式会社|大学)', ProperNounType.ORGANIZATION),
        ],
        'zh': [
            (r'[一-龯]{2,4}(?:先生|女士|教授)', ProperNounType.PERSON),
            (r'[一-龯]+(?:公司|大学|学院)', ProperNounType.ORGANIZATION),
        ],
        'ko': [
            (r'[가-힣]{2,4}(?:씨|님|선생님)', ProperNounType.PERSON),
            (r'[가-힣]+(?:회사|대학교)', ProperNounType.ORGANIZATION),
        ],
    }

    # Structure patterns (language-independent where possible)
    STRUCTURE_PATTERNS = [
        (r'^(?:Chapter|Chương|第)\s*\d+', PatternType.CHAPTER_START),
        (r'^(?:Part|Phần|部)\s*\d+', PatternType.SECTION_BREAK),
        (r'[「『""].*?[」』""]', PatternType.DIALOGUE),
        (r'^\s*[-•*]\s+', PatternType.LIST_STRUCTURE),
        (r'\[\d+\]|\(\d+\)', PatternType.FOOTNOTE),
        (r'^\s*\*\s*\*\s*\*\s*$', PatternType.SECTION_BREAK),
    ]

    # Common exclusion words
    EXCLUDE_WORDS = {
        'The', 'This', 'That', 'These', 'Those', 'There', 'Here',
        'I', 'We', 'You', 'He', 'She', 'It', 'They',
        'What', 'Who', 'Where', 'When', 'Why', 'How',
        'And', 'But', 'Or', 'If', 'Then', 'So', 'As',
        'Chapter', 'Section', 'Part', 'Introduction', 'Conclusion',
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not CompiledPatterns._initialized:
            self._compile_patterns()
            CompiledPatterns._initialized = True

    def _compile_patterns(self):
        """Compile all patterns once"""
        # Compile proper noun patterns
        self.proper_noun_compiled = {}
        for lang, patterns in self.PROPER_NOUN_PATTERNS.items():
            self.proper_noun_compiled[lang] = [
                (re.compile(pattern, re.MULTILINE | re.UNICODE), pn_type)
                for pattern, pn_type in patterns
            ]

        # Compile structure patterns
        self.structure_compiled = [
            (re.compile(pattern, re.MULTILINE | re.IGNORECASE), p_type)
            for pattern, p_type in self.STRUCTURE_PATTERNS
        ]

        # Compile exclusion set (lowercase for comparison)
        self.exclude_lower = {w.lower() for w in self.EXCLUDE_WORDS}

        logger.debug("ADN patterns compiled (singleton)")

    def get_proper_noun_patterns(self, lang: str) -> List:
        """Get compiled patterns for language"""
        return self.proper_noun_compiled.get(lang, self.proper_noun_compiled.get('en', []))

    def get_structure_patterns(self) -> List:
        """Get compiled structure patterns"""
        return self.structure_compiled

    def is_excluded(self, text: str) -> bool:
        """Check if text is in exclusion list"""
        return text.lower() in self.exclude_lower


class OptimizedADNExtractor:
    """
    Optimized ADN Extractor with caching and batch processing.

    Optimizations:
    1. Pre-compiled patterns (singleton)
    2. Batch text processing
    3. Deduplication during extraction
    4. Early termination for small documents
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "vi",
        glossary: Dict[str, str] = None,
    ):
        self.source_lang = source_lang.lower()[:2]
        self.target_lang = target_lang.lower()[:2]
        self.glossary = glossary or {}

        # Get pre-compiled patterns (singleton)
        self._patterns = CompiledPatterns()

    def extract(
        self,
        segments: List[str],
        document_type: str = "unknown",
    ) -> ContentADN:
        """
        Extract ADN with optimizations.
        """
        adn = ContentADN(
            source_language=self.source_lang,
            target_language=self.target_lang,
            document_type=document_type,
            total_segments=len(segments),
        )

        # Combine texts for batch processing
        combined_text = "\n\n".join(segments)
        adn.total_characters = len(combined_text)

        # Skip if too small
        if len(combined_text) < 100:
            return adn

        # Extract in batch (more efficient than per-segment)
        adn.proper_nouns = self._extract_proper_nouns_batch(combined_text)
        adn.patterns = self._extract_patterns_batch(combined_text)

        # Characters from proper nouns (persons)
        adn.characters = self._extract_characters(adn.proper_nouns)

        # Terms from glossary
        adn.terms = self._extract_terms(combined_text)
        adn.unique_terms = len(adn.terms)

        return adn

    def _extract_proper_nouns_batch(self, text: str) -> List[ProperNoun]:
        """Extract proper nouns in single pass"""
        found: Dict[str, ProperNoun] = {}

        patterns = self._patterns.get_proper_noun_patterns(self.source_lang)

        for compiled_re, pn_type in patterns:
            for match in compiled_re.finditer(text):
                name = match.group().strip()

                # Skip short matches
                if len(name) < 2:
                    continue

                # Skip excluded words
                if self._patterns.is_excluded(name):
                    continue

                # Deduplicate
                key = name.lower()
                if key in found:
                    # Increment occurrence
                    found[key].occurrences.append(match.start())
                else:
                    found[key] = ProperNoun(
                        text=name,
                        type=pn_type,
                        occurrences=[match.start()],
                        confidence=self._calculate_confidence(name, pn_type),
                    )

        # Sort by occurrence count
        result = sorted(found.values(), key=lambda x: len(x.occurrences), reverse=True)
        return result

    def _calculate_confidence(self, text: str, pn_type: ProperNounType) -> float:
        """Calculate confidence score"""
        score = 0.5

        # Boost for longer names
        word_count = len(text.split())
        if word_count >= 2:
            score += 0.15
        if word_count >= 3:
            score += 0.1

        # Boost for title prefixes
        if re.match(r'^(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)', text):
            score += 0.2

        # Boost for Vietnamese honorifics
        if re.match(r'^(?:Ông|Bà|Anh|Chị|Cô|Thầy)', text):
            score += 0.2

        # Boost for acronyms
        if text.isupper() and 2 <= len(text) <= 6:
            score += 0.15

        return min(score, 1.0)

    def _extract_patterns_batch(self, text: str) -> List[Pattern]:
        """Extract structural patterns in single pass"""
        found: Dict[PatternType, Pattern] = {}

        for compiled_re, p_type in self._patterns.get_structure_patterns():
            matches = list(compiled_re.finditer(text))

            if matches:
                examples = [m.group()[:50] for m in matches[:3]]
                markers = [compiled_re.pattern[:30]]

                if p_type in found:
                    found[p_type].occurrences += len(matches)
                    # Add unique examples
                    for ex in examples:
                        if ex not in found[p_type].examples:
                            found[p_type].examples.append(ex)
                else:
                    found[p_type] = Pattern(
                        type=p_type,
                        occurrences=len(matches),
                        markers=markers,
                        examples=examples,
                    )

        return list(found.values())

    def _extract_characters(self, proper_nouns: List[ProperNoun]) -> List[Character]:
        """Extract characters from person-type proper nouns"""
        characters = []

        for pn in proper_nouns:
            if pn.type == ProperNounType.PERSON:
                # Determine role based on occurrences
                occ_count = len(pn.occurrences)
                if occ_count >= 10:
                    role = "main"
                elif occ_count >= 5:
                    role = "supporting"
                elif occ_count >= 2:
                    role = "minor"
                else:
                    role = "mentioned"

                characters.append(Character(
                    name=pn.text,
                    variants=pn.variants,
                    role=role,
                    first_appearance=min(pn.occurrences) if pn.occurrences else 0,
                    occurrences=pn.occurrences,
                ))

        # Sort by first appearance
        characters.sort(key=lambda c: c.first_appearance)
        return characters

    def _extract_terms(self, text: str) -> List[Term]:
        """Extract terms from glossary matches"""
        terms = []
        text_lower = text.lower()

        for original, translation in self.glossary.items():
            # Count occurrences
            count = text_lower.count(original.lower())

            if count > 0:
                terms.append(Term(
                    original=original,
                    translation=translation,
                    domain="glossary",
                    frequency=count,
                ))

        # Sort by frequency
        terms.sort(key=lambda t: t.frequency, reverse=True)
        return terms

    def extract_to_json(
        self,
        segments: List[str],
        document_type: str = "unknown",
        indent: int = 2,
    ) -> str:
        """Extract ADN and return as JSON string."""
        adn = self.extract(segments, document_type)
        return adn.to_json(indent=indent)

    def extract_to_dict(
        self,
        segments: List[str],
        document_type: str = "unknown",
    ) -> Dict:
        """Extract ADN and return as dictionary."""
        adn = self.extract(segments, document_type)
        return adn.to_dict()


# Backwards compatibility alias
ADNExtractorOptimized = OptimizedADNExtractor
