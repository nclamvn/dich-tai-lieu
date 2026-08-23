# Changelog

All notable changes to AI Publisher Pro will be documented in this file.

## [Unreleased] — P2 debt paydown

### Changed
- **One port map everywhere**: backend **:8000**, frontend **:3000** — in dev.sh,
  Dockerfile, Dockerfile.dev, docker-compose and nginx alike (was 3000/3001 in
  Docker). `BACKEND_PORT`/`FRONTEND_PORT` env still override the published ports.
- **Lifespan startup**: the nine deprecated `@app.on_event` handlers now run from
  a single `_lifespan` (identical order); dead `integrate_with_app()` removed.
- `api/main.py` sheds its 7 unreachable inline `/api/system|queue|cache|processor`
  duplicates — `api/routes/system.py` is the only definition, and the
  `/api/cache/clear` 5/minute rate limit now sits on the route that actually
  serves (the decorator previously lived on the dead copy).

### Fixed
- docker-compose gave the browser bundle `NEXT_PUBLIC_API_URL=http://backend:3000`
  — a Docker-internal hostname no real browser can resolve; defaults to
  `http://localhost:8000` now (override via env for real domains).
- nginx profile proxied everything to `app:3001`, a service that doesn't exist in
  compose — split into `backend_server` (API/WS/health) + `frontend_server` (pages).
- `Dockerfile.dev` ran python:3.11 while production runs 3.13 — aligned to 3.13.
- `JobRepository` logged `data/jobs.db` while actually writing `data/aps_jobs.db`
  (source of the "orphan aps_jobs.db" ledger scare — both DBs are live: v1 queue
  vs v2 job store). The log now tells the truth.

## [3.3.1] - 2026-08-23

### BREAKING: AST is the only renderer (Option A complete)
- **Stage 4**: `OUTPUT_PIPELINE` default flipped to the AST stack — every DOCX/PDF
  export renders through `DocumentAST` + `core/rendering` adapters (proven better
  source coverage than the legacy engines on every soak sample).
- **Stage 5 (breaking)**: `core/docx_engine` + `core/pdf_engine` deleted
  (~5.3K lines) along with the `OUTPUT_PIPELINE` flag and `output_pipeline`
  setting. Content integrity is guarded by `scripts/soak_render_coverage.py`
  (in CI as `tests/eval/test_render_coverage.py`; floors DOCX ≥ 0.99, PDF ≥ 0.95).
  An AST failure raises and the orchestrator's pandoc fallback still guarantees
  an output.

### New: Cover templates
- 12 pre-built cover designs rendered natively with ReportLab (no new deps),
  applied to PDF (merged page 1), DOCX (full-bleed zero-margin section) and
  EPUB (baked at build time). Custom cover image upload wins over templates.
- Picker UI in the translate screen (`/api/cover-templates` + live previews +
  `/api/cover-upload`); per-job `cover_template`/`cover_image` through
  `/api/v2/publish` and `/publish/text`; env defaults `COVER_TEMPLATE`/`COVER_IMAGE`.
- Bundled Vietnamese-complete fonts (`assets/fonts/`, Noto Sans/Serif, OFL) —
  covers and PDF body render diacritics on every machine; preview URLs are
  version-stamped so browser cache can't mask a font/template fix.

### Fixed
- Running headers/footers ("page furniture") stripped from extracted text
  before translation — the book title no longer litters the body/TOC
  (`core_v2/text_cleanup.py`, `STRIP_RUNNING_FURNITURE`).
- Full test suite brought to green (~3.2K tests) and CI extended to every test
  tree (batch/rri_t/e2e/streaming/v2/root) with `tsc --noEmit` as a hard gate.
- Generated artifacts purged from git (`outputs/`, test outputs, runtime data)
  with whole-tree ignore rules.

### Maintenance
- Dead code removed: orphan `integration_bridge/` + empty `services/` packages,
  stale root scripts (`translate_book.py`, `start_server.sh`, `setup.py`, …).
- Deprecations cleared: pydantic v2 `model_config` everywhere, `import pymupdf`
  (fitz shim retired), `asyncio.get_event_loop()` → `get_running_loop()`/`run()`
  (Python 3.13-safe). Unused dependencies dropped (pdf2image, openpyxl,
  aiofiles, python-dateutil, jieba).

## [Unreleased] — Translation engine quick-wins

Targeted upgrades to the live `core_v2` translation path (quality, cost, reliability).

