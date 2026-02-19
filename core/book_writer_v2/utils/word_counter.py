"""
Word counting utilities.
"""

import re


def count_words(text: str) -> int:
    """Count words in text, handling edge cases."""
    if not text:
        return 0
    return len(text.split())


def estimate_pages(word_count: int, words_per_page: int = 300) -> int:
    """Estimate page count from word count."""
    if words_per_page <= 0:
        return 0
    return word_count // words_per_page


def count_unique_words(text: str) -> int:
    """Count unique words in text."""
    if not text:
        return 0
    words = re.findall(r'\b\w+\b', text.lower())
    return len(set(words))


def vocabulary_richness(text: str) -> float:
    """Calculate vocabulary richness (unique/total ratio)."""
    if not text:
        return 0.0
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 0.0
    return len(set(words)) / len(words)
