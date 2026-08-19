"""Offline tests for the eval runner + regression gate — mock translator."""

from pathlib import Path

from evalkit.runner import (
    GoldenItem,
    compare_baseline,
    load_golden,
    run_eval,
    save_baseline,
)

ROOT = Path(__file__).resolve().parents[2]

GOLD = [
    GoldenItem(
        id="a",
        direction="en2vi",
        source="Hello world",
        reference="Xin chào thế giới",
        expect_terms=["Xin chào"],
    ),
    GoldenItem(id="b", direction="vi2en", source="Xin chào", reference="Hello"),
]

_PERFECT = {"Hello world": "Xin chào thế giới", "Xin chào": "Hello"}


def perfect_translate(source, direction):
    return _PERFECT[source]


def bad_translate(source, direction):
    return "xxx"


def test_run_eval_perfect_is_high():
    report = run_eval(GOLD, perfect_translate)
    assert report.overall() is not None and report.overall() > 0.8


def test_baseline_gate_detects_regression(tmp_path):
    good = run_eval(GOLD, perfect_translate)
    baseline = tmp_path / "baseline.json"
    save_baseline(good, baseline)

    passed, regressions = compare_baseline(good, baseline)
    assert passed and regressions == []

    bad = run_eval(GOLD, bad_translate)
    passed2, regressions2 = compare_baseline(bad, baseline)
    assert not passed2 and regressions2


def test_report_markdown_renders():
    md = run_eval(GOLD, perfect_translate).to_markdown()
    assert "Overall" in md and "| a |" in md


def test_judge_axis_wired_when_provided():
    judge = lambda p: '{"adequacy":5,"fluency":5,"terminology":5,"format":5}'  # noqa: E731
    report = run_eval(GOLD, perfect_translate, judge_fn=judge)
    per = report.per_scorer()
    assert per.get("llm_judge") == 1.0


def test_load_real_golden_set_parses():
    items = load_golden(ROOT / "evalkit" / "golden")
    assert len(items) >= 4
    assert all(it.id and it.direction in ("en2vi", "vi2en") for it in items)