### Quality
- Translation now runs at a low, configurable temperature (`TRANSLATION_TEMPERATURE`,
  default 0.3) instead of the provider default (~1.0) → faithful, low-variance output.
- Per-provider model registry is env-overridable; Anthropic default refreshed from the
  stale `claude-sonnet-4-20250514` to `claude-sonnet-4-5-20250929`, Gemini from the
  experimental `-exp` alias to stable `gemini-2.0-flash`.
- Language-mismatch retry now reuses the full system prompt (keeps terminology/LaTeX
  guidance) instead of a stripped prompt.

### Cost
- Translation prompt split into a static (cacheable) system prefix + small dynamic user
  message, with Anthropic **prompt caching** (`cache_control`) on the prefix → ~30-50%
  fewer input tokens on multi-chunk documents.
- `ChunkCache` is now wired into `core_v2` with a collision-safe key
  (model + temperature + profile + prompt version) → repeated/identical content is not
  re-translated on re-runs.

### Reliability
- Failed chunks no longer ship a silent `[TRANSLATION ERROR: n]` hole in the document;
  a `ChunkTranslationError` fails the job loudly with the chunk index.
- Exponential backoff + full jitter for all transient errors (was 429-only, fixed 15/30/45s).
- Rate limits back off in-place then fail over (were raised); providers are benched with a
  TTL (`PROVIDER_HEALTH_TTL_SECONDS`) instead of for the whole process lifetime.
- Output truncation (`finish_reason=length` / `stop_reason=max_tokens`) is now detected and
  logged, and truncated chunks are never cached.

### Tests
- `tests/unit/test_engine_quickwins.py` — 28 unit tests covering backoff, error
  classification, cache-key discrimination, model-registry env overrides, health TTL, and
  `_translate_chunk` behaviour (temperature/cache_system forwarding, cache hit/miss/store,
  transient-retry, fail-loud). No regressions in existing suites.

### Terminology consistency (Phase 2 — cross-chunk quality)
- New `core_v2/term_ledger.py`: a shared, document-level term ledger (source → agreed
  target). Merges an optional user glossary (`core/glossary`, loaded lazily and guarded so
  it degrades to empty when SQLAlchemy is absent) with terms auto-extracted from the source
  in one LLM pre-pass. Diacritic/CJK-safe relevance matching.
- The ledger is injected into the **cached** `TRANSLATION_SYSTEM` prefix (new `{glossary}`
  slot), so every chunk shares the same terminology at near-zero token cost — fixing the
  proper-noun / term drift between chapters that the 100-char pseudo-context caused.
- The ledger fingerprint is folded into the chunk-cache key, so changing terminology
  invalidates stale cache entries.
- Fully degrade-safe: no glossary, no API key, or a failed pre-pass all fall back to the
  prior behaviour. `tests/unit/test_term_ledger.py` (23) + `tests/unit/test_glossary_wiring.py`
  (8); Phase-1 suites remain green (81 passing total).
- Settings: `TRANSLATION_AUTO_GLOSSARY_ENABLED`, `TRANSLATION_GLOSSARY_MAX_TERMS`,
  `TRANSLATION_GLOSSARY_IDS`.

### Token-aware chunking (Phase 3 — correctness & robustness)
- New `core_v2/token_chunking.py`: dependency-free, structure-preserving chunking sized by an
  estimated **token** budget (VN/CJK-aware) instead of raw character count. Guarantees every
  chunk stays within budget by splitting oversized blocks finest-first
  (lines → sentences → words → hard slices) without flattening newlines / paragraphs / LaTeX.
- `core_v2/semantic_chunker.py`: `_finalize_chunks` now runs a hard token-cap pass first, so
  **every** chunking path is guaranteed to emit no chunk over budget (`CHUNK_MAX_TOKENS`,
  default 2000). This kills the long-standing **mega-chunk bug** where the LLM-boundary path
  sampled only the first 10k chars but dumped everything after into one trailing chunk that
  then blew past the model's `max_tokens` (silent truncation).
- `_simple_chunk` rewritten to preserve structure (was `text.split()` + `' '.join()` — a blob
  that destroyed all newlines/paragraphs/LaTeX). `_detect_boundaries_with_claude` now logs
  failures instead of swallowing them. `_find_chapters` detects Vietnamese lowercase numbered
  headings and markdown h1–h6.
- `tests/unit/test_token_chunking.py` (22) + `tests/unit/test_chunker_tokencap.py` (8);
  `test_semantic_chunker.py` and all Phase-1/2 suites remain green (138 passing total).

