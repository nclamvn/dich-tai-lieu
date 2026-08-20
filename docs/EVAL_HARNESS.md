# Translation quality eval harness (EN↔VI)

A small, **offline-testable** harness that measures translation quality against a
human-referenced golden set. The scoring logic runs with **no API key**; a key is
only needed to translate real candidates for a baseline.

## What it measures

Each candidate translation is scored on four axes (`evalkit/scorers.py`), every
score normalized to `[0, 1]`:

- **chrf** — chrF++ vs the human reference (via `sacrebleu`). Network-free.
- **terminology** — declared `expect_terms` are present, and `expect_no_translate`
  tokens are kept verbatim (names, code, formulas, numbers, URLs).
- **format_preservation** — structural counts (lines, table rows, `$…$` formulas,
  list items) match the source, so layout survives translation.
- **llm_judge** — an LLM rubric (adequacy / fluency / terminology / format), 0–5
  each. The network call is injected via `judge_fn`, so it is *mockable* and
  **fail-open** (a judge error yields `None`, never a crashed run). Off by default.

## The golden set

`evalkit/golden/*.yaml` — 23 seed items across `technical`, `academic`, `book`,
`general`, in both directions. Every file is loaded; add items freely. Schema:

```yaml
- id: unique-id
  direction: en2vi        # or vi2en
  domain: technical
  source: "…"
  reference: "…"          # human translation
  expect_terms: ["…"]            # optional: must appear (case-insensitive)
  expect_no_translate: ["…"]     # optional: must be kept verbatim
```

Invariant enforced by the tests: an item's own `reference` must satisfy its own
`expect_terms` / `expect_no_translate` — a malformed constraint fails CI.

## Run it offline (no API key)

```bash
pytest tests/eval/ -q          # scorers + runner + real golden, end-to-end
```

`tests/eval/test_runner.py::test_real_golden_end_to_end_offline` runs the whole
pipeline over the real golden set with a reference-echo translator and asserts a
near-perfect score with zero violations — proof the harness is turnkey before any
key is attached.

## Produce a baseline (needs a provider key)

Attach any one provider key, then translate the golden set and save a baseline:

```bash
export OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY / GOOGLE_API_KEY / DEEPSEEK_API_KEY
python3 scripts/eval_translation.py \
  --backend engine \                # 'engine' = full translate_document; 'raw' = single chat call
  --judge \                         # include the LLM judge (extra cost)
  --save-baseline eval_baseline.json \
  --report eval_report.md
```

Without a key the script exits with a clear message (the scoring logic is still
unit-tested). `--limit N` runs only the first N items for a quick smoke.

## Regression gate

Once a baseline exists, fail CI/local runs when quality drops more than
`--tolerance` (default 0.03) overall or on any item:

```bash
python3 scripts/eval_translation.py --backend engine --baseline eval_baseline.json --gate
```

Tuning translation quality (term ledger, prompts, quality gate) is then measured
against this harness rather than by eye.
