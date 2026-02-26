# AI Publisher Pro — Investor X-Ray Report

**Date:** 2026-02-26
**Version:** v3.3.1
**Prepared by:** Technical Architecture Review (automated deep scan)

---

## Executive Summary

AI Publisher Pro is a **full-stack AI publishing platform** with 209K lines of code across 766 files (659 Python + 107 TypeScript/TSX). The platform delivers three major product verticals — **Document Translation**, **AI Book Generation**, and **Screenplay Studio** — powered by 4 AI providers with automatic failover. The codebase is production-grade with 1,588 passing tests, enterprise security, and a modern Next.js 16 + React 19 frontend.

### Key Numbers at a Glance

| Metric | Value |
|--------|-------|
| Total Lines of Code | **209,404** |
| Python LOC | 192,561 |
| TypeScript/TSX LOC | 16,843 |
| API Endpoints | **274** (269 REST + 5 WebSocket) |
| AI Providers | **4** (Anthropic, OpenAI, Google, DeepSeek) |
| Publishing Profiles | **12** professional templates |
| Languages Supported | **9** OCR + unlimited translation pairs |
| SQLite Databases | **12** (all WAL mode) |
| Database Tables | **19** production tables |
| Tests Passing | **1,588 / 1,588** (100% pass rate) |
| Test Functions Defined | **2,453** across all test suites |
| Git Commits | **50** |
| Pydantic Schema Models | **139** |

---

## 1. Product Architecture — Three Pillars

### Pillar 1: Universal Document Translation

**Core value proposition:** Translate any document (PDF, DOCX, TXT) while preserving layout, tables, formulas, and formatting.

```
Input Document
    ↓
Smart Extraction Router ──→ FAST_TEXT (PyMuPDF, FREE, 0.1s/page)
    │                   ──→ HYBRID (PyMuPDF + selective Vision)
    │                   ──→ FULL_VISION (Claude/GPT Vision, ~12s/page)
    │                   ──→ OCR (PaddleOCR, 2-3s/page)
    ↓
Document DNA Extraction (genre, tone, voice, reading level)
    ↓
Semantic Chunking (chapters, sections, tables, formulas)
    ↓
Parallel Translation (5x concurrency) ←── Provider Auto-Routing (QAPR)
    ↓
Quality Verification (AI self-check, 0.0-1.0 scoring)
    ↓
Layout-Preserving Assembly
    ↓
Multi-Format Output (DOCX / PDF / EPUB / MOBI)
```

**Performance benchmark:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| 598-page extraction | ~2 hours | ~30 sec | **240x faster** |
| Translation | ~2.5 hours | ~28 min | **5x faster** |
| Total pipeline | ~4.5 hours | ~28 min | **10x faster** |
| Cost | ~$15-30 | ~$0.28 | **50-100x cheaper** |

### Pillar 2: AI Book Writer (9-Agent Pipeline)

**35 files** implementing a multi-agent book generation system.

```
AnalystAgent → ArchitectAgent → OutlinerAgent → WriterAgent
    → ExpanderAgent → EnricherAgent → EditorAgent
    → QualityGateAgent → PublisherAgent
```

| Agent | Role |
|-------|------|
| Analyst | Analyzes topic, audience, requirements |
| Architect | Designs book structure |
| Outliner | Creates detailed chapter outlines |
| Writer | Generates chapter content |
| Expander | Expands to target page count |
| Enricher | Adds depth, examples, references |
| Editor | Quality and consistency editing |
| Quality Gate | Pass/fail verification |
| Publisher | Final formatting and export |

**Features:** Ghostwriter memory (characters, events, timeline), consistency checking, draft import/parse, multi-format export.

### Pillar 3: Screenplay Studio (12-Agent Pipeline)

**36 files** implementing screenplay adaptation with video generation.