### Quality gate + bounded repair (Phase 4 — catch & fix silent failures)
- New `core_v2/quality_gate.py`: deterministic, dependency-free checks that flag a translated
  chunk as suspect — empty, `[TRANSLATION ERROR]` marker, truncated, **too_short** (dropped
  content on a substantial source), **wrong_language**, and **latex_lost** (formulas dropped).
  Tuned to avoid false positives (a Vietnamese translation longer than its English source, or a
  shorter CJK one, stays clean).
- `core_v2/orchestrator.py`: a new **Stage 3.5 repair pass** (`_repair_suspect_chunks`) runs the
  gate over every translated chunk and re-translates ONLY the flagged ones — concurrently, under
  the semaphore, bounded by `TRANSLATION_REPAIR_MAX_CHUNKS` — adopting a retry only when it is
  *strictly* better. `_translate_chunk` gained `force_refresh` so repairs bypass the chunk-cache
  GET (and overwrite it with the good result). Clean chunks are never touched; the default path
  is unchanged.
- `tests/unit/test_quality_gate.py` (22) + `tests/unit/test_repair_pass.py` (6); all prior suites
  green (166 passing total). Settings: `TRANSLATION_REPAIR_ENABLED`, `TRANSLATION_REPAIR_MAX_CHUNKS`.

### Rolling cross-chunk context (Phase 5 — narrative continuity)
- New `core_v2/context_builder.py`: deterministic, LLM-free rolling context. For each chunk it
  builds a "previous content" window from the **tail** (end) of the preceding chunk plus a
  budgeted gist of older chunks, and a "next content" window from the head of the next chunk —
  all at sentence boundaries. This replaces the previous behaviour where both windows were just
  the first 100 characters of the neighbouring chunk (wrong end, sliced mid-word), a driver of
  discontinuity across chapters.
- `SemanticChunker._finalize_chunks` now populates `previous_summary` / `next_preview` from the
  context builder (first-chunk previous and last-chunk next stay `None`). Being deterministic, it
  adds no LLM cost and doesn't serialize the concurrent translation stage.
- Optional LLM summary pre-pass (`_summarize_chunks`, gated OFF by
  `TRANSLATION_CONTEXT_SUMMARY_ENABLED`) can enrich the gist with one-sentence chunk summaries
  computed in parallel. Settings: `TRANSLATION_CONTEXT_WINDOW`, `TRANSLATION_CONTEXT_SUMMARY_ENABLED`.
- `tests/unit/test_context_builder.py` (27) + `tests/unit/test_context_wiring.py` (7); all prior
  suites green (200 passing total).

