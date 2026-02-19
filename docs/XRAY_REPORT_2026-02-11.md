# AI Publisher Pro — Full Technical X-Ray Report

**Date:** 2026-02-11
**Version:** 2.8.1+
**Analyst:** Claude Code (3 parallel agents)
**Overall Score: 7.5/10**

---

## Executive Summary

| Area | Score | Critical Issues |
|------|-------|-----------------|
| Backend Architecture | 7.2/10 | Security defaults, memory leaks, 8 SQLite DBs |
| Frontend Architecture | 8.2/10 | No error boundaries, no tests, accessibility gaps |
| Tests & Infrastructure | 6.5/10 | Coverage at 10%, no migrations, 18 lint rules ignored |

**Total Files:** 265+ Python, 47+ TypeScript/TSX
**Total Functions:** 3,000+ Python, 40+ React hooks
**API Endpoints:** 230 route handlers across 25 files
**Databases:** 8 SQLite files

---

## Part 1: Backend Architecture

### 1.1 API Layer (`api/`)

**Structure:** 25 route files, 230 endpoint handlers

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `aps_v2_router.py` | 16 | Main translation service |
| `routes/author.py` | 29 | Author/book writer |
| `glossary_router.py` | 21 | Glossary management |
| `tm_router.py` | 18 | Translation memory |
| `main.py` | 16 | App setup, middleware |
| `auth_router.py` | 15 | Authentication |
| `book_writer_router.py` | 12 | Book Writer v1 |
| `routes/book_writer_v2.py` | 12 | Book Writer v2 |
| `error_dashboard_router.py` | 10 | Error monitoring |
| `batch_router.py` | 7 | Batch processing |

**Issues Found:**
- `aps_v2_service.py`: Jobs stored in `_jobs` dict in memory indefinitely (memory leak)
- `aps_v2_service.py:279`: API key stored in job record (security risk)
- Many `except Exception` blocks swallow errors silently
- No input validation for file magic bytes (only extension check)
- No path traversal sanitization on uploaded filenames

### 1.2 AI Providers (`ai_providers/`)

**unified_client.py (755 lines) — Score: 9/10**

Best-designed module in the codebase. Features:
- Auto-fallback: OpenAI -> Anthropic -> DeepSeek -> Gemini
- Vision support: Claude Vision -> OpenAI Vision -> Gemini Vision
- Smart error classification (billing, rate limit, invalid key)
- Usage tracking with cost estimation

**Issues:**
- `_current_provider` mutable without lock (race condition in async)
- `_failed_providers` set never cleared (providers permanently blacklisted)
- Cost rates hardcoded (will become outdated)

### 1.3 Core Modules (`core/`)

**2,937 functions across 265 files**

| Module | LOC | Quality | Purpose |
|--------|-----|---------|---------|
| `smart_extraction/` | ~600 | 8.5/10 | PDF routing (240x faster extraction) |
| `layout_preserve/` | ~500 | 7/10 | LLM layout-preserving translation |
| `pdf_renderer/` | ~800 | 7.5/10 | Markdown+LaTeX to PDF/DOCX |
| `book_writer_v2/` | ~2,500 | 8/10 | 9-agent book pipeline |
| `database/` | ~100 | 9/10 | Protocol-based DB abstraction |
| `batch_processor.py` | ~1,600 | 6/10 | Legacy batch (largest file) |

**Key Issues:**
- `core/` and `core_v2/` coexist (architectural confusion)
- No async database operations (blocks event loop)
- No connection pooling for SQLite
- Book Writer v2 has no checkpointing (crash = restart from zero)

### 1.4 Translation Orchestrator (`core_v2/orchestrator.py`)

**980 lines — Score: 8.5/10**

Pipeline: Input -> Vision Reading -> DNA Extraction -> Chunking -> Translation -> Assembly -> Conversion

**Strengths:** Excellent Japanese support, LaTeX preservation, parallel translation
**Issues:**
- Default concurrency = 1 (very conservative)
- Translation errors return placeholder string instead of raising
- Simple join bypasses quality checks for >15k chars

