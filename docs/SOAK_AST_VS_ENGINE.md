# Soak: legacy engine vs AST pipeline

The objective, **no-API-key** parity check that de-risks the Option-A stage-4
default flip (switching the live DOCX/PDF export from the legacy
`docx_engine`/`pdf_engine` to the `DocumentAST` + `core/rendering` adapters).

## What it does

`scripts/soak_ast_vs_engine.py` renders a corpus of sample Markdown documents
through **both** live professional converters —
`convert_markdown_to_{docx,pdf}_professional` with `OUTPUT_PIPELINE=engine` and
again with `OUTPUT_PIPELINE=ast` — then extracts the text each output actually
contains and compares it against the source.

The metric is **source-token coverage**: the fraction of the source's content
words that survive into the rendered file (1.00 = nothing dropped). The gate that
matters for the flip is simple and asymmetric:

- the AST path must **drop no source token the engine keeps**, and
- its coverage must be **at least as high** as the engine's, on every sample and
  format.

AST-only extra tokens are expected and fine — they are the front matter the AST
book layout adds (cover page, table-of-contents heading). Bare list ordinals are
*not* counted as content, because the AST DOCX renderer emits native Word
auto-numbered lists (the number is Word's list numbering, not paragraph text)
whereas the legacy engine embeds the digit literally.

## Run it

```bash
# Full corpus + a written report; exits non-zero if a regression is found
python scripts/soak_ast_vs_engine.py --report soak_report.md

# Keep the rendered engine/AST artifacts to eyeball them
python scripts/soak_ast_vs_engine.py --keep ./soak_out
```

The same check runs in CI as `tests/eval/test_ast_engine_soak.py` (one document,
DOCX + PDF) so a future change that makes the AST path lose content fails the
build.

## Latest result

No content regressions. On every sample and format the AST pipeline covers the
source at least as well as the legacy engine — and on **DOCX it covers *better***
(the engine dropped some content the AST path preserves):

| sample | fmt | engine cov | ast cov |
| --- | --- | --- | --- |
| prose_inline | docx | 0.97 | **1.00** |
| lists | docx | 0.94 | **1.00** |
| table | docx | 0.88 | **1.00** |
| mixed_book | docx | 0.97 | **1.00** |
| (all) | pdf | 0.97–1.00 | 0.97–1.00 (parity) |

So on the *structural / content* axis the AST path is ready. The remaining gate
before flipping the default (stage 4) is the **translation-quality eval baseline**
(`docs/EVAL_HARNESS.md`), which needs a provider key — the renderer swap being
content-neutral is confirmed here; quality neutrality of the whole pipeline is
confirmed by that baseline.