### Translation Memory leverage (Phase 6 — reuse approved translations)
- New `core_v2/tm_gateway.py`: a guarded bridge to the existing (SQLite) Translation Memory that
  the live translation path previously ignored. Per chunk it finds exact and fuzzy sentence
  matches and renders them as prompt hints ("approved translations — reuse verbatim when the
  segment matches"). The gateway is **active only when the TM holds ≥1 segment**, so an empty or
  unavailable TM adds zero per-chunk cost, and it never raises into the caller.
- `_translate_chunk` prepends the TM hints to the **dynamic user message** (never the cached
  system prefix, never the templates), so a populated TM leverages prior work without breaking
  prompt caching. TM state is intentionally not part of the chunk-cache key.
- Read/hints path only; write-back is deferred (it needs sentence alignment to be worthwhile and
  overlaps the chunk cache). Settings: `TM_REUSE_ENABLED` (default on), `TM_MAX_HINTS`; reuses the
  existing `TM_FUZZY_THRESHOLD`.
- `tests/unit/test_tm_gateway.py` (9, real temp sqlite TM) + `tests/unit/test_tm_wiring.py` (4);
  all prior suites green (213 passing total).

### Semantic faithfulness verification (Phase 7 — close the verifier loop)
- New `core_v2/semantic_verifier.py`: an optional single-call LLM check of whether a translated
  chunk faithfully renders its source — catching dropped/added/mistranslated meaning that the
  deterministic Phase-4 gate cannot see. Returns a typed `SemanticVerdict(faithful, severity,
  issue)` and is **fail-open**: empty input, a client error, or a malformed reply all default to
  "faithful", so a flaky check never triggers a spurious re-translate.
- `_repair_suspect_chunks` gains an opt-in semantic pass (gated by
  `TRANSLATION_SEMANTIC_VERIFY_ENABLED`, default off; bounded by `TRANSLATION_SEMANTIC_VERIFY_MAX`):
  it checks the chunks the deterministic gate passed, and any judged unfaithful (≥ major severity)
  join the **same** bounded repair loop. On repair a semantic suspect is re-verified, so a faithful
  retry is adopted and a still-unfaithful one is rejected. Disabled (the default) leaves the repair
  path byte-for-byte identical to Phase 4.
- `tests/unit/test_semantic_verifier.py` (20) + `tests/unit/test_semantic_repair.py` (6); all prior
  suites green (239 passing total).

## [3.3.0] - 2026-02-12

### New Feature: Screenplay Studio

Transform novels and stories into professional screenplays with AI-powered video generation.

#### Highlights

- **12-Agent Pipeline**: Complete screenplay adaptation from analysis to video
- **4 Pricing Tiers**: FREE, STANDARD, PRO, DIRECTOR
- **Bilingual Support**: English + Vietnamese with cultural adaptation
- **3 Video Providers**: Pika Labs, Runway Gen-3, Google Veo 2
- **Professional Exports**: Fountain, PDF, Storyboard PDF, Video

#### Backend

- 12 AI agents for screenplay generation pipeline
- 4 video/image providers (DALL-E, Runway, Veo, Pika)
- SQLite database for project storage
- 17 API endpoints for screenplay operations
- Cost calculator with tier-based pricing

#### Frontend

- Dashboard with project list and stats
- 3-step Create Wizard (Source, Settings, Review)
- Script Editor with scene navigation
- Storyboard Viewer with shot grid
- Video Player with render progress
- Export Panel for all formats

#### Pipeline Phases

1. **Analysis** (FREE): Story analysis + scene breakdown
2. **Screenplay** (FREE): Dialogue + action writing + formatting
3. **Pre-Visualization** (STANDARD): Shot lists + storyboard images
4. **Video Rendering** (PRO): AI video generation + editing

#### Technical

- 60+ new files created
- 1,328 tests passing
- 40 API endpoint tests
- Full integration testing completed
- 9 bugs found and fixed during integration

### Fixed

- API field name mismatches between frontend/backend
- Missing progress, visualize, render endpoints
- Missing export endpoints for storyboard-pdf and video
- Unicode emoji rendering in export panel
- Next.js API proxy configuration

---

## [2.7.0] - 2024-12-21

### 🎉 Initial Public Release

#### ✨ Features
- **Smart Extraction Router**: Automatically detect document type and choose optimal extraction strategy
  - FAST_TEXT: For text-only documents (FREE, 4000x faster)
  - FULL_VISION: For scanned documents and academic papers
  - HYBRID: For mixed content documents
  
- **Academic Paper Support**: Special handling for arXiv and academic papers
  - Keyword-based detection (theorem, lemma, proof, etc.)
  - Formula preservation via Vision API
  - LaTeX table rendering

- **Multi-Provider AI**: Support for multiple AI providers
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Anthropic (Claude Sonnet)
  - DeepSeek (DeepSeek Chat)

- **Multiple Output Formats**
  - PDF (ebook style with ReportLab)
  - PDF (academic style with LaTeX)
  - DOCX (Microsoft Word)
  - Markdown

- **Usage Statistics**: Real-time tracking of
  - Token usage
  - API costs
  - Processing time
  - Calls by provider

- **Web UI**: Modern, responsive interface
  - File upload with drag & drop
  - Real-time progress tracking
  - Download in multiple formats
  - Admin panel

#### 🐛 Bug Fixes
- Fixed PDF download with partial job ID matching
- Fixed academic paper formula detection
- Fixed table rendering in LaTeX output

#### 📊 Performance
- Text-only documents: 97% faster, 97% cheaper
- 600-page novel: ~5 minutes (vs ~3 hours)
- Optimized memory usage for large documents

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 3.3.1 | 2026-08-23 | AST-only renderer (Option A complete), cover templates, suite green + CI hardening |
| 3.3.0 | 2026-02-12 | Screenplay Studio - 12-agent pipeline |
| 2.7.0 | 2024-12-21 | Initial public release |

---

## Upgrade Guide

### From scratch
```bash
git clone https://github.com/nclamvn/dich-tai-lieu.git
cd dich-tai-lieu
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn api.main:app --port 3001
```

---

## Support

- 📝 [Issues](https://github.com/nclamvn/dich-tai-lieu/issues)
- 💬 [Discussions](https://github.com/nclamvn/dich-tai-lieu/discussions)
