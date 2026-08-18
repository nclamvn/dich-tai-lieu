#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for :mod:`core_v2.context_builder`.

Covers the deterministic, LLM-free rolling cross-chunk context builder:
sentence splitting, leading/trailing sentence windows, the rolling gist, and the
per-chunk ``(preceding, following)`` assembly (older-context gist + exact tail of
the immediate predecessor, with no duplication).

Plain pytest functions (no classes / fixtures); run with::

    python3 -m pytest tests/unit/test_context_builder.py -o addopts="" -q
"""

from core_v2.context_builder import (
    build_chunk_contexts,
    build_running_gist,
    first_sentences,
    last_sentences,
    split_sentences,
)


# --------------------------------------------------------------------------- #
# split_sentences
# --------------------------------------------------------------------------- #
def test_split_sentences_basic():
    assert split_sentences("A. B! C?") == ["A.", "B!", "C?"]


def test_split_sentences_cjk_boundaries():
    # Full-width CJK punctuation followed by whitespace is a boundary too.
    assert split_sentences("甲。 乙！ 丙？") == ["甲。", "乙！", "丙？"]


def test_split_sentences_no_boundary_returns_whole():
    assert split_sentences("hello world no punctuation") == [
        "hello world no punctuation"
    ]


def test_split_sentences_preserves_internal_spaces():
    # Only outer whitespace is stripped; internal spacing is preserved verbatim.
    assert split_sentences("foo   bar baz") == ["foo   bar baz"]


def test_split_sentences_empty_and_whitespace():
    assert split_sentences("") == []
    assert split_sentences("   \n\t ") == []


# --------------------------------------------------------------------------- #
# last_sentences — returns the END, not the start
# --------------------------------------------------------------------------- #
def test_last_sentences_returns_tail_not_head():
    assert last_sentences("One. Two. Three.", max_sentences=1) == "Three."


def test_last_sentences_multiple():
    assert last_sentences("One. Two. Three.", max_sentences=2) == "Two. Three."


def test_last_sentences_char_cap_keeps_tail():
    text = "One. Two. Three. Four."
    # Cap smaller than the joined tail must keep the most recent characters.
    result = last_sentences(text, max_sentences=4, max_chars=10)
    assert len(result) <= 10
    assert result.endswith("Four.")
    assert "One." not in result


def test_last_sentences_empty():
    assert last_sentences("") == ""
    assert last_sentences("   ") == ""


# --------------------------------------------------------------------------- #
# first_sentences — returns the START
# --------------------------------------------------------------------------- #
def test_first_sentences_returns_head():
    assert first_sentences("One. Two. Three.", max_sentences=1) == "One."


def test_first_sentences_multiple():
    assert first_sentences("One. Two. Three.", max_sentences=2) == "One. Two."


def test_first_sentences_char_cap_keeps_start():
    result = first_sentences("One. Two. Three.", max_sentences=3, max_chars=4)
    assert len(result) <= 4
    assert result.startswith("One")


def test_first_sentences_empty():
    assert first_sentences("") == ""


# --------------------------------------------------------------------------- #
# build_running_gist
# --------------------------------------------------------------------------- #
def test_build_running_gist_joins_topics():
    assert build_running_gist(["Topic A.", "Topic B."]) == "Topic A. Topic B."


def test_build_running_gist_skips_empty_topics():
    assert build_running_gist(["", "  ", "Only one."]) == "Only one."


def test_build_running_gist_over_budget_keeps_recent_tail():
    topics = ["oldest", "middle", "newest"]
    result = build_running_gist(topics, max_chars=6)
    assert len(result) <= 6
    assert result.endswith("newest")
    assert "oldest" not in result


def test_build_running_gist_empty():
    assert build_running_gist([]) == ""
    assert build_running_gist(["", "   "]) == ""


# --------------------------------------------------------------------------- #
# build_chunk_contexts — core behaviours
# --------------------------------------------------------------------------- #
_THREE = ["Alpha one. Alpha two.", "Beta one. Beta two.", "Gamma one."]


def test_build_chunk_contexts_first_chunk_has_no_preceding():
    contexts = build_chunk_contexts(_THREE)
    assert contexts[0][0] == ""  # nothing precedes the first chunk
    assert "Beta" in contexts[0][1]  # following = head of chunk 1


def test_build_chunk_contexts_middle_uses_tail_of_previous():
    contexts = build_chunk_contexts(_THREE)
    preceding, following = contexts[1]
    # preceding is the TAIL (end) of chunk 0, not merely its opening word.
    assert "Alpha two." in preceding
    assert "Gamma" in following  # following = head of chunk 2


def test_build_chunk_contexts_last_gist_plus_tail_no_duplication():
    contexts = build_chunk_contexts(_THREE)
    preceding, following = contexts[2]
    # Immediate tail = end of chunk 1.
    assert "Beta two." in preceding
    # Gist part carries chunk 0's topic (window reaches back to it).
    gist_part, _, immediate_part = preceding.partition("\n")
    assert "Alpha" in gist_part
    # No duplication: the immediate tail must NOT also appear inside the gist.
    assert "Beta" not in gist_part
    assert preceding.count("Beta two.") == 1
    # Last chunk has no following.
    assert following == ""


def test_build_chunk_contexts_summaries_override_topic_sentence():
    summaries = ["s0", "s1", "s2"]
    contexts = build_chunk_contexts(_THREE, summaries=summaries)
    preceding = contexts[2][0]
    # Gist for chunk 2 uses the supplied summary of chunk 0 ("s0"), not its
    # topic sentence ("Alpha ...").
    gist_part, _, _ = preceding.partition("\n")
    assert "s0" in gist_part
    assert "Alpha" not in gist_part


def test_build_chunk_contexts_two_tiny_chunks():
    # Matches the existing semantic_chunker finalize-test expectations.
    contexts = build_chunk_contexts(["First chunk content", "Second chunk content"])
    assert "First" in contexts[1][0]  # preceding of chunk 1 = tail of chunk 0
    assert "Second" in contexts[0][1]  # following of chunk 0 = head of chunk 1
    assert contexts[0][0] == ""
    assert contexts[1][1] == ""


def test_build_chunk_contexts_single_chunk():
    assert build_chunk_contexts(["only chunk"]) == [("", "")]


def test_build_chunk_contexts_empty_input():
    assert build_chunk_contexts([]) == []


def test_build_chunk_contexts_length_matches_input():
    contexts = build_chunk_contexts(_THREE)
    assert len(contexts) == len(_THREE)
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in contexts)


def test_build_chunk_contexts_short_summaries_fall_back():
    # A summaries list shorter than contents must not raise; missing positions
    # fall back to the chunk's topic sentence.
    contexts = build_chunk_contexts(_THREE, summaries=["s0"])
    # Chunk 2's gist covers chunk 0 (has summary "s0") -> uses it.
    assert "s0" in contexts[2][0].partition("\n")[0]


def test_build_chunk_contexts_window_limits_gist_reach():
    # With window=1 the gist window [max(0, i-1), i-1) is always empty, so
    # preceding is exactly the immediate tail with no gist prefix / newline.
    contents = ["A one. A two.", "B one. B two.", "C one. C two.", "D one. D two."]
    contexts = build_chunk_contexts(contents, window=1)
    preceding = contexts[3][0]
    assert "\n" not in preceding
    assert preceding == last_sentences(contents[2], 2)
