"""
Text Segmenter
Split text into translation units (sentences, paragraphs).
"""
import re
import logging
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SegmentType(str, Enum):
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SMART = "smart"


@dataclass
class Segment:
    """A text segment for translation."""
    index: int
    text: str
    start: int
    end: int
    word_count: int
    segment_type: SegmentType


class Segmenter:
    """
    Text segmenter for Translation Memory.

    Splits text into sentences or paragraphs for TM lookup/storage.
    """

    # Sentence-ending punctuation
    SENTENCE_ENDINGS = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z\u00C0-\u017F])|'  # Standard sentence end
        r'(?<=[.!?]["\'])\s+|'  # After closing quote
        r'(?<=\.\.\.)\s+(?=[A-Z])'  # After ellipsis
    )

    # Paragraph separator
    PARAGRAPH_SEP = re.compile(r'\n\s*\n')

    # Min/max segment lengths
    MIN_SEGMENT_WORDS = 3
    MAX_SEGMENT_WORDS = 100

    def __init__(
        self,
        segment_type: SegmentType = SegmentType.SENTENCE,
        min_words: int = 3,
        max_words: int = 100,
    ):
        """
        Initialize segmenter.

        Args:
            segment_type: Type of segmentation
            min_words: Minimum words per segment
            max_words: Maximum words per segment
        """
        self.segment_type = segment_type
        self.min_words = min_words
        self.max_words = max_words

    def segment(self, text: str) -> List[Segment]:
        """
        Split text into segments.

        Args:
            text: Text to segment

        Returns:
            List of Segment objects
        """
        if not text or not text.strip():
            return []

        if self.segment_type == SegmentType.SENTENCE:
            return self._segment_sentences(text)
        elif self.segment_type == SegmentType.PARAGRAPH:
            return self._segment_paragraphs(text)
        else:  # SMART
            return self._segment_smart(text)

    def _segment_sentences(self, text: str) -> List[Segment]:
        """Split text into sentences."""
        # Clean text
        text = text.strip()

        # Split by sentence endings
        sentences = self.SENTENCE_ENDINGS.split(text)

        segments = []
        pos = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            word_count = len(sentence.split())

            # Skip very short segments
            if word_count < self.min_words:
                # Merge with previous if possible
                if segments:
                    prev = segments[-1]
                    merged_text = prev.text + " " + sentence
                    segments[-1] = Segment(
                        index=prev.index,
                        text=merged_text,
                        start=prev.start,
                        end=pos + len(sentence),
                        word_count=len(merged_text.split()),
                        segment_type=SegmentType.SENTENCE,
                    )
                    pos += len(sentence) + 1
                    continue

            start = pos
            end = pos + len(sentence)

            segments.append(Segment(
                index=len(segments),
                text=sentence,
                start=start,
                end=end,
                word_count=word_count,
                segment_type=SegmentType.SENTENCE,
            ))

            pos = end + 1

        return segments

    def _segment_paragraphs(self, text: str) -> List[Segment]:
        """Split text into paragraphs."""
        # Split by double newlines
        paragraphs = self.PARAGRAPH_SEP.split(text)

        segments = []
        pos = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            word_count = len(para.split())

            # Skip very short paragraphs
            if word_count < self.min_words:
                if segments:
                    prev = segments[-1]
                    merged_text = prev.text + "\n\n" + para
                    segments[-1] = Segment(
                        index=prev.index,
                        text=merged_text,
                        start=prev.start,
                        end=pos + len(para),
                        word_count=len(merged_text.split()),
                        segment_type=SegmentType.PARAGRAPH,
                    )
                    pos += len(para) + 2
                    continue

            start = pos
            end = pos + len(para)

            segments.append(Segment(
                index=len(segments),
                text=para,
                start=start,
                end=end,
                word_count=word_count,
                segment_type=SegmentType.PARAGRAPH,
            ))

            pos = end + 2

        return segments

    def _segment_smart(self, text: str) -> List[Segment]:
        """
        Smart segmentation based on text structure.

        - Short text: sentence-based
        - Long text: paragraph-based with sentence fallback
        """
        word_count = len(text.split())

        # For short text, use sentences
        if word_count < 200:
            return self._segment_sentences(text)

        # For longer text, try paragraphs first
        paragraphs = self._segment_paragraphs(text)

        # If paragraphs are too long, split into sentences
        result = []
        for para in paragraphs:
            if para.word_count > self.max_words:
                # Split long paragraph into sentences
                sub_segments = self._segment_sentences(para.text)
                for seg in sub_segments:
                    seg.index = len(result)
                    result.append(seg)
            else:
                para.index = len(result)
                result.append(para)

        return result

    def merge_short_segments(
        self,
        segments: List[Segment],
        min_words: Optional[int] = None,
    ) -> List[Segment]:
        """
        Merge segments that are too short.

        Args:
            segments: List of segments
            min_words: Minimum words (uses self.min_words if None)

        Returns:
            Merged segments
        """
        min_words = min_words or self.min_words

        if not segments:
            return []

        merged = []
        current = segments[0]

        for seg in segments[1:]:
            if current.word_count < min_words:
                # Merge with next
                merged_text = current.text + " " + seg.text
                current = Segment(
                    index=current.index,
                    text=merged_text,
                    start=current.start,
                    end=seg.end,
                    word_count=len(merged_text.split()),
                    segment_type=current.segment_type,
                )
            else:
                merged.append(current)
                current = Segment(
                    index=len(merged),
                    text=seg.text,
                    start=seg.start,
                    end=seg.end,
                    word_count=seg.word_count,
                    segment_type=seg.segment_type,
                )

        merged.append(current)
        return merged


# Global instance
_segmenter: Optional[Segmenter] = None


def get_segmenter(segment_type: SegmentType = SegmentType.SENTENCE) -> Segmenter:
    """Get segmenter instance."""
    global _segmenter
    if _segmenter is None or _segmenter.segment_type != segment_type:
        _segmenter = Segmenter(segment_type=segment_type)
    return _segmenter
