"""
Phase 3.3 - Book Paragraph Merging Engine

Intelligently merges paragraphs that were artificially split mid-sentence
during PDF-to-text conversion. Uses heuristic-based approach with safety-first
philosophy: only merge when confident.

Architecture:
    - Config-driven design with ParagraphMergeConfig
    - Helper functions for detecting sentence endings, headings, etc.
    - Main API: merge_paragraphs_for_book(paragraphs, config) -> List[str]

Integration:
    - Called in batch_processor.py BEFORE extract_semantic_structure()
    - Only active when layout_mode == 'book'
    - Never touches STEM/academic pipeline

Safety Philosophy:
    - "An toàn > hung hãn" (Safe > Aggressive)
    - Comprehensive NO MERGE rules have priority over MERGE rules
    - When in doubt, DON'T merge
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class ParagraphMergeConfig:
    """
    Configuration for paragraph merging behavior.

    Phase 3.3: Tunable parameters for controlling merge aggressiveness.

    Attributes:
        max_merged_length: Maximum length (chars) of merged paragraph
        soft_length_threshold: If paragraph < this, more willing to merge
        hard_end_punctuations: Strong sentence endings (never merge)
        soft_end_punctuations: Weak endings (may merge if continuation clear)
        min_paragraph_length: Don't merge very short paragraphs (likely intentional)
    """
    # Length controls
    max_merged_length: int = 800  # Don't create paragraphs longer than this
    soft_length_threshold: int = 600  # Below this, more willing to merge
    min_paragraph_length: int = 15  # Very short paragraphs likely intentional

    # Punctuation rules
    hard_end_punctuations: tuple = ('.', '!', '?', '。', '！', '？')  # Strong endings
    soft_end_punctuations: tuple = (',', ';', ':', '—', '–', '...', '，', '；', '：', '…')  # Weak endings (added Chinese ,;: and ellipsis)

    # Detection thresholds
    max_heading_length: int = 150  # Headings usually shorter than this
    scene_break_patterns: tuple = ('***', '* * *', '---', '- - -', '•••', '• • •')


def merge_paragraphs_for_book(
    paragraphs: List[str],
    config: Optional[ParagraphMergeConfig] = None
) -> List[str]:
    """
    Merge paragraphs that were artificially split mid-sentence during PDF conversion.

    Phase 3.3: Heuristic-based merging with safety-first approach.
    Only merges when confident that paragraphs belong together.

    Args:
        paragraphs: List of paragraph strings (from final_text.split('\\n'))
        config: Optional ParagraphMergeConfig (uses defaults if None)

    Returns:
        List of merged paragraphs (same or shorter than input list)

    Example:
        >>> paragraphs = [
        ...     "This is a sentence that got",
        ...     "split across two lines by PDF conversion.",
        ...     "This is a new paragraph."
        ... ]
        >>> merged = merge_paragraphs_for_book(paragraphs)
        >>> len(merged)
        2
        >>> merged[0]
        'This is a sentence that got split across two lines by PDF conversion.'

    Safety:
        - Idempotent: Running twice produces same result
        - Conservative: When in doubt, DON'T merge
        - Preserves semantic structure (headings, scene breaks, dialogue)
    """
    if not paragraphs:
        return []

    if config is None:
        config = ParagraphMergeConfig()

    merged: List[str] = []
    i = 0

    while i < len(paragraphs):
        current = paragraphs[i]

        # Start with current paragraph
        merged_text = current

        # Look ahead to see if we should merge with next paragraph(s)
        j = i + 1
        while j < len(paragraphs):
            next_para = paragraphs[j]

            # Safety check: Should we merge current with next?
            if _should_merge(merged_text, next_para, config):
                # Merge with space separator
                merged_text = merged_text + " " + next_para
                j += 1
            else:
                # Stop merging
                break

        # Add the merged result
        merged.append(merged_text)

        # Move to next unprocessed paragraph
        i = j

    return merged


def _should_merge(current: str, next_para: str, config: ParagraphMergeConfig) -> bool:
    """
    Determine if current paragraph should be merged with next paragraph.

    Safety-first approach: NO MERGE rules have priority over MERGE rules.

    Args:
        current: Current paragraph (possibly already merged)
        next_para: Next paragraph to consider merging
        config: Merge configuration

    Returns:
        True if safe to merge, False otherwise
    """
    # ===========================
    # ABSOLUTE NO MERGE RULES
    # (Safety > Aggressiveness)
    # ===========================

    # Rule 0a: Don't merge if CURRENT is a heading (BUG FIX: was only checking next)
    if _looks_like_heading(current, config):
        return False

    # Rule 0b: Don't merge if CURRENT is a list item (BUG FIX: was only checking next)
    if _looks_like_list_item(current):
        return False

    # Rule 0c: Don't merge if CURRENT is dialogue (BUG FIX: was only checking next)
    if _looks_like_dialogue(current):
        return False

    # Rule 1: Don't merge if result would be too long
    if len(current) + len(next_para) + 1 > config.max_merged_length:
        return False

    # Rule 2: Don't merge if current ends with hard punctuation
    if _looks_like_sentence_end(current, config):
        return False

    # Rule 3: Don't merge if next looks like a heading
    if _looks_like_heading(next_para, config):
        return False

    # Rule 4: Don't merge if next looks like a scene break
    if _looks_like_scene_break(next_para, config):
        return False

    # Rule 5: Don't merge if next looks like dialogue
    if _looks_like_dialogue(next_para):
        return False

    # Rule 6: Don't merge if next looks like a list item
    if _looks_like_list_item(next_para):
        return False

    # Rule 7: Don't merge if next paragraph starts with strong indicator
    if _starts_with_strong_indicator(next_para):
        return False

    # Rule 8: Don't merge very short paragraphs (likely intentional)
    if len(next_para) < config.min_paragraph_length:
        return False

    # ===========================
    # CONDITIONAL MERGE RULES
    # (Only if all NO MERGE rules passed)
    # ===========================

    # Rule M1: Merge if current ends mid-sentence (soft punctuation or lowercase)
    if _looks_like_continuation(current, next_para, config):
        return True

    # Rule M2: Merge if next starts with lowercase (clear continuation)
    if next_para and next_para[0].islower():
        return True

    # Default: Don't merge (conservative)
    return False


def _looks_like_sentence_end(text: str, config: ParagraphMergeConfig) -> bool:
    """
    Check if text ends with strong sentence-ending punctuation.

    Args:
        text: Text to check
        config: Configuration with hard_end_punctuations

    Returns:
        True if text ends with hard punctuation (., !, ?, etc.)
    """
    text = text.rstrip()
    if not text:
        return False

    # BUGFIX: Check for ellipsis patterns FIRST (before checking for period)
    # "..." or "…" should be treated as soft ending, not hard ending
    if text.endswith('...') or text.endswith('…'):
        return False

    # Check for hard punctuation
    for punct in config.hard_end_punctuations:
        if text.endswith(punct):
            return True

    return False


def _looks_like_continuation(current: str, next_para: str, config: ParagraphMergeConfig) -> bool:
    """
    Check if current paragraph looks like it continues into next paragraph.

    Indicators:
        - Ends with soft punctuation (comma, semicolon, dash, ellipsis)
        - Next starts with lowercase (clear continuation)

    Args:
        current: Current paragraph
        next_para: Next paragraph
        config: Configuration

    Returns:
        True if current appears to continue into next
    """
    current = current.rstrip()
    next_para = next_para.lstrip()

    if not current or not next_para:
        return False

    # Check if ends with soft punctuation
    for punct in config.soft_end_punctuations:
        if current.endswith(punct):
            return True

    # BUGFIX: Removed "current[-1].islower()" check - too broad!
    # It was matching ALL normal words (e.g., "Begins", "started", "wrote")
    # and causing false positives. Mid-word breaks should end with hyphen or
    # soft punctuation, which is already checked above.

    # Check if next starts with lowercase (clear continuation)
    if next_para[0].islower():
        return True

    return False


def _looks_like_heading(para: str, config: ParagraphMergeConfig) -> bool:
    """
    Check if paragraph looks like a heading.

    Indicators:
        - Short length (< max_heading_length)
        - Starts with "Chapter", "Section", "Part", etc.
        - All caps
        - No ending punctuation

    Args:
        para: Paragraph to check
        config: Configuration

    Returns:
        True if paragraph looks like a heading
    """
    para = para.strip()

    # Check length
    if len(para) > config.max_heading_length:
        return False

    # Check for heading keywords (case-insensitive)
    heading_keywords = [
        'chapter', 'section', 'part', 'book',
        'chương', 'phần', 'mục',  # Vietnamese
        'prologue', 'epilogue', 'preface', 'introduction',
        'acknowledgments', 'appendix', 'glossary', 'index'
    ]

    para_lower = para.lower()
    for keyword in heading_keywords:
        if para_lower.startswith(keyword):
            return True

    # Check if all caps (excluding spaces and punctuation)
    letters = [c for c in para if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return True

    # REMOVED: Overly aggressive "short + no punctuation = heading" check
    # This was causing idempotency violations where "Introduction" would be
    # detected as heading, but "Introduction [merged text]." would not be.
    # Now we only trust keyword matching and ALL CAPS detection.

    return False


def _looks_like_scene_break(para: str, config: ParagraphMergeConfig) -> bool:
    """
    Check if paragraph looks like a scene break.

    Scene breaks: ***, ---, • • •, etc.

    Args:
        para: Paragraph to check
        config: Configuration with scene_break_patterns

    Returns:
        True if paragraph looks like a scene break
    """
    para = para.strip()

    # Check against known patterns
    for pattern in config.scene_break_patterns:
        if para == pattern:
            return True

    # Check for patterns with only special characters and spaces
    # Example: "* * * * *", "- - - - -"
    if len(para) < 30:  # Scene breaks are short
        # Remove spaces
        no_spaces = para.replace(' ', '')
        # Check if all same character and special
        if no_spaces and len(set(no_spaces)) == 1 and not no_spaces[0].isalnum():
            return True

    return False


def _looks_like_dialogue(para: str) -> bool:
    """
    Check if paragraph looks like dialogue.

    Indicators:
        - Starts with quotation mark ("', ", «, etc.)
        - Starts with dash (—, –) indicating dialogue

    Args:
        para: Paragraph to check

    Returns:
        True if paragraph looks like dialogue
    """
    para = para.lstrip()
    if not para:
        return False

    # Check for quotation marks
    quote_marks = ('"', "'", '"', '"', '«', '»', '「', '」')
    if para[0] in quote_marks:
        return True

    # Check for dialogue dash
    if para.startswith('—') or para.startswith('–'):
        return True

    return False


def _looks_like_list_item(para: str) -> bool:
    """
    Check if paragraph looks like a list item.

    Indicators:
        - Starts with bullet point (•, -, *, etc.)
        - Starts with number followed by period or parenthesis (1., a), etc.)

    Args:
        para: Paragraph to check

    Returns:
        True if paragraph looks like a list item
    """
    para = para.lstrip()
    if not para:
        return False

    # Check for bullet points
    bullets = ('•', '◦', '▪', '▫', '–', '—', '-', '*')
    for bullet in bullets:
        if para.startswith(bullet + ' '):
            return True

    # Check for numbered list (e.g., "1.", "a)", "i.", etc.)
    # Pattern: optional letter/number + . or )
    list_pattern = re.match(r'^[a-zA-Z0-9ivxIVX]+[.)]\s', para)
    if list_pattern:
        return True

    return False


def _starts_with_strong_indicator(para: str) -> bool:
    """
    Check if paragraph starts with strong indicator of new section.

    Indicators:
        - Time/date markers ("The next day", "Years later", etc.)
        - Location markers ("Meanwhile", "Elsewhere", etc.)
        - Transition words indicating new section

    Args:
        para: Paragraph to check

    Returns:
        True if paragraph starts with strong new-section indicator
    """
    para = para.lstrip()
    if not para:
        return False

    para_lower = para.lower()

    # Time/transition markers
    transition_markers = [
        'meanwhile', 'elsewhere', 'later', 'the next day', 'years later',
        'months later', 'hours later', 'suddenly', 'then', 'now',
        'in the meantime', 'at that moment', 'at the same time'
    ]

    for marker in transition_markers:
        if para_lower.startswith(marker):
            return True

    return False