### 1.5 Data Layer

**8 SQLite Databases:**

| Database | Purpose |
|----------|---------|
| `data/jobs.db` | Legacy jobs |
| `data/aps_jobs.db` | APS V2 jobs |
| `data/book_writer.db` | Book projects |
| `data/glossary.db` | Glossary terms |
| `data/translation_memory/tm.db` | TM segments |
| `data/cache/chunks.db` | Translation cache |
| `data/checkpoints/checkpoints.db` | Resume points |
| `data/errors/error_tracker.db` | Error tracking |

**Critical:** No migration system, no schema versioning, no WAL mode, no connection pooling.

---

## Part 2: Frontend Architecture

### 2.1 Stack & Structure

**Framework:** Next.js 16.1.6 + React 19.2.3 (App Router)
**Styling:** Tailwind CSS v4 + CSS variables (Notion-inspired)
**State:** React Query + 3 Context providers (locale, theme, reader)
**i18n:** 1,000+ translation keys (EN/VI), 100% coverage

### 2.2 Pages (21 routes)

```
/                    Landing page
/translate           Upload & translate
/write               Book Writer v1
/write-v2            Book Writer Pro (9-agent)
/jobs                Job list
/jobs/[id]           Job detail
/jobs/[id]/read      In-app reader
/glossary            Glossary management
/tm                  Translation Memory
/batch               Batch upload
/dashboard           Analytics
/profiles            Publishing profiles
/settings            Configuration (6 tabs)
/editor/[jobId]      CAT tool
```

### 2.3 API Integration

**client.ts (899 lines):** 12 resource namespaces, 50+ endpoints
**hooks.ts (866 lines):** 40+ React Query hooks with caching, polling, mutations
**types.ts (809 lines):** Comprehensive TypeScript interfaces

**WebSocket:** 3 implementations (jobs, book v1, book v2) with auto-reconnect

### 2.4 Design System

- Custom CSS variables for all colors, spacing, shadows, radii
- Full dark mode via `.dark` class + variable overrides
- Notion-inspired aesthetic (clean, minimal, professional)
- Responsive with collapsible sidebar

### 2.5 Frontend Issues

**Critical:**
- No error boundaries (app crashes on component errors)
- No `loading.tsx` files for slow pages
- No code splitting (single large bundle ~350KB gzipped)

**High:**
- 13 instances of `any` type usage
- No `aria-label` on 30+ icon-only buttons
- No keyboard navigation for custom dropdowns
- WebSocket reconnect without exponential backoff

**Medium:**
- No runtime validation (no Zod for API responses)
- No virtualization for long lists
- Recharts (~100KB) loaded even when not needed
- No Tailwind config file (using v4 defaults)

**Testing:** Zero frontend test files.

---

## Part 3: Tests & Infrastructure

### 3.1 Test Suite

| Metric | Value |
|--------|-------|
| Test files | 119 |
| Test functions | 644+ |
| Fixtures | 160+ |
| Coverage threshold | **10%** (lowered from 70%) |
| Categories | unit, integration, e2e, stress, regression |

**Book Writer v2 Tests:** Only 50% agent coverage (4/9 agents tested). No integration tests for the parallelized pipeline.

### 3.2 Linting (ruff.toml)

**18 rules ignored** including dangerous ones:
- `E722` (bare except) — hides bugs
- `F821` (undefined name) — runtime errors
- `F841` (unused variable) — dead code
- `F401` (unused import) — import side-effects

### 3.3 Dependencies

**Outdated:**
- `anthropic` 0.25.0 (current: 0.50+)
- `fastapi` 0.109.0 (current: 0.115+)
- No dependency pinning (`>=` instead of `==`)
- No vulnerability scanning

### 3.4 Documentation

**19 docs files** — Excellent handover discipline (Feb 3, 9, 11 reports).

**CLAUDE.md inaccuracies:**
- "Tests: 883+" — Actual: 644+
- Port numbers inconsistent (3000/3001/8000)

---

