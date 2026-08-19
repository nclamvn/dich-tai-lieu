"""Offline tests for evalkit scorers — no API key, no network."""

from evalkit.scorers import chrf, format_preservation, llm_judge, terminology


# --- chrF ------------------------------------------------------------------
def test_chrf_identical_is_high():
    r = chrf("Xin chào thế giới", "Xin chào thế giới")
    assert r.score is not None and r.score > 0.99


def test_chrf_no_reference_is_none():
    assert chrf("bất kỳ", None).score is None


def test_chrf_worse_translation_scores_lower():
    good = chrf("Xin chào thế giới", "Xin chào thế giới").score
    bad = chrf("Tạm biệt nhé", "Xin chào thế giới").score
    assert bad < good


# --- terminology -----------------------------------------------------------
def test_terminology_flags_missing_and_translated():
    r = terminology(
        "mạng nơ ron học rất tốt",  # hyphenated term absent; Transformer absent
        expect_terms=["mạng nơ-ron"],
        expect_no_translate=["Transformer"],
    )
    assert r.score is not None and r.score < 1.0
    kinds = {v["type"] for v in r.violations}
    assert "missing_term" in kinds and "should_not_translate" in kinds


def test_terminology_all_satisfied_is_one():
    r = terminology(
        "Chúng tôi dùng mô hình Transformer.",
        expect_terms=["mô hình"],
        expect_no_translate=["Transformer"],
    )
    assert r.score == 1.0 and r.violations == []


def test_terminology_no_constraints_is_none():
    assert terminology("bất kỳ").score is None


# --- format preservation ---------------------------------------------------
def test_format_same_structure_is_one():
    assert format_preservation("Line 1\nLine 2", "Dòng 1\nDòng 2").score == 1.0


def test_format_dropped_formula_scores_lower():
    src = "Loss $x=1$ here"
    kept = format_preservation("Mất mát $x=1$ ở đây", src).score
    dropped = format_preservation("Mất mát ở đây", src).score
    assert dropped < kept


# --- llm judge (mocked) ----------------------------------------------------
def test_llm_judge_none_without_fn():
    assert llm_judge("hyp", "src").score is None


def test_llm_judge_parses_full_marks():
    fn = lambda p: '{"adequacy":5,"fluency":5,"terminology":5,"format":5}'  # noqa: E731
    assert llm_judge("hyp", "src", judge_fn=fn).score == 1.0


def test_llm_judge_extracts_json_amid_prose():
    fn = lambda p: 'Sure: {"adequacy":4,"fluency":4,"terminology":5,"format":5} ok'  # noqa: E731
    r = llm_judge("hyp", "src", judge_fn=fn)
    assert r.score is not None and 0.0 < r.score <= 1.0


def test_llm_judge_fail_open_on_bad_output():
    fn = lambda p: "totally not json"  # noqa: E731
    r = llm_judge("hyp", "src", judge_fn=fn)
    assert r.score is None and "error" in r.detail