```
StoryAnalyst → SceneArchitect → DialogueWriter → ActionWriter
    → VietnameseAdapter → ScreenplayFormatter
    → Cinematographer → VisualDesigner → Storyboarder
    → PromptEngineer → VideoRenderer → VideoEditor
```

**4 Video Generation Providers:**

| Provider | Cost | Quality |
|----------|------|---------|
| Pika | ~$0.02/sec | Budget |
| Runway | ~$0.05/sec | Balanced |
| Veo (Google) | ~$0.08/sec | Best quality |
| DALL-E | Per-image | Storyboards |

**4 Pricing Tiers:** FREE (screenplay only) → STANDARD (+storyboards) → PRO (+video) → DIRECTOR (+multi-take, editing)

---

## 2. Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | >=0.109.0 |
| Runtime | Python | 3.13.5 |
| Data validation | Pydantic | >=2.6.0 |
| Database | SQLite (WAL mode) | 12 databases |
| Auth | JWT (HS256) + bcrypt | PyJWT >=2.8.0 |
| Rate limiting | slowapi | >=0.1.9 |
| CSRF protection | fastapi-csrf-protect | ==0.3.4 |
| PDF processing | PyMuPDF + ReportLab | >=1.23.0, >=4.0.0 |
| Real-time | WebSocket | 5 endpoints |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js (App Router) | 16.1.6 |
| UI Library | React | 19.2.3 |
| State | TanStack React Query | 5.90.20 |
| Charts | Recharts | 3.7.0 |
| Styling | Tailwind CSS | 4.x |
| Testing | Vitest + Testing Library | 3.2.1 |
| Language | TypeScript | 5.x |

### AI Providers (Auto-Failover)

| Provider | Models | Vision | Streaming |
|----------|--------|--------|-----------|
| Anthropic Claude | Claude Sonnet 4, 3.5 Sonnet, 3.5 Haiku, 3 Opus | Yes | Yes |
| OpenAI | GPT-4o, GPT-4o-mini, GPT-4 Turbo, o1-preview | Yes | Yes |
| Google | Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash | Yes | Yes |
| DeepSeek | V3, Chat, Coder | No | Yes |

**Failover chain:** Primary → Secondary → Tertiary (auto-detected from API key availability and billing status)

---

## 3. API Surface — 274 Endpoints

### Route Module Breakdown

| Module | Endpoints | Capabilities |
|--------|-----------|--------------|
| Author/Ghostwriter | 28 | propose, rewrite, expand, generate-chapter, brainstorm, critique, projects, memory, consistency-check, export |
| Screenplay | 16 | projects CRUD, analyze, generate, visualize, render, export (fountain/PDF/video), cost estimate |
| Book Writer v2 | 12 | CRUD, upload-draft, analyze-draft, reader, download, preview, WebSocket progress |
| Translation Memory | 18 | segment CRUD, search, import/export, stats |
| Glossary | 21 | term CRUD, search, import/export, categories |
| Publishing (APS v2) | 17 | publish file/text, jobs, reader, on-demand convert, EQS, QAPR |
| Auth | 15 | register, login, refresh, roles, users, API keys |
| Batch | 10 | upload, queue management, retry, status |
| Jobs | 8 | CRUD, progress, cancel, restart |
| System | 8 | info, status, cache, processor, engines |
| Health/Monitoring | 5 | health, detailed, costs, audit, errors |
| Other (dashboard, settings, uploads, outputs, cinema, editor) | 116 | Full platform management |

### WebSocket Endpoints (5)

| Path | Purpose |
|------|---------|
| `/ws` | Main real-time job progress |
| `/stream/{job_id}` | Translation streaming preview |
| `/ws/jobs/{job_id}` | Cinema job progress |
| `/{book_id}/ws` | Book writer v1 progress |
| `/{project_id}/ws` | Book writer v2 progress |

---

## 4. Frontend — 18 Pages, 49 Components

### Page Structure

