# Blueprint — AST convergence (Option A)

> **⚑ TÀI LIỆU LỊCH SỬ — Option A ĐÃ HOÀN TẤT (stage 1→5 shipped).** Phần
> "Current state" và kế hoạch bên dưới mô tả thế giới TRƯỚC KHI thực thi (hai
> stack song song, cờ `OUTPUT_PIPELINE`, các file soak/flag-test cũ — nay đã
> xóa). Chỉ mục **Status** ở cuối file là thẩm quyền hiện hành; guard đương
> nhiệm: `scripts/soak_render_coverage.py` + `tests/eval/test_render_coverage.py`.

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
   - **2b — document assembly + styling _(done)_.** Done for DOCX: the
     `ebook`/`academic`/`business` **template system**, a **title page**, a
     **table of contents** (an auto-updating Word TOC field) and **running
     header/footer + page numbers** — wired into `render_book_docx` /
     `render_academic_docx`, default-off on the plain adapter. Done for **PDF**:
     the same **template path** — the PDF adapter now reads `ast.styles` and
     registers serif + sans families (ebook/academic → serif, business → sans),
     instead of hardcoding one font and its sizes. Done for **inline text runs**:
     an optional `Paragraph.runs` overlay (`InlineRun` spans: bold/italic/code)
     that is fully backward-compatible — `runs=None` renders exactly as before.
     The Markdown extractor parses `**`/`__`, `*`/`_`, `***`/`___` and `` `code` ``
     (underscore forms guarded so identifiers/paths are left alone); the DOCX
     extractor reads run-level bold/italic + monospace/code-style runs back.
     `docx_adapter` emits one Word run per span, `pdf_adapter` uses ReportLab
     `<b>`/`<i>` + built-in Courier, `epub_adapter` uses `<strong>`/`<em>`/`<code>`.
     `.text` stays a faithful plaintext view (markers removed), so every consumer
     that reads it keeps working. **Polish _(done)_:** the same emphasis now also
     renders inside **list items, blockquotes and table cells** — via the shared
     `core.rendering.inline.parse_inline`, parsed at render time in all three
     adapters, no AST model change (plain text stays plain). And the **PDF adapter
     reached DOCX book parity**: `render_pdf_from_ast` gained default-off
     `title_page` / `toc` (a real reportlab TableOfContents with page numbers via
     multiBuild) / `header_footer` (centered page number, cover unnumbered), and
     the live `OUTPUT_PIPELINE=ast` PDF path now requests them. (Remaining
     follow-up: source runs from `ast_builder(DocNode → AST)` where the semantic
     nodes still exist, not only from the enriched Markdown.)
3. **Wire behind a flag — _done_.** The live professional DOCX/PDF converters
   (`core_v2/output_converter.convert_markdown_to_{docx,pdf}_professional`, the
   functions the orchestrator calls) now consult `OUTPUT_PIPELINE`. Unset /
   `engine` (default) keeps the legacy `docx_engine` / `pdf_engine` path exactly
   as before; `OUTPUT_PIPELINE=ast` routes markdown → `extract_to_ast` →
   `render_docx_from_ast` (ebook/academic/business template + title page + TOC +
   header/footer) / `render_pdf_from_ast` (serif/sans template). The AST branch is
   wrapped in a try/except that **falls back to the legacy engine on any error**,
   so flipping the flag can never leave a job with no output. Env wins live (ops
   can flip without a code change); the `output_pipeline` setting is the default.
   Both branches are exercised by `tests/unit/test_output_pipeline_flag.py`.
4. **Flip the default** to the AST path, keeping the engines as fallback. Gate:
   the eval baseline (needs a provider key) shows no regression, and the
   output-equivalence tests are green. The **content-parity half of this gate is
   already met** — `scripts/soak_ast_vs_engine.py` (+ `tests/eval/test_ast_engine_soak.py`,
   no key) shows the AST path drops no source content the engine keeps and covers
   DOCX *better*; see `docs/SOAK_AST_VS_ENGINE.md`. What still needs the key is the
   translation-quality baseline.
5. **Retire the legacy engines** (`core/docx_engine`, `core/pdf_engine`, and the
   legacy `core/pdf_renderer_v2` WeasyPrint path) — the large LOC drop — only once
   nothing depends on them and the AST path has carried the default with no
   regressions.

## Safety gates (every stage)

- The live default does **not** change until stage 4. (Stage 3 added the flag but
  left `engine` the default; `ast` is opt-in and self-heals via legacy fallback.)
- Full CI green on Python 3.11 + 3.12 (unit / api / security / core / integration
  / eval / import-smoke).
- Output-equivalence tests must pass before any default flip.
- The **eval baseline** is the quality gate for stage 4; structural correctness is
  provable without a key, but neutrality of the renderer swap is confirmed by
  output-equivalence **and** the eval baseline.
- Legacy engines are deleted only in stage 5, after a soak with no regressions.

## Status

Stage 1 (faithful Markdown → AST), stage 2a (equivalence harness + correctness
fixes), **all of stage 2b** — **DOCX document assembly** (template + title page +
TOC + running header/footer), **PDF templates**, and **inline runs**
(bold/italic/code, default-safe `Paragraph.runs` overlay) — and **stage 3**
(flag-wire `OUTPUT_PIPELINE=ast` on the live DOCX/PDF converters, with automatic
fallback to the legacy engine) — shipped.

**Stage 4 — shipped.** The live default is now `ast` (`settings.output_pipeline`);
`OUTPUT_PIPELINE=engine` remains the ops escape hatch until stage 5. Gate met via
the structural axis: the content-parity soak (`docs/SOAK_AST_VS_ENGINE.md`, in CI
as `tests/eval/test_ast_engine_soak.py`) shows AST ≥ engine coverage on every
sample/format — the renderer swap happens after translation, so it cannot change
translation quality; the translation eval baseline (`docs/EVAL_HARNESS.md`)
remains recommended as a pre-wide-beta reference point and needs a provider key.

**Stage 5 — shipped. Option A is complete.** `core/docx_engine` and
`core/pdf_engine` (~5.3K lines) are deleted; the professional converters route
straight through the AST adapters (an AST failure raises, and the orchestrator's
pandoc fallback still guarantees an output). The `OUTPUT_PIPELINE` flag and the
`output_pipeline` setting are gone with the engines. The engine-vs-AST soak is
succeeded by the absolute content guard `scripts/soak_render_coverage.py`
(`docs/SOAK_RENDER_COVERAGE.md`, in CI as `tests/eval/test_render_coverage.py`).
