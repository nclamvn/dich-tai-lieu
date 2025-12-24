#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SmartMerger - Intelligent merging với overlap detection

FIX-002: Added fuzzy matching and overlap_char_count support
"""

import re
from typing import List
from difflib import SequenceMatcher


class SmartMerger:
    """Intelligent merging với overlap detection và fuzzy matching"""

    # FIX-002: Hệ số mở rộng cho tiếng Việt (dài hơn tiếng Anh ~20%)
    VIETNAMESE_EXPANSION_FACTOR = 1.2

    @staticmethod
    def find_overlap(text1: str, text2: str, min_overlap: int = 20) -> int:
        """Find overlap between end of text1 and start of text2 (exact match)"""
        max_check = min(len(text1), len(text2), 500)

        # Try word-level matching first
        words1 = text1.split()
        words2 = text2.split()

        for i in range(min(len(words1), len(words2), 50), 2, -1):
            if words1[-i:] == words2[:i]:
                # Found word-level match
                overlap_text = " ".join(words2[:i])
                return len(overlap_text)

        # Fallback to character-level
        for i in range(max_check, min_overlap, -1):
            if text1[-i:] == text2[:i]:
                return i

        return 0

    @staticmethod
    def find_overlap_fuzzy(text1: str, text2: str, min_match_size: int = 50) -> int:
        """
        FIX-002: Find overlap using fuzzy matching (SequenceMatcher).

        Dùng khi exact match thất bại (sau khi dịch, text có thể khác nhau).

        Args:
            text1: Text đầu tiên (merged so far)
            text2: Text tiếp theo (current chunk)
            min_match_size: Kích thước match tối thiểu để coi là overlap

        Returns:
            Số ký tự cần cắt từ đầu text2
        """
        # Lấy ~500 chars cuối của text1 và đầu của text2
        end_text1 = text1[-500:] if len(text1) > 500 else text1
        start_text2 = text2[:500] if len(text2) > 500 else text2

        # Tìm longest common substring
        matcher = SequenceMatcher(None, end_text1, start_text2)
        match = matcher.find_longest_match(0, len(end_text1), 0, len(start_text2))

        # Nếu có match đủ dài, tính overlap
        if match.size >= min_match_size:
            # match.b = vị trí bắt đầu match trong text2
            # match.size = độ dài match
            # Cắt bỏ từ đầu text2 đến hết phần match
            return match.b + match.size

        return 0

    @classmethod
    def merge_translations(cls, results: List['TranslationResult']) -> str:
        """
        Merge translated chunks intelligently.

        FIX-002: Sử dụng overlap_char_count nếu có, fallback sang fuzzy matching.

        Priority:
        1. overlap_char_count từ chunk metadata (tin cậy nhất)
        2. Exact match (find_overlap)
        3. Fuzzy match (find_overlap_fuzzy)
        4. No overlap - nối trực tiếp
        """
        if not results:
            return ""

        # Sort by chunk ID
        sorted_results = sorted(results, key=lambda x: x.chunk_id)

        # Start với chunk đầu tiên
        merged = sorted_results[0].translated.strip()

        for i in range(1, len(sorted_results)):
            result = sorted_results[i]
            current = result.translated.strip()

            if not current:
                continue

            overlap = 0

            # FIX-002: Priority 1 - Sử dụng overlap_char_count từ metadata
            if hasattr(result, 'overlap_char_count') and result.overlap_char_count > 0:
                # Ước tính overlap trong bản dịch (tiếng Việt dài hơn)
                estimated_overlap = int(result.overlap_char_count * cls.VIETNAMESE_EXPANSION_FACTOR)
                # Đảm bảo không cắt quá nhiều
                overlap = min(estimated_overlap, len(current) // 2)

            # Priority 2 - Exact match
            if overlap == 0:
                overlap = cls.find_overlap(merged, current)

            # Priority 3 - Fuzzy match
            if overlap == 0:
                overlap = cls.find_overlap_fuzzy(merged, current, min_match_size=30)

            # Merge với overlap
            if overlap > 20:
                merged = merged + current[overlap:]
            else:
                # No overlap found - nối với separator phù hợp
                if merged and current:
                    if merged[-1] in '.!?។។។' and current[0].isupper():
                        merged = merged + "\n\n" + current
                    else:
                        merged = merged + " " + current

        return cls.post_process(merged)

    @staticmethod
    def post_process(text: str) -> str:
        """Clean up merged text"""
        # Remove duplicate spaces
        text = re.sub(r' +', ' ', text)

        # Fix paragraph breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove translation artifacts
        text = re.sub(r'\[CHUNK \d+\]', '', text)
        text = re.sub(r'---START---|---END---', '', text)

        # Fix quotes
        text = re.sub(r'"\s*"', '"', text)

        return text.strip()
