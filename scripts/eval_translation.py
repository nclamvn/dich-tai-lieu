#!/usr/bin/env python3
"""CLI for the EN<->VI translation quality eval harness (TIP-Q0).

Wires the real engine as the translator and (optionally) the real LLM as judge.
The scoring/gating logic lives in ``evalkit/`` and is unit-tested offline; this
file only does the network wiring, so it needs a provider API key to run.

Examples
--------
  # measure current engine and SAVE the baseline
  python3 scripts/eval_translation.py --save-baseline eval_baseline.json

  # later: fail (exit!=0) if quality regressed vs the saved baseline
  python3 scripts/eval_translation.py --baseline eval_baseline.json --gate

  # include the LLM-as-judge axis (extra API cost)
  python3 scripts/eval_translation.py --judge
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY")


def _lang_names(direction: str):
    return ("English", "Vietnamese") if direction == "en2vi" else ("Vietnamese", "English")


def _content_of(resp) -> str:
    content = getattr(resp, "content", resp)
    return content if isinstance(content, str) else str(content)


def _job_text(job) -> str:
    """Best-effort extraction of translated text from a PublishingJob."""
    for attr in ("translated_text", "translated_markdown", "markdown", "output_text", "result", "content"):
        val = getattr(job, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    raise RuntimeError(
        "Could not read translated text from PublishingJob; available attrs: "
        + ", ".join(sorted(vars(job).keys()))
    )


def _make_fns(backend: str, run):
    from ai_providers.unified_client import UnifiedLLMClient

    client = UnifiedLLMClient()

    async def _translate_raw(source: str, direction: str) -> str:
        src, tgt = _lang_names(direction)
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a professional {src}-to-{tgt} translator. "
                    "Translate faithfully, preserve formatting/markup, and output "
                    "ONLY the translation with no notes."
                ),
            },
            {"role": "user", "content": source},
        ]
        return _content_of(await client.chat(messages, temperature=0.3))

    async def _translate_engine(source: str, direction: str) -> str:
        from core_v2.orchestrator import translate_document

        _, tgt = _lang_names(direction)
        job = await translate_document(source, "auto", tgt, client, output_format="markdown")
        return _job_text(job)

    coro = _translate_engine if backend == "engine" else _translate_raw

    def translate_fn(source: str, direction: str) -> str:
        return run(coro(source, direction))

    def judge_fn(prompt: str) -> str:
        return run(client.chat([{"role": "user", "content": prompt}], temperature=0.0))

    return translate_fn, judge_fn


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="EN<->VI translation quality eval")
    parser.add_argument("--golden", default=str(ROOT / "evalkit" / "golden"))
    parser.add_argument("--backend", choices=("raw", "engine"), default="raw")
    parser.add_argument("--judge", action="store_true", help="include LLM-as-judge (extra cost)")
    parser.add_argument("--baseline", help="baseline JSON to compare against")
    parser.add_argument("--save-baseline", dest="save_baseline", help="write baseline JSON here")
    parser.add_argument("--gate", action="store_true", help="exit!=0 on regression vs --baseline")
    parser.add_argument("--tolerance", type=float, default=0.03)
    parser.add_argument("--limit", type=int, default=0, help="only first N items (0 = all)")
    parser.add_argument("--report", help="write markdown report here (default: stdout)")
    args = parser.parse_args(argv)

    from evalkit.runner import compare_baseline, load_golden, run_eval, save_baseline

    golden = load_golden(args.golden)
    if args.limit:
        golden = golden[: args.limit]
    if not golden:
        print(f"No golden items found under {args.golden}", file=sys.stderr)
        return 2

    if not any(os.environ.get(k) for k in _KEYS):
        print(
            "No provider API key found. Set one of "
            + ", ".join(_KEYS)
            + " to run the eval (the scoring logic is unit-tested without a key).",
            file=sys.stderr,
        )
        return 2

    loop = asyncio.new_event_loop()
    try:
        translate_fn, judge_fn = _make_fns(args.backend, loop.run_until_complete)
        report = run_eval(golden, translate_fn, judge_fn if args.judge else None)
    finally:
        loop.close()

    md = report.to_markdown()
    if args.report:
        Path(args.report).write_text(md, encoding="utf-8")
        print(f"Wrote report -> {args.report}")
    else:
        print(md)

    if args.save_baseline:
        save_baseline(report, args.save_baseline)
        print(f"Saved baseline -> {args.save_baseline}")

    if args.baseline:
        passed, regressions = compare_baseline(report, args.baseline, args.tolerance)
        if regressions:
            print("\nREGRESSIONS vs baseline:")
            for r in regressions:
                print(f"  - {r['scope']}: {r['baseline']:.3f} -> {r['now']:.3f}")
        if args.gate and not passed:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
