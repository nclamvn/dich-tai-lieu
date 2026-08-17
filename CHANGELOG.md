# Changelog

All notable changes to AI Publisher Pro will be documented in this file.

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
