"""
Text Segmentation Module

Provides language-specific text segmentation for accurate
word counting and semantic chunking.
"""

from .japanese_segmenter import (
    JapaneseSegmenter,
    segment_japanese,
    count_japanese_words,
    get_japanese_reading,
)

__all__ = [
    'JapaneseSegmenter',
    'segment_japanese',
    'count_japanese_words',
    'get_japanese_reading',
]
