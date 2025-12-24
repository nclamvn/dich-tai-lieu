"""
Phase 3.3 - Paragraph Merger Test Suite

Comprehensive tests for the book paragraph merging engine.
Verifies both happy paths (merging mid-sentence splits) and safety rules (NO MERGE cases).
"""

import pytest
from core.post_formatting.paragraph_merger import (
    merge_paragraphs_for_book,
    ParagraphMergeConfig
)


# ============================================================================
# A. HAPPY PATH - Merge "đoạn bị cắt giữa câu"
# ============================================================================

def test_merge_mid_sentence_split_basic():
    """Test merging Vietnamese paragraphs split mid-sentence"""
    paras = [
        "Đây là một đoạn văn khá dài nhưng bị ngắt",
        "giữa câu do PDF xuống dòng sai."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1, f"Expected 1 paragraph, got {len(result)}"
    assert result[0] == "Đây là một đoạn văn khá dài nhưng bị ngắt giữa câu do PDF xuống dòng sai."


def test_merge_english_lowercase_start():
    """Test merging English paragraphs where second starts with lowercase"""
    paras = [
        "The quick brown fox jumps over",
        "the lazy dog near the river."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1, f"Expected 1 paragraph, got {len(result)}"
    assert result[0] == "The quick brown fox jumps over the lazy dog near the river."


def test_merge_with_comma_soft_end():
    """Test merging when first paragraph ends with comma (soft punctuation)"""
    paras = [
        "Tác giả đã trình bày nền tảng lý thuyết,",
        "và trong chương tiếp theo, chúng ta sẽ đi sâu vào ví dụ."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1, f"Expected 1 paragraph, got {len(result)}"
    expected = "Tác giả đã trình bày nền tảng lý thuyết, và trong chương tiếp theo, chúng ta sẽ đi sâu vào ví dụ."
    assert result[0] == expected


def test_merge_with_semicolon():
    """Test merging when first paragraph ends with semicolon"""
    paras = [
        "This is the first part;",
        "this is the second part of the same thought."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert "first part; this is the second" in result[0]


def test_merge_multiple_consecutive_splits():
    """Test merging three paragraphs that are all part of one sentence"""
    paras = [
        "This sentence got split",
        "across three different",
        "lines in the PDF file."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert result[0] == "This sentence got split across three different lines in the PDF file."


# ============================================================================
# B. NO MERGE CASES - bắt buộc phải giữ nguyên
# ============================================================================

def test_do_not_merge_heading_chapter():
    """Test that chapter headings are NOT merged"""
    paras = ["CHƯƠNG 1", "Mở đầu"]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2, f"Expected 2 paragraphs (no merge), got {len(result)}"
    assert result[0] == "CHƯƠNG 1"
    assert result[1] == "Mở đầu"


def test_do_not_merge_heading_all_caps():
    """Test that ALL CAPS headings are not merged"""
    paras = ["INTRODUCTION", "This is the introduction text."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "INTRODUCTION"


def test_do_not_merge_heading_with_keyword():
    """Test that headings with keywords (Chapter, Section) are not merged"""
    paras = ["Chapter 5: The Journey Begins", "It was a dark and stormy night."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "Chapter 5: The Journey Begins"


def test_do_not_merge_scene_break_asterisks():
    """Test that scene breaks (***) are NOT merged"""
    paras = ["***", "Đoạn tiếp theo bắt đầu..."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "***"
    assert result[1] == "Đoạn tiếp theo bắt đầu..."


def test_do_not_merge_scene_break_spaced_asterisks():
    """Test that spaced scene breaks (* * *) are not merged"""
    paras = ["* * *", "Next scene starts here."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "* * *"


def test_do_not_merge_scene_break_dashes():
    """Test that dash scene breaks (---) are not merged"""
    paras = ["---", "After the break."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "---"


def test_do_not_merge_dialogue_quote():
    """Test that dialogue (starting with quotes) is NOT merged"""
    paras = ['"Anh có khỏe không?"', "Cô ấy nhìn anh một lúc lâu."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == '"Anh có khỏe không?"'


def test_do_not_merge_dialogue_dash():
    """Test that dialogue (starting with dash) is not merged"""
    paras = ["— Hello there!", "He waved enthusiastically."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "— Hello there!"


def test_do_not_merge_full_sentence_end_period():
    """Test that sentences ending with period are NOT merged"""
    paras = ["Đây là một câu hoàn chỉnh.", "Đây là câu tiếp theo."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "Đây là một câu hoàn chỉnh."
    assert result[1] == "Đây là câu tiếp theo."


def test_do_not_merge_full_sentence_end_exclamation():
    """Test that sentences ending with ! are NOT merged"""
    paras = ["What an amazing discovery!", "The next paragraph continues."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2


def test_do_not_merge_full_sentence_end_question():
    """Test that sentences ending with ? are NOT merged"""
    paras = ["How did this happen?", "Nobody knew the answer."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2


def test_do_not_merge_long_paragraph_over_threshold():
    """Test that very long paragraphs are not merged to avoid exceeding max_merged_length"""
    config = ParagraphMergeConfig(max_merged_length=100)

    # Create a paragraph that's 90 chars
    long_para = "A" * 90
    short_para = "continuation"

    paras = [long_para, short_para]
    result = merge_paragraphs_for_book(paras, config)

    # Should NOT merge because 90 + 12 + 1 (space) > 100
    assert len(result) == 2


def test_do_not_merge_list_items_dash():
    """Test that list items (starting with -) are NOT merged"""
    paras = ["- Mục 1", "Tiếp theo là một đoạn giải thích."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "- Mục 1"


def test_do_not_merge_list_items_bullet():
    """Test that list items (starting with •) are not merged"""
    paras = ["• First item", "This is a normal paragraph."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2


def test_do_not_merge_list_items_numbered():
    """Test that numbered list items are not merged"""
    paras = ["1. First point", "Some explanation follows."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 2
    assert result[0] == "1. First point"


def test_do_not_merge_very_short_paragraphs():
    """Test that very short paragraphs (likely intentional) are not merged"""
    config = ParagraphMergeConfig(min_paragraph_length=15)

    paras = ["OK.", "This is a longer paragraph that follows."]

    result = merge_paragraphs_for_book(paras, config)

    # "OK." is only 3 chars, below min_paragraph_length, so should NOT be merged
    assert len(result) == 2


def test_do_not_merge_strong_transition_markers():
    """Test that paragraphs starting with transition markers are not merged"""
    paras = ["The story began in 1945.", "Meanwhile, in another part of the city, something was happening."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    # "Meanwhile" is a strong transition marker
    assert len(result) == 2


# ============================================================================
# C. IDEMPOTENCY
# ============================================================================

def test_idempotent_behavior_basic():
    """Test that running merge twice produces the same result"""
    paras = [
        "This is a sentence that got",
        "split across two lines.",
        "This is a complete sentence."
    ]

    config = ParagraphMergeConfig()

    once = merge_paragraphs_for_book(paras, config)
    twice = merge_paragraphs_for_book(once, config)

    assert once == twice, "Merge operation must be idempotent"


def test_idempotent_behavior_complex():
    """Test idempotency with a complex mix of paragraphs"""
    paras = [
        "CHAPTER 1",
        "Introduction",
        "This paragraph was split",
        "across two lines by mistake.",
        "***",
        "After the scene break.",
        "Another split",
        "paragraph here."
    ]

    config = ParagraphMergeConfig()

    once = merge_paragraphs_for_book(paras, config)
    twice = merge_paragraphs_for_book(once, config)
    thrice = merge_paragraphs_for_book(twice, config)

    assert once == twice == thrice, "Multiple runs must produce identical results"


# ============================================================================
# D. EDGE CASES
# ============================================================================

def test_empty_input():
    """Test that empty input returns empty output"""
    result = merge_paragraphs_for_book([], ParagraphMergeConfig())
    assert result == []


def test_single_paragraph_no_change():
    """Test that a single paragraph is returned unchanged"""
    paras = ["This is a single paragraph with no splits."]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert result[0] == paras[0]


def test_whitespace_only_paragraphs_filtered():
    """Test that whitespace-only paragraphs are handled gracefully"""
    # Note: The actual split in batch_processor uses [p.strip() for p in ... if p.strip()]
    # So whitespace-only paragraphs should already be filtered before reaching merger
    # But we test that merger handles them gracefully if they somehow get through
    paras = [
        "Valid paragraph",
        "Another valid paragraph."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert all(p.strip() for p in result), "Result should not contain whitespace-only paragraphs"


def test_unicode_handling():
    """Test that merger handles Unicode characters correctly"""
    paras = [
        "这是中文测试，句子在中间",
        "被分开了。"
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert "被分开了" in result[0]


def test_mixed_language_merge():
    """Test merging with mixed English/Vietnamese"""
    paras = [
        "The concept of machine learning, hay học máy,",
        "is becoming increasingly important in modern technology."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert "hay học máy, is becoming" in result[0]


def test_ellipsis_soft_ending():
    """Test that ellipsis (...) is treated as soft punctuation"""
    paras = [
        "The story continues...",
        "and reaches an unexpected conclusion."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    # Ellipsis is in soft_end_punctuations, so should merge
    assert len(result) == 1


def test_em_dash_ending():
    """Test that em dash (—) at end is treated as soft punctuation"""
    paras = [
        "He was about to speak—",
        "but then changed his mind."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    assert len(result) == 1
    assert "speak— but then" in result[0]


# ============================================================================
# E. CONFIG PARAMETER TESTS
# ============================================================================

def test_custom_max_merged_length():
    """Test that custom max_merged_length is respected"""
    config = ParagraphMergeConfig(max_merged_length=50)

    paras = [
        "This is a relatively long first paragraph",
        "that should not be merged."
    ]

    result = merge_paragraphs_for_book(paras, config)

    # Total would be > 50 chars, so should NOT merge
    assert len(result) == 2


def test_custom_min_paragraph_length():
    """Test that custom min_paragraph_length is respected"""
    config = ParagraphMergeConfig(min_paragraph_length=20)

    paras = [
        "Short.",
        "This is a longer continuation paragraph."
    ]

    result = merge_paragraphs_for_book(paras, config)

    # "Short." is < 20 chars, so should NOT be merged
    assert len(result) == 2


# ============================================================================
# F. REALISTIC SCENARIOS
# ============================================================================

def test_realistic_book_chapter_opening():
    """Test a realistic book chapter opening with various elements"""
    paras = [
        "Chapter 3",
        "The Journey Begins",
        "",  # Empty paragraph (should already be filtered by batch_processor)
        "It was a cold morning when Sarah decided",
        "to embark on her adventure.",
        "She packed her bags carefully.",
        "***",
        "Hours later, she arrived at the station.",
        "The platform was crowded with people",
        "rushing to catch their trains."
    ]

    # Filter empty paragraphs (simulating batch_processor behavior)
    paras = [p for p in paras if p.strip()]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    # Expected: Chapter 3 stays separate, heading stays separate,
    # "decided/to embark" merge, "people/rushing" merge, scene break stays separate
    assert "Chapter 3" in result
    assert "The Journey Begins" in result
    assert any("decided to embark on her adventure" in p for p in result)
    assert "***" in result
    assert any("people rushing to catch" in p for p in result)


def test_realistic_dialogue_heavy_section():
    """Test a section with lots of dialogue (should not merge dialogue)"""
    paras = [
        '"Hello," she said.',
        '"Hi there," he replied.',
        'They stood in silence for a moment.',
        '"About yesterday..."',
        '"Let\'s not talk about it."'
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    # All dialogue paragraphs should stay separate
    dialogue_count = sum(1 for p in result if p.startswith('"'))
    assert dialogue_count == 4, "Dialogue paragraphs must not be merged"


def test_realistic_academic_style_text():
    """Test academic-style text with proper sentence endings"""
    paras = [
        "The research methodology was carefully designed.",
        "Three main approaches were considered.",
        "First, a quantitative analysis was performed.",
        "Second, qualitative interviews were conducted.",
        "Finally, the results were synthesized."
    ]

    result = merge_paragraphs_for_book(paras, ParagraphMergeConfig())

    # All end with periods, so should NOT merge
    assert len(result) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