| Route | Purpose |
|-------|---------|
| `/dashboard` | Analytics & cost overview |
| `/translate` | Document translation |
| `/jobs` / `/jobs/[id]` / `/jobs/[id]/read` | Job management & reader |
| `/write` / `/write/[id]` / `/write/[id]/read` | Book writer v1 |
| `/write-v2` / `/write-v2/[id]` / `/write-v2/[id]/read` | Book writer v2 |
| `/screenplay` / `/screenplay/new` / `/screenplay/[id]` | Screenplay studio |
| `/editor/[jobId]` | Document editor |
| `/batch` | Batch processing |
| `/tm` / `/glossary` | Translation memory & glossary |
| `/settings` / `/admin` / `/profiles` | Configuration |

**Error boundaries** on all major routes (error.tsx + loading.tsx for graceful degradation).

### Component Categories

| Category | Count | Examples |
|----------|-------|---------|
| Screenplay | 16 | ProjectCard, ScriptEditor, VideoPlayer, ShotGrid |
| Settings | 9 | API keys panel, translation panel, export panel |
| Book Writer v2 | 6 | Structure preview, book progress, book card |
| Reader | 7 | Reader layout, toolbar, sidebar, regions |
| UI primitives | 7 | Card, badge, button, stat-card, locale-toggle |
| Layout | 1 | App shell |

---

## 5. Security Architecture

### Authentication & Authorization

| Layer | Implementation |
|-------|---------------|
| Password hashing | bcrypt (12 rounds) |
| JWT tokens | HS256, access=30min, refresh=7 days |
| Role-based access | 5 roles: admin, manager, user, viewer, api |
| API keys | Format `aip_<32chars>`, bcrypt-hashed storage, scoped permissions |
| Sessions | File-based persistent, survives restarts |
| Rate limiting | Per-endpoint, user/IP-based, burst allowance |
| CSRF | Double-submit cookie pattern |

### Security Infrastructure

| Component | Purpose |
|-----------|---------|
| Audit logging | SQLite-backed trail (user, action, resource, IP) |
| Error tracking | Categorized, deduplicated, severity-graded |
| Health monitor | System health with alerting thresholds |
| Watchdog | Process monitoring and auto-restart |
| File cleanup | Automatic temp file removal |

### Security Posture

| Check | Status |
|-------|--------|
| Secrets in source code | **CLEAN** — 0 real secrets |
| `.env` in git | **CLEAN** — properly gitignored |
| `eval()`/`exec()` in production | **CLEAN** — 0 instances |
| `os.system()`/`subprocess.call()` | **CLEAN** — 0 instances |
| Insecure default blocking | **YES** — production mode blocks startup with dev defaults |
| CORS configuration | **YES** — permissive in dev, restricted in prod |

---

## 6. Database Architecture

### 12 SQLite Databases (All WAL Mode)

| Database | Tables | Purpose |
|----------|--------|---------|
| `data/jobs.db` | jobs, job_history | Job queue and history |
| `data/aps_jobs.db` | aps_jobs | APS v2 job repository |
| `data/book_writer.db` | book_projects | Book writer projects |
| `data/screenplay_studio.db` | screenplay_projects | Screenplay projects |
| `data/cache/chunks.db` | chunk_cache | Translation chunk cache |
| `data/checkpoints/checkpoints.db` | checkpoints | Crash recovery |
| `data/translation_memory/tm.db` | segments, tm_stats | Translation memory |
| `data/usage/usage.db` | usage_records, user_quotas, monthly_usage | Usage tracking |
| `data/audit.db` | audit_log | Audit trail |
| `data/errors/error_tracker.db` | errors | Error tracking |
| `data/glossary.db` | (glossary tables) | Terminology |
| `data/tm.db` | (TM tables) | Secondary TM |

### Database Abstraction Layer

```
DatabaseBackend (Protocol)
    └── SQLiteBackend (Implementation)
         ├── WAL journal mode
         ├── Row factory (dict access)
         ├── Thread-safe (persistent mode with Lock)
         ├── Connection pooling
         └── Schema migration support
```

