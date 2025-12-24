"""
Japanese Word Segmentation Module

Provides morphological analysis for Japanese text using fugashi (MeCab wrapper).
Essential for:
- Accurate word counting (Japanese has no spaces)
- Semantic chunking for translation
- Text quality validation
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class JapaneseSegmenter:
    """
    Japanese morphological analyzer using MeCab/fugashi.

    Features:
    - Word segmentation (分かち書き)
    - Reading extraction (ふりがな/フリガナ)
    - Part-of-speech tagging
    - Word counting
    """

    _instance: Optional['JapaneseSegmenter'] = None
    _tagger = None

    def __new__(cls):
        """Singleton pattern - reuse tagger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._tagger is None:
            self._initialize_tagger()

    def _initialize_tagger(self):
        """Initialize MeCab tagger with unidic-lite dictionary."""
        try:
            import fugashi
            self._tagger = fugashi.Tagger()
            logger.info("Japanese segmenter initialized with fugashi/unidic-lite")
        except ImportError as e:
            logger.error(f"Failed to import fugashi: {e}")
            logger.error("Install with: pip install fugashi unidic-lite")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Japanese tagger: {e}")
            raise

    def segment(self, text: str) -> list[str]:
        """
        Segment Japanese text into words/morphemes.

        Args:
            text: Japanese text to segment

        Returns:
            List of words/morphemes

        Example:
            >>> seg = JapaneseSegmenter()
            >>> seg.segment("私は学生です")
            ['私', 'は', '学生', 'です']
        """
        if not text or not text.strip():
            return []

        return [word.surface for word in self._tagger(text)]

    def segment_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Segment text and return with part-of-speech tags.

        Args:
            text: Japanese text to segment

        Returns:
            List of (word, pos) tuples

        Example:
            >>> seg.segment_with_pos("私は学生です")
            [('私', '代名詞'), ('は', '助詞'), ('学生', '名詞'), ('です', '助動詞')]
        """
        if not text or not text.strip():
            return []

        result = []
        for word in self._tagger(text):
            pos = word.feature.pos1 if hasattr(word.feature, 'pos1') else 'Unknown'
            result.append((word.surface, pos))
        return result

    def get_readings(self, text: str) -> list[tuple[str, str]]:
        """
        Get words with their furigana readings.

        Args:
            text: Japanese text

        Returns:
            List of (surface, reading) tuples

        Example:
            >>> seg.get_readings("東京")
            [('東京', 'トウキョウ')]
        """
        if not text or not text.strip():
            return []

        result = []
        for word in self._tagger(text):
            reading = getattr(word.feature, 'kana', None) or word.surface
            result.append((word.surface, reading))
        return result

    def get_reading_string(self, text: str) -> str:
        """
        Get full reading (furigana) for text as a string.

        Args:
            text: Japanese text

        Returns:
            Reading in katakana
        """
        readings = self.get_readings(text)
        return ''.join(reading for _, reading in readings)

    def count_words(self, text: str) -> int:
        """
        Accurate word count for Japanese text.

        Unlike len(text) which counts characters,
        this counts actual words/morphemes.

        Args:
            text: Japanese text

        Returns:
            Number of words
        """
        return len(self.segment(text))

    def count_content_words(self, text: str) -> int:
        """
        Count content words (nouns, verbs, adjectives) excluding particles.

        Useful for semantic density analysis.
        """
        if not text or not text.strip():
            return 0

        content_pos = {'名詞', '動詞', '形容詞', '副詞'}
        count = 0
        for word in self._tagger(text):
            pos = getattr(word.feature, 'pos1', '')
            if pos in content_pos:
                count += 1
        return count

    def extract_nouns(self, text: str) -> list[str]:
        """
        Extract all nouns from text.

        Useful for keyword extraction and topic analysis.
        """
        if not text or not text.strip():
            return []

        nouns = []
        for word in self._tagger(text):
            pos = getattr(word.feature, 'pos1', '')
            if pos == '名詞':
                nouns.append(word.surface)
        return nouns

    def detect_formality(self, text: str) -> str:
        """
        Detect formality level of Japanese text.

        Returns:
            'formal' (です/ます form)
            'informal' (だ/である form)
            'mixed' (both present)
            'neutral' (cannot determine)
        """
        if not text or not text.strip():
            return 'neutral'

        formal_markers = 0
        informal_markers = 0

        for word in self._tagger(text):
            surface = word.surface
            # Check for formal endings
            if surface in ('です', 'ます', 'ました', 'ません', 'でした'):
                formal_markers += 1
            # Check for informal endings
            elif surface in ('だ', 'である', 'だった', 'だろう'):
                informal_markers += 1

        if formal_markers > 0 and informal_markers > 0:
            return 'mixed'
        elif formal_markers > 0:
            return 'formal'
        elif informal_markers > 0:
            return 'informal'
        return 'neutral'

    def split_sentences(self, text: str) -> list[str]:
        """
        Split Japanese text into sentences.

        Uses Japanese sentence-ending punctuation:
        。(period), ！(exclamation), ？(question)
        """
        import re

        if not text or not text.strip():
            return []

        # Split on Japanese sentence endings
        pattern = r'([。！？\!\?])'
        parts = re.split(pattern, text)

        sentences = []
        current = ''
        for part in parts:
            current += part
            if part in '。！？!?':
                if current.strip():
                    sentences.append(current.strip())
                current = ''

        # Add remaining text if any
        if current.strip():
            sentences.append(current.strip())

        return sentences


# Convenience functions
def segment_japanese(text: str) -> list[str]:
    """Convenience function for word segmentation."""
    return JapaneseSegmenter().segment(text)


def count_japanese_words(text: str) -> int:
    """Convenience function for word counting."""
    return JapaneseSegmenter().count_words(text)


def get_japanese_reading(text: str) -> str:
    """Convenience function for getting reading."""
    return JapaneseSegmenter().get_reading_string(text)
