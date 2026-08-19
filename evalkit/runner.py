"""Golden-set loader, eval runner, and regression gate (TIP-Q0).

The runner is engine-agnostic: it takes a ``translate_fn(source, direction) ->
str`` and an optional ``judge_fn(prompt) -> str``. That keeps this module
offline-testable (inject mocks) while ``scripts/eval_translation.py`` wires the
real engine + LLM judge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from evalkit.scorers import (
    ScoreResult,
    chrf,
    format_preservation,
    llm_judge,
    terminology,
)


@dataclass
class GoldenItem:
    id: str
    direction: str  # "en2vi" | "vi2en"
    source: str
    domain: str = "general"
    reference: Optional[str] = None
    expect_terms: list = field(default_factory=list)
    expect_no_translate: list = field(default_factory=list)


def load_golden(path) -> list[GoldenItem]:
    """Load golden items from a YAML file or a directory of YAML files."""
    import yaml

    p = Path(path)
    files = (
        sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml")) if p.is_dir() else [p]
    )
    items: list[GoldenItem] = []
    for f in files:
        docs = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        if isinstance(docs, dict):
            docs = [docs]
        for d in docs:
            items.append(
                GoldenItem(
                    id=d["id"],
                    direction=d["direction"],
                    source=d["source"],
                    domain=d.get("domain", "general"),
                    reference=d.get("reference"),
                    expect_terms=d.get("expect_terms", []),
                    expect_no_translate=d.get("expect_no_translate", []),
                )
            )
    return items


@dataclass
class ItemResult:
    id: str
    direction: str
    domain: str
    hypothesis: str
    scores: dict  # scorer name -> ScoreResult

    @property
    def mean(self) -> Optional[float]:
        vals = [s.score for s in self.scores.values() if s.score is not None]
        return sum(vals) / len(vals) if vals else None


def _mean(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


@dataclass
class EvalReport:
    items: list  # list[ItemResult]

    def overall(self) -> Optional[float]:
        return _mean([it.mean for it in self.items])

    def per_scorer(self) -> dict:
        names: list = []
        for it in self.items:
            for n in it.scores:
                if n not in names:
                    names.append(n)
        return {
            n: _mean([it.scores[n].score for it in self.items if n in it.scores])
            for n in names
        }

    def by(self, attr: str) -> dict:
        groups: dict = {}
        for it in self.items:
            groups.setdefault(getattr(it, attr), []).append(it.mean)
        return {k: _mean(v) for k, v in groups.items()}

    def summary(self) -> dict:
        """Compact dict suitable for a baseline file."""
        return {
            "overall": self.overall(),
            "per_scorer": self.per_scorer(),
            "by_direction": self.by("direction"),
            "items": [{"id": it.id, "mean": it.mean} for it in self.items],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.summary(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        lines = ["# Eval report — translation quality", ""]
        ov = self.overall()
        lines.append(f"**Overall:** {ov:.3f}" if ov is not None else "**Overall:** n/a")
        lines.append("")
        lines.append("## Per scorer")
        for name, val in self.per_scorer().items():
            lines.append(f"- {name}: {val:.3f}" if val is not None else f"- {name}: n/a")
        lines.append("")
        lines.append("## Per direction")
        for name, val in self.by("direction").items():
            lines.append(f"- {name}: {val:.3f}" if val is not None else f"- {name}: n/a")
        lines.append("")
        lines.append("## Items")
        lines.append("| id | dir | mean | violations |")
        lines.append("|---|---|---|---|")
        for it in self.items:
            viol = sum(len(s.violations) for s in it.scores.values())
            m = f"{it.mean:.3f}" if it.mean is not None else "n/a"
            lines.append(f"| {it.id} | {it.direction} | {m} | {viol} |")
        return "\n".join(lines) + "\n"


def run_eval(
    golden: list,
    translate_fn: Callable[[str, str], str],
    judge_fn: Optional[Callable[[str], str]] = None,
) -> EvalReport:
    """Translate every golden source and score it. Deterministic given inputs."""
    results = []
    for it in golden:
        hyp = translate_fn(it.source, it.direction)
        scores: dict = {}
        chrf_res = chrf(hyp, it.reference)
        if chrf_res.score is not None:
            scores["chrf"] = chrf_res
        term_res = terminology(hyp, it.expect_terms, it.expect_no_translate)
        if term_res.score is not None:
            scores["terminology"] = term_res
        scores["format_preservation"] = format_preservation(hyp, it.source)
        judge_res = llm_judge(hyp, it.source, it.direction, it.reference, judge_fn)
        if judge_res.score is not None:
            scores["llm_judge"] = judge_res
        results.append(ItemResult(it.id, it.direction, it.domain, hyp, scores))
    return EvalReport(results)


def save_baseline(report: EvalReport, path) -> None:
    Path(path).write_text(report.to_json(), encoding="utf-8")


def compare_baseline(report: EvalReport, baseline_path, tolerance: float = 0.03):
    """Return (passed, regressions). A regression = a drop > tolerance vs baseline."""
    base = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    regressions = []

    now_overall, base_overall = report.overall(), base.get("overall")
    if now_overall is not None and base_overall is not None:
        if now_overall < base_overall - tolerance:
            regressions.append(
                {"scope": "overall", "baseline": base_overall, "now": now_overall}
            )

    base_items = {i["id"]: i for i in base.get("items", [])}
    for it in report.items:
        b = base_items.get(it.id)
        if b and it.mean is not None and b.get("mean") is not None:
            if it.mean < b["mean"] - tolerance:
                regressions.append(
                    {"scope": it.id, "baseline": b["mean"], "now": it.mean}
                )

    return (len(regressions) == 0, regressions)