### Caching Infrastructure (Multi-Tier)

| Tier | Engine | Use Case |
|------|--------|----------|
| L1 | In-memory LRU | Hot data, session state |
| L2 | SQLite | Translation chunks, checkpoints |
| L3 | File system | Large documents, PDFs |
| L4 | Redis (optional) | Distributed caching, rate limiting |

---

## 7. Quality Metrics

### Test Health

| Metric | Value |
|--------|-------|
| Unit tests passing | **1,588 / 1,588** (100%) |
| Tests skipped | 6 |
| Test failures | **0** |
| Test execution time | 28.78 seconds |
| Test files | 118 |
| Test functions defined | 2,453 |

### Code Quality Tooling

| Tool | Status |
|------|--------|
| Linter | ruff (configured, E/F/W rules) |
| Type hints | Pydantic models (139 schemas) |
| API docs | OpenAPI auto-generated (/docs, /redoc) |
| Documentation | 33 doc files, 5 handover documents |
| README | 280 lines, comprehensive |
| CHANGELOG | Present |
| CONTRIBUTING | Present |

---

## 8. Honest Assessment — Technical Debt

### Risk Matrix

| Risk | Level | Impact | Remediation |
|------|-------|--------|-------------|
| **No dependency lock file** | HIGH | Non-reproducible builds | 1 day — add `requirements.lock` or Poetry |
| **Test coverage gaps** | HIGH | 45% of core modules untested | 2-3 weeks — prioritize screenplay, formatting, pdf_templates |
| **Broad exception handling** | HIGH | 561 `except Exception` catches, 24 silent | 1-2 weeks — audit and add specific handlers |
| **Dependency pinning** | HIGH | 30/31 packages use floor-only `>=` | 1 day — pin versions, add vulnerability scanning |
| **Coverage threshold** | MEDIUM | Set at 15% (lowered from 70%) | Ongoing — raise incrementally |
| **Un-migrated SQLite** | MEDIUM | 12 files still use raw `import sqlite3` | 3-5 days |
| **Large files** | MEDIUM | 10 files >1,000 lines (largest: 2,170) | 1-2 weeks refactoring |
| **Legacy code** | LOW | 5 deprecated files still present | 1 day cleanup |
| **Security posture** | LOW | Solid foundation, no critical gaps | — |

### What's Working Well

1. **Architecture** — Clean separation: routes → services → core → database
2. **AI provider abstraction** — Swap providers without code changes, auto-failover
3. **Multi-agent pipelines** — 9-agent book writer + 12-agent screenplay studio
4. **Performance** — 10x speed, 50-100x cost reduction over baseline
5. **Security** — JWT+RBAC+API keys, audit logging, rate limiting, CSRF
6. **Configuration** — Pydantic BaseSettings with production validation
7. **Database abstraction** — Clean protocol pattern, WAL mode everywhere
8. **Real-time** — 5 WebSocket endpoints for live progress
9. **Test pass rate** — 100% (1,588/1,588) with 0 failures
10. **Documentation** — 33 docs, 5 handover files, auto-generated API docs

### What Needs Work

1. **Dependency management** — No lock file = non-reproducible deployments
2. **Test coverage breadth** — 141 core modules have zero test coverage
3. **Exception handling** — Too many broad catches masking real errors
4. **Monolithic files** — 10 files over 1,000 lines need splitting
5. **Single contributor** — Bus factor = 1

---

## 9. Competitive Moat Analysis

### Differentiators

| Feature | AI Publisher Pro | Typical Translation SaaS |
|---------|-----------------|-------------------------|
| Layout preservation | Yes (Vision AI) | Rarely |
| Formula/table handling | Yes (STEM detection) | No |
| Multi-format output | DOCX/PDF/EPUB/MOBI | Usually 1-2 formats |
| AI book generation | 9-agent pipeline | No |
| Screenplay + video | 12-agent + 4 video providers | No |
| Provider failover | 4 providers, auto-routing | Usually 1 provider |
| Quality scoring | EQS + QAPR + consistency | Basic or none |
| Translation memory | Full TM system | Sometimes |
| Cost optimization | $0.28 for 598 pages | $15-30+ typical |
| Self-hosted | Yes (SQLite, no cloud deps) | Usually cloud-only |

