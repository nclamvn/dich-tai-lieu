"""Scorers for EN<->VI translation quality (TIP-Q0).

Every scorer returns a :class:`ScoreResult` whose ``score`` is normalized to
``[0, 1]`` (or ``None`` when the scorer cannot apply — e.g. no reference, or no
LLM judge available). All scorers are pure and network-free EXCEPT the network
call is pushed OUT of :func:`llm_judge` via an injectable ``judge_fn`` — so the
whole module is fully testable offline with no API key.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ScoreResult:
    """One scorer's verdict for one translation."""

    name: str
    score: Optional[float]  # in [0, 1], or None when not applicable
    detail: dict = field(default_factory=dict)
    violations: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Reference-based: chrF++ (via sacrebleu). No network.
# --------------------------------------------------------------------------- #
def chrf(hypothesis: str, reference: Optional[str]) -> ScoreResult:
    """chrF++ score normalized to [0, 1]. Returns None if no reference."""
    if not reference:
        return ScoreResult("chrf", None, {"reason": "no reference"})
    from sacrebleu.metrics import CHRF

    raw = CHRF(word_order=2).sentence_score(hypothesis, [reference]).score  # 0..100
    return ScoreResult("chrf", max(0.0, min(1.0, raw / 100.0)), {"raw_chrf": round(raw, 2)})


# --------------------------------------------------------------------------- #
# Terminology: expected terms present; do-not-translate terms kept verbatim.
# --------------------------------------------------------------------------- #
def terminology(
    hypothesis: str,
    expect_terms: Optional[list] = None,
    expect_no_translate: Optional[list] = None,
) -> ScoreResult:
    """Fraction of terminology constraints satisfied. None if no constraints."""
    expect_terms = expect_terms or []
    expect_no_translate = expect_no_translate or []
    total = len(expect_terms) + len(expect_no_translate)
    if total == 0:
        return ScoreResult("terminology", None, {"reason": "no terms specified"})

    hay = hypothesis.lower()
    violations = []
    hits = 0
    for term in expect_terms:
        if term.lower() in hay:
            hits += 1
        else:
            violations.append({"type": "missing_term", "term": term})
    for term in expect_no_translate:  # verbatim, case-sensitive
        if term in hypothesis:
            hits += 1
        else:
            violations.append({"type": "should_not_translate", "term": term})

    return ScoreResult(
        "terminology", hits / total, {"hits": hits, "total": total}, violations
    )


# --------------------------------------------------------------------------- #
# Format preservation: structural feature counts vs the source.
# --------------------------------------------------------------------------- #
_FORMULA_RE = re.compile(r"\$[^$]+\$|\\\([^)]*\\\)|\\\[[^\]]*\\\]")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


def _structural_features(text: str) -> dict:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return {
        "lines": len(lines),
        "table_rows": sum(1 for ln in lines if ln.count("|") >= 2),
        "formulas": len(_FORMULA_RE.findall(text)),
        "list_items": sum(1 for ln in lines if _LIST_RE.match(ln)),
    }


def format_preservation(hypothesis: str, source: str) -> ScoreResult:
    """1.0 when structural counts match the source; drops as they diverge."""
    src = _structural_features(source)
    hyp = _structural_features(hypothesis)
    detail = {}
    sims = []
    for feat in ("lines", "table_rows", "formulas", "list_items"):
        s, h = src[feat], hyp[feat]
        sim = 1.0 if (s == 0 and h == 0) else 1.0 - abs(s - h) / max(s, h, 1)
        sims.append(sim)
        detail[feat] = {"source": s, "hypothesis": h, "sim": round(sim, 3)}
    return ScoreResult("format_preservation", sum(sims) / len(sims), detail)


# --------------------------------------------------------------------------- #
# LLM-as-judge: rubric scoring. Network is injected via judge_fn (mockable).
# --------------------------------------------------------------------------- #
_JUDGE_AXES = ("adequacy", "fluency", "terminology", "format")

_JUDGE_PROMPT = """You are a strict bilingual {direction} translation-quality judge.
Rate the TRANSLATION of the SOURCE on four axes, each an integer 0-5:
- adequacy: is the meaning fully preserved?
- fluency: is it natural in the target language?
- terminology: are terms correct and consistent?
- format: is structure/markup (tables, formulas, lists) preserved?
Return ONLY a JSON object, no prose:
{{"adequacy": N, "fluency": N, "terminology": N, "format": N}}

SOURCE:
{source}

TRANSLATION:
{hypothesis}
"""


def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in judge output")
    return json.loads(match.group(0))


def llm_judge(
    hypothesis: str,
    source: str,
    direction: str = "en2vi",
    reference: Optional[str] = None,  # accepted for signature parity; unused here
    judge_fn: Optional[Callable[[str], str]] = None,
) -> ScoreResult:
    """Average of four rubric axes / 5. ``judge_fn`` maps prompt->raw JSON text.

    None (skipped) when no ``judge_fn`` is supplied, and fail-open (None, not an
    exception) when the judge errors or returns malformed output — a judge
    problem must never crash an eval run.
    """
    if judge_fn is None:
        return ScoreResult("llm_judge", None, {"reason": "no judge_fn provided"})
    prompt = _JUDGE_PROMPT.format(direction=direction, source=source, hypothesis=hypothesis)
    try:
        data = _extract_json(judge_fn(prompt))
        vals = [float(data[axis]) for axis in _JUDGE_AXES]
    except Exception as exc:  # noqa: BLE001 — deliberate fail-open
        return ScoreResult("llm_judge", None, {"error": str(exc)})
    score = sum(vals) / (5.0 * len(vals))
    return ScoreResult(
        "llm_judge",
        max(0.0, min(1.0, score)),
        {axis: val for axis, val in zip(_JUDGE_AXES, vals)},
    )
