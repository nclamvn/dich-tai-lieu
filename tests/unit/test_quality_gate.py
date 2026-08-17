"""Tests for TIP-07: deterministic, dependency-free chunk quality gate.

Plain pytest functions (no plugins required). Run with:

    python3 -m pytest tests/unit/test_quality_gate.py -o addopts="" -q
"""

from core_v2.quality_gate import (
    DEFAULT_MIN_LENGTH_RATIO,
    LATEX_COMMANDS,
    check_chunk,
    count_inline_math,
    count_latex_commands,
    is_suspect,
)


# --------------------------------------------------------------------------- #
# empty / whitespace translation -> terminal ["empty"].
# --------------------------------------------------------------------------- #


def test_empty_translation_returns_only_empty():
    assert check_chunk("some real source text", "", "vi") == ["empty"]


def test_whitespace_translation_returns_only_empty():
    # Whitespace-only is terminal: no other check runs even when the source is
    # substantial and truncation is flagged.
    result = check_chunk("x" * 500, "   \n\t ", "vi", was_truncated=True)
    assert result == ["empty"]
    assert is_suspect("x" * 500, "  ", "vi") is True


# --------------------------------------------------------------------------- #
# error marker.
# --------------------------------------------------------------------------- #


def test_error_marker_detected():
    result = check_chunk("source", "partial [TRANSLATION ERROR: 3] output", "vi")
    assert "error_marker" in result


# --------------------------------------------------------------------------- #
# truncation flag.
# --------------------------------------------------------------------------- #


def test_truncated_flag_present():
    result = check_chunk("source", "a decent translation", "vi", was_truncated=True)
    assert "truncated" in result


# --------------------------------------------------------------------------- #
# too_short (dropped-content) heuristic.
# --------------------------------------------------------------------------- #


def test_too_short_when_source_substantial_and_translation_tiny():
    source = "a" * 300
    translated = "b" * 30  # ~10% of source length -> well below 0.30
    result = check_chunk(source, translated, "vi")
    assert "too_short" in result


def test_no_too_short_when_similar_length():
    source = "a" * 300
    translated = "b" * 300  # ratio 1.0
    result = check_chunk(source, translated, "vi")
    assert "too_short" not in result


def test_tiny_source_never_too_short():
    # Source under the 200-char floor: a very short translation must NOT flag.
    source = "Short source."  # < 200 chars
    translated = "x"
    result = check_chunk(source, translated, "vi")
    assert "too_short" not in result
    assert result == []


def test_too_short_respects_custom_min_length_ratio():
    source = "a" * 300
    translated = "b" * 120  # ratio 0.40
    # Default floor 0.30 -> not short; a stricter 0.50 floor -> short.
    assert "too_short" not in check_chunk(source, translated, "vi")
    assert "too_short" in check_chunk(
        source, translated, "vi", min_length_ratio=0.50
    )


# --------------------------------------------------------------------------- #
# wrong_language.
# --------------------------------------------------------------------------- #


def test_wrong_language_detected():
    result = check_chunk("source", "some english text", "vi", detected_lang="en")
    assert "wrong_language" in result


def test_no_wrong_language_when_detected_matches_target():
    result = check_chunk("source", "văn bản tiếng việt", "vi", detected_lang="vi")
    assert "wrong_language" not in result


def test_no_wrong_language_when_unknown_or_blank():
    assert "wrong_language" not in check_chunk(
        "source", "text", "vi", detected_lang="unknown"
    )
    assert "wrong_language" not in check_chunk(
        "source", "text", "vi", detected_lang=""
    )


def test_no_wrong_language_when_detection_absent():
    # detected_lang defaults to None -> the check is skipped entirely.
    assert "wrong_language" not in check_chunk("source", "text", "vi")


# --------------------------------------------------------------------------- #
# latex_lost.
# --------------------------------------------------------------------------- #


def test_latex_lost_when_formulas_dropped():
    source = "The value $a$ equals $b$ plus $c$ over $d$ exactly."  # 4 inline
    translated = "The value equals plus over exactly."  # 0 formulas
    result = check_chunk(source, translated, "vi", has_formulas=True)
    assert "latex_lost" in result


def test_no_latex_lost_when_formulas_preserved():
    source = "The value $a$ equals $b$ plus $c$ over $d$ exactly."
    translated = "Giá trị $a$ bằng $b$ cộng $c$ trên $d$ chính xác."  # all 4 kept
    result = check_chunk(source, translated, "vi", has_formulas=True)
    assert "latex_lost" not in result


def test_no_latex_lost_when_has_formulas_false():
    # Even with every formula dropped, the check is off unless has_formulas.
    source = "The value $a$ equals $b$ plus $c$ over $d$ exactly."
    translated = "The value equals plus over exactly."
    result = check_chunk(source, translated, "vi", has_formulas=False)
    assert "latex_lost" not in result


def test_latex_lost_via_dropped_commands():
    source = r"Consider $$\sum_{i} x_i$$ and \frac{a}{b} and \int f."
    translated = "Consider the sum and the fraction and the integral."
    result = check_chunk(source, translated, "vi", has_formulas=True)
    assert "latex_lost" in result
    # latex_lost must be reported at most once even when both sub-checks fire.
    assert result.count("latex_lost") == 1


# --------------------------------------------------------------------------- #
# count_inline_math / count_latex_commands.
# --------------------------------------------------------------------------- #


def test_count_inline_math_no_double_count():
    # Two inline ($a$, $c$) + one display ($$b$$) = 3, not 4.
    assert count_inline_math("$a$ and $$b$$ and $c$") == 3


def test_count_inline_math_edges():
    assert count_inline_math("") == 0
    assert count_inline_math("no math here at all") == 0
    assert count_inline_math("$$x$$") == 1  # single display, not two inline
    assert count_inline_math("$x$") == 1


def test_count_latex_commands_sums_occurrences():
    text = r"\sum here \frac there \sum again \begin{eq}\end{eq}"
    # \sum x2, \frac x1, \begin x1, \end x1 = 5
    assert count_latex_commands(text) == 5
    assert count_latex_commands("") == 0
    assert count_latex_commands("plain prose") == 0


# --------------------------------------------------------------------------- #
# clean chunk + is_suspect.
# --------------------------------------------------------------------------- #


def test_clean_chunk_has_no_issues():
    source = (
        "This is a sufficiently long source paragraph describing a method, "
        "well over two hundred characters so the length ratio check activates, "
        "and it carries two formulas $x$ and $y$ that the translation keeps."
    )
    translated = (
        "Đây là một đoạn nguồn đủ dài mô tả một phương pháp, vượt quá hai trăm "
        "ký tự để phép kiểm tỷ lệ độ dài kích hoạt, và nó mang hai công thức "
        "$x$ và $y$ mà bản dịch giữ lại đầy đủ."
    )
    result = check_chunk(
        source,
        translated,
        "vi",
        detected_lang="vi",
        was_truncated=False,
        has_formulas=True,
    )
    assert result == []
    assert is_suspect(source, translated, "vi", detected_lang="vi", has_formulas=True) is False


def test_is_suspect_true_when_flagged():
    assert is_suspect("source", "", "vi") is True
    assert is_suspect("source", "text", "vi", detected_lang="fr") is True


# --------------------------------------------------------------------------- #
# module constants sanity.
# --------------------------------------------------------------------------- #


def test_module_constants():
    assert DEFAULT_MIN_LENGTH_RATIO == 0.30
    assert "\\sum" in LATEX_COMMANDS
    assert "\\mathcal" in LATEX_COMMANDS
