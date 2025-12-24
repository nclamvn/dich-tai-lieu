#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proper Noun Extractor

Extracts named entities (people, places, organizations) from text.
Supports multiple languages: EN, VI, JA, ZH, KO

Version: 1.0.0
"""

import re
from typing import List, Dict, Set
from collections import defaultdict

from .schema import ProperNoun, ProperNounType


class ProperNounExtractor:
    """
    Extract proper nouns from text using pattern matching and heuristics.

    For production, can be enhanced with:
    - spaCy NER
    - Hugging Face transformers
    - Cloud NER APIs (Google, AWS)
    """

    # Common patterns by language
    PATTERNS = {
        'en': {
            'person': [
                r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Sir|Lord|Lady)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',  # Two/three capitalized words
            ],
            'place': [
                r'\b(?:Mount|Lake|River|City|Town|Village|Port|Cape|Bay)\s+[A-Z][a-z]+',
                r'\b[A-Z][a-z]+(?:land|burg|ville|ton|ford|shire|polis|chester)\b',
                r'\b(?:New|North|South|East|West)\s+[A-Z][a-z]+\b',
            ],
            'organization': [
                r'\b(?:University|Institute|College|Academy|School)\s+(?:of\s+)?[A-Z][a-z]+',
                r'\b(?:Company|Corporation|Inc\.|Ltd\.|LLC|Corp\.)\b',
                r'\b[A-Z][A-Z]{1,5}\b',  # Acronyms (2-6 chars)
            ],
        },
        'vi': {
            'person': [
                r'\b(?:Ông|Bà|Anh|Chị|Cô|Chú|Bác|Dì|Cậu|Mợ|Thầy|Cô)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+)*',
                # Vietnamese full name pattern (Họ + Tên đệm + Tên)
                r'\b[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+(?:\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+){1,3}',
            ],
            'place': [
                r'\b(?:Thành phố|Tỉnh|Huyện|Xã|Quận|Phường|Thị trấn|Làng|Thôn)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐ][a-zàáảãạăằắẳẵặâầấẩẫậđ]+',
                r'\b(?:Hà Nội|Hồ Chí Minh|Đà Nẵng|Huế|Cần Thơ|Hải Phòng|Nha Trang|Đà Lạt|Vũng Tàu|Phú Quốc)\b',
                r'\b(?:Sông|Núi|Hồ|Biển|Vịnh|Đảo)\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐ][a-zàáảãạăằắẳẵặâầấẩẫậđ]+',
            ],
            'organization': [
                r'\b(?:Công ty|Tập đoàn|Trường|Viện|Bộ|Sở|Ban|Hội|Đảng)\s+[A-ZÀÁẢÃẠ][a-zàáảãạ]+',
                r'\b(?:UBND|HĐND|ĐBQH|VNPT|EVN|VTV|HTV)\b',  # Vietnamese acronyms
            ],
        },
        'ja': {
            'person': [
                r'[一-龯]{1,4}(?:さん|様|氏|君|ちゃん|先生|殿)',  # Japanese name + honorific
                r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Western names in Japanese text
            ],
            'place': [
                r'[一-龯]+(?:市|県|町|村|区|島|山|川|湖|海)',
                r'(?:東京|大阪|京都|北海道|沖縄|名古屋|横浜|神戸|福岡|札幌)',
            ],
            'organization': [
                r'[一-龯]+(?:株式会社|会社|大学|学校|銀行|病院)',
                r'(?:株式会社|有限会社)[一-龯]+',
            ],
        },
        'zh': {
            'person': [
                r'[一-龯]{2,4}(?:先生|女士|小姐|老师|教授|医生)',
                r'[一-龯]{2,3}',  # Chinese names (2-3 characters)
            ],
            'place': [
                r'[一-龯]+(?:市|省|县|区|镇|村|山|河|湖|海)',
                r'(?:北京|上海|广州|深圳|香港|台北|澳门)',
            ],
            'organization': [
                r'[一-龯]+(?:公司|集团|大学|学院|银行|医院)',
            ],
        },
        'ko': {
            'person': [
                r'[가-힣]{2,4}(?:씨|님|선생님|교수님)',
                r'[가-힣]{2,4}',  # Korean names
            ],
            'place': [
                r'[가-힣]+(?:시|도|군|구|동|리)',
                r'(?:서울|부산|인천|대구|대전|광주|울산|제주)',
            ],
            'organization': [
                r'[가-힣]+(?:주식회사|회사|대학교|병원|은행)',
            ],
        },
    }

    # Common words to exclude (false positives)
    EXCLUDE_WORDS = {
        'en': {
            'The', 'This', 'That', 'These', 'Those', 'There', 'Here',
            'I', 'We', 'You', 'He', 'She', 'It', 'They',
            'What', 'Who', 'Where', 'When', 'Why', 'How',
            'And', 'But', 'Or', 'If', 'Then', 'So', 'As',
            'Chapter', 'Section', 'Part', 'Page', 'Figure', 'Table',
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        },
        'vi': {
            'Này', 'Đó', 'Kia', 'Đây', 'Ấy',
            'Tôi', 'Chúng', 'Họ', 'Nó', 'Bạn', 'Mình',
            'Và', 'Hoặc', 'Nhưng', 'Nếu', 'Thì', 'Vì',
            'Chương', 'Phần', 'Mục', 'Trang', 'Bảng', 'Hình',
        },
        'ja': {
            'これ', 'それ', 'あれ', 'ここ', 'そこ', 'あそこ',
            '私', '僕', '俺', '彼', '彼女',
        },
        'zh': {
            '这', '那', '这里', '那里',
            '我', '你', '他', '她', '它', '我们', '你们', '他们',
        },
        'ko': {
            '이것', '그것', '저것',
            '나', '너', '그', '그녀', '우리', '당신',
        },
    }

    def __init__(self, language: str = 'en'):
        """
        Initialize extractor.

        Args:
            language: Language code (en, vi, ja, zh, ko)
        """
        self.language = language.lower()[:2]
        self.patterns = self.PATTERNS.get(self.language, self.PATTERNS['en'])
        self.exclude = self.EXCLUDE_WORDS.get(self.language, set())

    def extract(self, text: str, segment_index: int = 0) -> List[ProperNoun]:
        """
        Extract proper nouns from text.

        Args:
            text: Input text
            segment_index: Index of the segment (for tracking occurrences)

        Returns:
            List of ProperNoun objects
        """
        results = []
        seen: Set[str] = set()

        for noun_type, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.UNICODE)
                    for match in matches:
                        noun_text = match.group().strip()

                        # Skip excluded words
                        if noun_text in self.exclude:
                            continue

                        # Skip too short
                        if len(noun_text) < 2:
                            continue

                        # Skip if already seen (case-insensitive for non-CJK)
                        key = noun_text.lower() if self.language in ['en', 'vi'] else noun_text
                        if key in seen:
                            continue

                        seen.add(key)

                        results.append(ProperNoun(
                            text=noun_text,
                            type=ProperNounType(noun_type),
                            occurrences=[segment_index],
                            confidence=self._calculate_confidence(noun_text, noun_type),
                        ))
                except re.error:
                    continue

        return results

    def extract_from_segments(self, segments: List[str]) -> List[ProperNoun]:
        """
        Extract proper nouns from multiple segments.
        Merges occurrences of the same noun.

        Args:
            segments: List of text segments

        Returns:
            Merged list of ProperNoun objects
        """
        noun_map: Dict[str, ProperNoun] = {}

        for idx, segment in enumerate(segments):
            nouns = self.extract(segment, idx)

            for noun in nouns:
                # Use lowercase key for non-CJK languages
                key = noun.text.lower() if self.language in ['en', 'vi'] else noun.text

                if key in noun_map:
                    # Merge occurrences
                    noun_map[key].occurrences.extend(noun.occurrences)
                    # Keep higher confidence
                    noun_map[key].confidence = max(noun_map[key].confidence, noun.confidence)
                else:
                    noun_map[key] = noun

        # Sort by occurrence count (most frequent first)
        result = list(noun_map.values())
        result.sort(key=lambda x: len(x.occurrences), reverse=True)

        return result

    def _calculate_confidence(self, text: str, noun_type: str) -> float:
        """Calculate confidence score for a proper noun"""
        score = 0.5

        # Boost for longer names (more likely to be real entities)
        word_count = len(text.split())
        if word_count >= 2:
            score += 0.15
        if word_count >= 3:
            score += 0.1

        # Boost for title prefixes (Mr., Dr., etc.)
        if re.match(r'^(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Sir|Lord)', text):
            score += 0.2

        # Boost for Vietnamese honorifics
        if re.match(r'^(?:Ông|Bà|Anh|Chị|Cô|Chú|Bác|Thầy)', text):
            score += 0.2

        # Boost for Japanese honorifics
        if re.search(r'(?:さん|様|氏|君|先生)$', text):
            score += 0.2

        # Boost for all caps (acronyms)
        if text.isupper() and 2 <= len(text) <= 6:
            score += 0.15

        # Boost for known place suffixes
        place_suffixes = ['land', 'burg', 'ville', 'ton', 'ford', 'shire', 'polis',
                         '市', '県', '省', '시', '도']
        for suffix in place_suffixes:
            if text.endswith(suffix):
                score += 0.1
                break

        return min(score, 1.0)

    def find_variants(self, nouns: List[ProperNoun]) -> List[ProperNoun]:
        """
        Find variant forms of the same proper noun.
        E.g., "John Smith", "Mr. Smith", "John"

        Args:
            nouns: List of proper nouns

        Returns:
            List with variants populated
        """
        # Group by potential same entity
        for i, noun1 in enumerate(nouns):
            for j, noun2 in enumerate(nouns):
                if i >= j:
                    continue

                # Check if one contains the other
                text1_lower = noun1.text.lower()
                text2_lower = noun2.text.lower()

                # Skip if same text
                if text1_lower == text2_lower:
                    continue

                # Check containment
                if text1_lower in text2_lower:
                    if noun1.text not in noun2.variants:
                        noun2.variants.append(noun1.text)
                elif text2_lower in text1_lower:
                    if noun2.text not in noun1.variants:
                        noun1.variants.append(noun2.text)

                # Check for last name matching (English)
                if self.language == 'en':
                    words1 = noun1.text.split()
                    words2 = noun2.text.split()

                    # If last words match, might be same person
                    if len(words1) > 0 and len(words2) > 0:
                        if words1[-1].lower() == words2[-1].lower():
                            if noun1.type == noun2.type == ProperNounType.PERSON:
                                if noun1.text not in noun2.variants and noun1.text != noun2.text:
                                    noun2.variants.append(noun1.text)

        return nouns

    def add_translation(self, noun: ProperNoun, lang: str, translation: str) -> None:
        """Add a translation for a proper noun"""
        noun.translations[lang] = translation