## Part 4: Security Assessment

### Critical Vulnerabilities (P0)

| # | Issue | File | Impact |
|---|-------|------|--------|
| 1 | **Hardcoded secrets** | `config/settings.py:60-66` | Session hijacking if deployed as-is |
| 2 | **Security disabled by default** | `security_mode = "development"` | All endpoints unprotected |
| 3 | **API key stored in job records** | `aps_v2_service.py:279` | Key leakage via job queries |
| 4 | **In-memory sessions** | `api/security.py:44` | All users logged out on restart |
| 5 | **No rate limiting on auth** | `api/security.py` | Brute force attacks |

### High Priority (P1)

| # | Issue | Impact |
|---|-------|--------|
| 1 | No content-type validation on uploads | Malicious file upload |
| 2 | No path traversal sanitization | File system access |
| 3 | CORS origins hardcoded (16 URLs) | Should be env vars |
| 4 | Temp files never cleaned up | Disk space exhaustion |
| 5 | No CSRF by default | Cross-site attacks |

---

## Part 5: Performance Analysis

### Bottlenecks

| Area | Issue | Impact |
|------|-------|--------|
| Database | No connection pooling, sync I/O | Blocks event loop |
| Memory | Jobs stored indefinitely in `_jobs` dict | Memory leak |
| AI | Default concurrency=1 in orchestrator | 5x slower than needed |
| Files | Full documents loaded in memory | OOM on large PDFs |
| Pipeline | Book Writer v2 no checkpointing | Crash = full restart |

### Estimated Capacity (Current)
- Concurrent jobs: ~10-20
- File size: ~50MB
- Users: ~100 concurrent sessions

---

## Part 6: Recommendations by Priority

### P0 — Security (Block Production) — 3 days
1. Force strong secrets in production mode
2. Move CORS origins to environment variables
3. Remove API key from job persistence
4. Add rate limiting to auth endpoints
5. Add path traversal sanitization to uploads

### P1 — Stability — 1 week
1. Implement job cleanup (TTL + max capacity)
2. Add error boundaries to frontend
3. Enable WAL mode on all SQLite databases
4. Add `loading.tsx` for slow pages
5. Fix broad `except Exception` patterns

### P2 — Performance — 2 weeks
1. Increase orchestrator default concurrency to 5
2. Add connection pooling (aiosqlite)
3. Consolidate 8 databases to 3
4. Add code splitting / lazy loading in frontend
5. Implement Book Writer v2 checkpointing

### P3 — Technical Debt — 1 month
1. Increase test coverage from 10% to 50%
2. Merge `core/` and `core_v2/`
3. Add frontend tests (Jest + Testing Library)
4. Implement database migration system (Alembic)
5. Add structured logging (JSON format)
6. Reduce ignored lint rules from 18 to 5

---

## Architecture Diagram

```
                    Frontend (Next.js 16)
                    ├── React Query hooks
                    ├── WebSocket (3 connections)
                    └── CSS Variables theme
                            │
                    ┌───────┴───────┐
                    │  FastAPI API   │
                    │  230 endpoints │
                    │  25 routers    │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        Translation    Book Writer    Glossary/TM
        Pipeline       v2 Pipeline    Services
              │             │             │
    ┌─────────┤      9 Agents (||)   8 SQLite DBs
    │         │             │
Smart      Vision      AI Adapter
Extract    Reading     (4 providers)
    │         │             │
PyMuPDF   Claude    OpenAI/Anthropic
(FREE)    Vision    DeepSeek/Gemini
```

---

## Final Verdict

**Production Readiness:**
- Current state: NOT production-ready (security issues)
- With P0 fixes (3 days): Internal deployment OK (5-10 users)
- With P0+P1 (2 weeks): SMB ready (100+ users)
- With all fixes (3 months): Enterprise ready (1000+ users)

**Strongest Areas:** AI provider abstraction (9/10), frontend design system (9/10), smart extraction routing (8.5/10)

**Weakest Areas:** Security defaults (3/10), test coverage (4/10), database architecture (5/10)
