"""
Unit tests for core_v2/token_chunking.py.

Plain pytest functions (no async). Run with:
    python3 -m pytest tests/unit/test_token_chunking.py -o addopts="" -q
"""

from core_v2.token_chunking import (
    chunk_text_by_tokens,
    estimate_tokens,
    pack_blocks,
    split_into_blocks,
    split_oversized_block,
)


# --------------------------------------------------------------------------- #
# estimate_tokens
# --------------------------------------------------------------------------- #
def test_estimate_tokens_empty_is_zero():
    assert estimate_tokens("") == 0
    assert estimate_tokens("   ") == 0
    assert estimate_tokens("\n\t  \n") == 0


def test_estimate_tokens_monotonic_non_decreasing():
    base = "The quick brown fox jumps over the lazy dog repeatedly."
    prev = 0
    for i in range(len(base) + 1):
        cur = estimate_tokens(base[:i])
        assert cur >= prev
        prev = cur


def test_estimate_tokens_cjk_more_than_same_length_ascii():
    cjk = "中" * 6  # 6 CJK chars -> 6 tokens
    ascii_ = "a" * 6  # ceil(6 / 3.5) = 2 tokens
    assert len(cjk) == len(ascii_)
    assert estimate_tokens(cjk) > estimate_tokens(ascii_)


def test_estimate_tokens_covers_hiragana_katakana_hangul():
    # One character each from the non-ideograph CJK ranges -> 1 token each.
    assert estimate_tokens("中") == 1  # CJK ideograph
    assert estimate_tokens("あ") == 1  # hiragana U+3042
    assert estimate_tokens("カ") == 1  # katakana U+30AB
    assert estimate_tokens("가") == 1  # hangul U+AC00


def test_estimate_tokens_100_char_ascii_is_roughly_len_over_ratio():
    est = estimate_tokens("A" * 100)
    # ceil(100 / 3.5) == 29; allow a small tolerance around len/3.5.
    assert est == 29
    assert abs(est - (100 / 3.5)) <= 3


# --------------------------------------------------------------------------- #
# split_into_blocks
# --------------------------------------------------------------------------- #
def test_split_into_blocks_basic():
    assert split_into_blocks("A\n\nB\n\nC") == ["A", "B", "C"]


def test_split_into_blocks_preserves_internal_single_newline():
    blocks = split_into_blocks("line1\nline2")
    assert blocks == ["line1\nline2"]
    assert "\n" in blocks[0]


def test_split_into_blocks_drops_leading_and_trailing_blank_lines():
    assert split_into_blocks("\n\nA\n\n") == ["A"]
    assert split_into_blocks("\n  \n  A \n \n") == ["A"]


def test_split_into_blocks_preserves_multiline_latex():
    latex = "$$\n\\sum x\n$$"
    blocks = split_into_blocks(latex)
    assert blocks == [latex]
    assert blocks[0].count("\n") == 2


def test_split_into_blocks_empty_input():
    assert split_into_blocks("") == []
    assert split_into_blocks("   \n \n ") == []


# --------------------------------------------------------------------------- #
# split_oversized_block
# --------------------------------------------------------------------------- #
def test_split_oversized_block_under_budget_returns_unchanged():
    block = "short text that easily fits"
    assert split_oversized_block(block, 1000) == [block]


def test_split_oversized_block_multiline_each_piece_within_budget():
    block = "\n".join(f"line number {i} carrying several words here" for i in range(200))
    max_tokens = 50
    pieces = split_oversized_block(block, max_tokens)
    assert len(pieces) > 1
    for piece in pieces:
        assert estimate_tokens(piece) <= max_tokens
    # No word is lost across the split.
    assert sum(len(p.split()) for p in pieces) == len(block.split())


def test_split_oversized_block_single_line_splits_on_words_without_loss():
    block = " ".join(f"word{i}" for i in range(500))  # one line, no sentences
    max_tokens = 30
    pieces = split_oversized_block(block, max_tokens)
    assert len(pieces) > 1
    for piece in pieces:
        assert estimate_tokens(piece) <= max_tokens
    flattened = []
    for piece in pieces:
        flattened.extend(piece.split())
    assert flattened == block.split()  # every word preserved, in order


def test_split_oversized_block_indivisible_token_falls_back_to_chars():
    block = "x" * 5000  # a single "word" with no whitespace at all
    max_tokens = 40
    pieces = split_oversized_block(block, max_tokens)
    assert len(pieces) > 1
    for piece in pieces:
        assert estimate_tokens(piece) <= max_tokens
    assert "".join(pieces) == block  # char slicing preserves content exactly


# --------------------------------------------------------------------------- #
# pack_blocks
# --------------------------------------------------------------------------- #
def test_pack_blocks_packs_many_small_blocks_into_fewer_chunks():
    blocks = [f"block number {i}" for i in range(50)]
    max_tokens = 200
    chunks = pack_blocks(blocks, max_tokens)
    assert len(chunks) < len(blocks)
    for chunk in chunks:
        assert chunk.strip() != ""  # never an empty chunk
        assert estimate_tokens(chunk) <= max_tokens


def test_pack_blocks_giant_block_never_exceeds_budget():
    giant = " ".join("word" for _ in range(2000))
    max_tokens = 100
    chunks = pack_blocks([giant], max_tokens)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert estimate_tokens(chunk) <= max_tokens


def test_pack_blocks_empty_input_returns_empty():
    assert pack_blocks([], 100) == []
    assert pack_blocks(["", "   "], 100) == []


# --------------------------------------------------------------------------- #
# chunk_text_by_tokens
# --------------------------------------------------------------------------- #
def test_chunk_text_by_tokens_preserves_structure_single_chunk():
    text = "para one\n\npara two"
    chunks = chunk_text_by_tokens(text, max_tokens=1000)
    assert chunks == ["para one\n\npara two"]


def test_chunk_text_by_tokens_long_blob_splits_within_budget():
    blob = " ".join(f"w{i}" for i in range(400))
    max_tokens = 40
    chunks = chunk_text_by_tokens(blob, max_tokens)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert estimate_tokens(chunk) <= max_tokens
    # Total word count preserved.
    total_words = sum(len(c.split()) for c in chunks)
    assert total_words == 400


def test_chunk_text_by_tokens_empty_returns_empty():
    assert chunk_text_by_tokens("", 100) == []
    assert chunk_text_by_tokens("   \n  \n", 100) == []


def test_chunk_text_by_tokens_no_blank_lines_single_block():
    # A single short line (no blank lines) still yields exactly one chunk.
    assert chunk_text_by_tokens("just one line here", 1000) == ["just one line here"]


def test_chunk_text_by_tokens_critical_preservation_3000_words():
    text = "word " * 3000  # one physical line, 3000 whitespace-separated words
    max_tokens = 200
    chunks = chunk_text_by_tokens(text, max_tokens)

    # No word lost and no whitespace-normalization catastrophe.
    all_words = []
    for chunk in chunks:
        all_words.extend(chunk.split())
    assert len(all_words) == 3000
    assert all(w == "word" for w in all_words)

    # Budget guarantee holds for every chunk.
    for chunk in chunks:
        assert estimate_tokens(chunk) <= max_tokens
