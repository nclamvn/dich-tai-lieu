# Blueprint — AST convergence (Option A)

**Goal.** Make the single `DocumentAST` + `core/rendering` adapters the *primary*
output path for DOCX / PDF / EPUB, and retire the parallel legacy renderers
(`core/docx_engine`, `core/pdf_engine`) once the AST path reaches parity. One
faithful representation, every format.

## Current state (from the two-stack audit)

- **Two live renderer stacks.** Legacy `core/docx_engine` (~3.0K LOC) and
  `core/pdf_engine` (~2.3K LOC) drive the live V2 DOCX/PDF output — via
  `core_v2/output_converter.py`, from *translated markdown*. EPUB already renders
  through `core/rendering` (ebooklib).
- **The AST stack already exists, partly wired.** `core/rendering/` has
  `document_ast`, `ast_builder` (semantic `DocNode` → AST), `document_extractor`
  (DOCX/Markdown → AST), the `docx/pdf/epub` adapters, and the `render` facade.
  `render.py` + `pdf_adapter` are not yet on any live path.

So the pieces largely exist; what's missing is *faithful input*, *parity*,
*wiring*, and *retirement*.

## Why staged, not big-bang

The legacy engines are mature (templates, normalizer, professional book/academic
layout). The AST adapters are younger and simpler; flipping blindly risks a
visible feature/quality regression. Every stage below is **default-safe**
(additive or flag-gated) and gated by tests. The final flip is additionally gated
by the **eval baseline** (`docs/EVAL_HARNESS.md`) proving output quality did not
drop.

## Stages

1. **Faithful Markdown → AST — _this PR_.** `extract_text` now parses tables,
   display math (`$$…$$`), blockquotes and image figures (previously dropped).
   Immediate win: the already-live EPUB path stops flattening them. Foundation
   for feeding the AST renderers from the live translated markdown.
2. **Parity.** Bring `docx_adapter` / `pdf_adapter` up to the legacy engines'
   output — styles, templates, book/academic layout, TOC, page setup. Drive from
   the richest source available: prefer `ast_builder(DocNode → AST)` where the
   semantic nodes still exist, else the enriched Markdown → AST. Add
   **output-equivalence tests** (AST-DOCX vs engine-DOCX: same headings, tables,
   figures, counts).
3. **Wire behind a flag.** Expose the AST facade as an alternative output path
   (e.g. `OUTPUT_PIPELINE=ast`), parallel to the engines; exercise both in CI.
4. **Flip the default** to the AST path, keeping the engines as fallback. Gate:
   the eval baseline (needs a provider key) shows no regression, and the
   output-equivalence tests are green.
5. **Retire the legacy engines** (`core/docx_engine`, `core/pdf_engine`, and the
   legacy `core/pdf_renderer_v2` WeasyPrint path) — the large LOC drop — only once
   nothing depends on them and the AST path has carried the default with no
   regressions.

## Safety gates (every stage)

- The live default does **not** change until stage 4.
- Full CI green on Python 3.11 + 3.12 (unit / api / security / core / integration
  / eval / import-smoke).
- Output-equivalence tests must pass before any default flip.
- The **eval baseline** is the quality gate for stage 4; structural correctness is
  provable without a key, but neutrality of the renderer swap is confirmed by
  output-equivalence **and** the eval baseline.
- Legacy engines are deleted only in stage 5, after a soak with no regressions.

## Status

Stage 1 shipped (this PR). Stages 2–5 are separate PRs; stage 4 depends on the
eval baseline from `docs/EVAL_HARNESS.md`.
