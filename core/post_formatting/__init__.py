"""
Phase 3.3 & 3.4 - Post-Formatting Module

Contains post-processing utilities for improving translated document quality.

Phase 3.3: Paragraph merging engine for book translation
Phase 3.4: Commercial ebook polish engine
"""

from core.post_formatting.paragraph_merger import (
    ParagraphMergeConfig,
    merge_paragraphs_for_book
)

from core.post_formatting.book_polisher import (
    BookPolisher,
    BookPolishConfig
)

__all__ = [
    'ParagraphMergeConfig',
    'merge_paragraphs_for_book',
    'BookPolisher',
    'BookPolishConfig'
]
