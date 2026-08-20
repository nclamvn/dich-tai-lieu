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
   output. Split:
   - **2a — content fidelity + the objective gate _(done)_.** An
     output-equivalence harness (`tests/unit/test_ast_parity.py`): round-trip
     fidelity (every block type survives DOCX/PDF), and a legacy-vs-AST DOCX
     check that the AST path loses no heading/paragraph/list/table content the
     legacy `DocxRenderer` captures. Fixed the concrete correctness gaps the
     audit found: the DOCX adapter no longer force-rewrites Georgia/Cambria →
     Times New Roman (the AST font is honored), it now applies page size +
     margins from `DocumentMetadata`, and the PDF adapter honors the metadata
     page size instead of hardcoding A4. (Note: both adapters already dispatch
     all 14 block types — nothing was being dropped — and they render images +
     equations the legacy PDF engine drops.)
   - **2b — document assembly + styling _(in progress)_.** Done: the
     `ebook`/`academic`/`business` **template system** (`render_docx_from_ast`
     takes a `template` that swaps the stylesheet, and `render_book_docx` /
     `render_academic_docx`, previously no-op, now apply theirs) and a DOCX
     **title page** (centered title + author + page break, enabled by the
     book/academic convenience renderers). Remaining: table of contents, running
     headers/footers + page numbers, a PDF template path (the PDF adapter still
     hardcodes its styles), and inline text runs (bold/italic/code inside
     paragraphs — needs an inline-run model in the AST). Drive from the richest
     source available: prefer `ast_builder(DocNode → AST)` where the semantic
     nodes still exist, else the enriched Markdown → AST.
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

Stage 1 (faithful Markdown → AST), stage 2a (equivalence harness + content /
page / font correctness fixes) and stage 2b's **template system + DOCX title
page** shipped. Remaining: the rest of stage 2b (TOC, headers/footers, PDF
templates, inline runs), stage 3 (flag-wire), stage 4 (flip default — needs the
eval baseline from `docs/EVAL_HARNESS.md`), stage 5 (retire the legacy engines).
