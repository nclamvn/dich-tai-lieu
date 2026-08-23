# Soak: render coverage

The **no-API-key** content-integrity guard for the live renderer (the
`DocumentAST` + `core/rendering` adapters — the only DOCX/PDF stack since
Option A stage 5).

## History

This file succeeds `SOAK_AST_VS_ENGINE.md`. That harness compared the legacy
`docx_engine`/`pdf_engine` against the AST stack to de-risk the stage-4 default
flip; the recorded result was decisive — the AST path matched PDF coverage and
**beat** the engine on every DOCX sample (engine 0.88–0.97 vs AST 1.00):

| sample | fmt | engine cov | ast cov |
| --- | --- | --- | --- |
| prose_inline | docx | 0.97 | **1.00** |
| lists | docx | 0.94 | **1.00** |
| table | docx | 0.88 | **1.00** |
| mixed_book | docx | 0.97 | **1.00** |
| (all) | pdf | 0.97–1.00 | 0.97–1.00 (parity) |

Stage 4 flipped the default to AST on that evidence; stage 5 retired the
engines, so the comparison leg is gone. What remains is the absolute invariant.

## What it does

`scripts/soak_render_coverage.py` renders a corpus of sample Markdown documents
through the live converters (`convert_markdown_to_{docx,pdf}_professional`),
extracts the text each output actually contains, and computes **source-token
coverage** — the fraction of the source's content words that survive into the
rendered file (1.00 = nothing dropped).

Coverage floors are pinned from the recorded results:

- **DOCX ≥ 0.99** (recorded 1.00 on every sample)
- **PDF ≥ 0.95** (recorded 0.97–1.00; the slack is pypdf extraction noise, not
  renderer loss)

A drop below a floor exits non-zero.

## Run it

```bash
# Full corpus + a written report; exits non-zero on a regression
python scripts/soak_render_coverage.py --report soak_report.md

# Keep the rendered artifacts to eyeball them
python scripts/soak_render_coverage.py --keep ./soak_out
```

The same check runs in CI as `tests/eval/test_render_coverage.py` (one document,
DOCX + PDF), so a change that makes the renderer lose content fails the build.