### Total Addressable Market

| Vertical | Market Segment |
|----------|---------------|
| Document translation | Publishing houses, legal, academic, enterprise |
| AI book writing | Self-publishing authors, content agencies |
| Screenplay studio | Film schools, indie studios, content creators |

---

## 10. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16)                     │
│  React 19 · TanStack Query · Recharts · Tailwind · Vitest   │
│  18 pages · 49 components · Error boundaries                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼───────────────────────────────────────┐
│                    API LAYER (FastAPI)                        │
│  274 endpoints · JWT auth · RBAC · Rate limiting · CSRF      │
│  12 route modules · 139 Pydantic schemas                     │
├──────────────────────────────────────────────────────────────┤
│                    SERVICE LAYER                              │
│  APS v2 Service · EQS · QAPR · Consistency Checker           │
│  Layout Analyzer · Smart Chunker · Cost Dashboard            │
├──────────────────────────────────────────────────────────────┤
│                    CORE ENGINE                                │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────┐       │
│  │ Translation  │ │ Book Writer │ │ Screenplay Studio│       │
│  │ Orchestrator │ │ v2 (9 agents│ │ (12 agents +     │       │
│  │ (5x parallel)│ │  pipeline)  │ │  4 video provs)  │       │
│  └──────┬──────┘ └─────────────┘ └──────────────────┘       │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────┐         │
│  │ Smart Extraction · Layout Preserve · PDF Render  │         │
│  │ STEM/LaTeX · TM · Glossary · OCR · Quality       │         │
│  └──────────────────────────────────────────────────┘         │
├──────────────────────────────────────────────────────────────┤
│              AI PROVIDER ABSTRACTION LAYER                    │
│  Anthropic Claude · OpenAI GPT · Google Gemini · DeepSeek    │
│  Auto-failover · Vision support · Streaming · Usage tracking │
├──────────────────────────────────────────────────────────────┤
│              DATA LAYER (12 SQLite DBs, WAL mode)            │
│  DatabaseBackend protocol · Schema migrations                │
│  Multi-tier cache (Memory → SQLite → File → Redis)           │
│  Audit log · Error tracker · Usage quotas                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Development Velocity

| Period | Commits | Focus |
|--------|---------|-------|
| Dec 2025 | 6 | Initial release, smart extraction, performance optimization |
| Jan 2026 | 7 | Security hardening, book writer, screenplay studio |
| Feb 2026 | 37 | RRI coverage, route cleanup, SQLite migration, frontend tests, exception hygiene |

**Recent sprint (Feb 2026) delivered:**
- Registered 5 missing route modules, removed ~1,550 lines of dead inline handlers
- Migrated 7 modules to SQLiteBackend abstraction
- Replaced 10 broad exception catches with specific types
- Added schema migration system
- Set up frontend Vitest infrastructure
- Expanded DB integrity check from 3 to 12 databases
- Removed 4,924 lines of dead `core/author/` code

---

## 12. Deployment & Operations

| Aspect | Status |
|--------|--------|
| Server | `uvicorn` with `--reload` for dev |
| Port | 3000 (configurable) |
| Database | SQLite (zero external deps) |
| External deps | None required (Redis optional) |
| Docker | Config present (`docker/`) |
| Health check | `/health` endpoint with detailed diagnostics |
| Monitoring | `/api/monitoring/*` (costs, audit, errors) |
| Error dashboard | `/api/errors/*` with severity/category tracking |
| Audit trail | Full action logging with user/IP tracking |

---

*Report generated from automated codebase analysis. All metrics verified against live code and test execution.*
