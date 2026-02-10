# AI Publisher Pro — X-Ray Report

**Date:** 2026-02-10
**Version:** 3.0
**Score:** 9.8/10 (Production Ready)

---

## 1. Project Overview

AI Publisher Pro is a full-stack AI-powered document translation and book authoring platform. It combines a FastAPI backend with a Next.js 16 React frontend, supporting multi-provider AI (OpenAI, Anthropic, Gemini, DeepSeek) for intelligent document processing.

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~180,000 |
| Python Files | 562 |
| TypeScript/TSX Files | 46 |
| Test Files | 119 |
| API Endpoints | ~200+ |
| Frontend Pages | 13 |
| SQLite Databases | 8 |
| Git Commits | 26 |
| AI Providers | 4 |
| Supported Languages | 10 |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 16 Frontend                   │
│  React 19 · React Query 5 · Tailwind 4 · TypeScript 5  │
│  13 pages · 15 components · WebSocket real-time         │
├─────────────────────────────────────────────────────────┤
│                     FastAPI Backend                      │
│  44 routers/services · WebSocket · Background Tasks     │
├────────────┬────────────┬───────────┬───────────────────┤
│ Translation│ Book Writer│ Glossary  │ Auth & Monitoring  │
│ Pipeline   │ Pipeline   │ & TM      │ Keys · Usage · Err │
├────────────┴────────────┴───────────┴───────────────────┤
│              Core Processing Engine                      │
│  Smart Extraction · Semantic Chunker · Layout Preserve  │
│  Vision Reader · Quality Verifier · Output Converter    │
├─────────────────────────────────────────────────────────┤
│              AI Provider Abstraction                     │
│  OpenAI · Anthropic · Gemini · DeepSeek                 │
│  Auto-fallback · Vision support · Cost tracking         │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  8 SQLite DBs · Redis (optional) · File Storage         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
ai-publisher-pro-public/
├── api/                    # FastAPI app (44 modules)
│   ├── main.py            # App entry, middleware, WebSocket
│   ├── routes/            # Modular routers (9 modules)
│   ├── services/          # Shared services (17 modules)
│   ├── book_writer_*.py   # Book writing API (4 modules)
│   └── aps_v2_*.py        # V2 publishing API (3 modules)
├── core/                   # Core business logic (301 files)
│   ├── smart_extraction/  # PDF routing (FAST/HYBRID/VISION/OCR)
│   ├── book_writer/       # 7-agent pipeline
│   ├── database/          # Database abstraction layer
│   ├── editorial/         # Consistency & intent mapping
│   ├── pdf_templates/     # 11 genre templates
│   └── ...                # 70+ other modules
├── core_v2/               # Universal Publishing Pipeline
│   ├── orchestrator.py    # Main pipeline orchestrator
│   ├── document_dna.py    # Claude-extracted metadata
│   └── ...                # Vision, chunker, verifier
├── ai_providers/          # Multi-provider abstraction
│   ├── unified_client.py  # Auto-fallback orchestration
│   └── *_provider.py      # 4 provider implementations
├── frontend/              # Next.js 16 app
│   └── src/
│       ├── app/           # 13 pages (App Router)
│       ├── components/    # 15 components (layout, reader, UI)
│       └── lib/           # API client, hooks, theme, i18n
├── config/                # Pydantic settings
├── data/                  # 8 SQLite databases
├── tests/                 # 119 test files
└── docs/                  # Handover & X-Ray reports
```

---

## 4. Completed Sprints & Features

### Sprint 1 — Technical Debt Elimination
- CI/CD pipeline with GitHub Actions
- Database abstraction layer (`DatabaseBackend` protocol + SQLite backend)
- Redis integration with in-memory fallback
- Codebase cleanup (340MB → 75MB, -78%)
- Backup and restore system

### Sprint 2 — Test Coverage
- 230+ unit tests across all modules
- pytest configuration with coverage thresholds
- Test fixtures for database, API, and AI providers

### Sprint 3 — Security Hardening
- Session authentication (JWT + cookie-based)
- API key management with scoped permissions
- CSRF protection
- Rate limiting (slowapi)
- Input validation and sanitization

### Sprint 4 — Bug Fixes
- Fixed `test_parallel.py` real API call issues
- Resolved silent exceptions in background tasks
- SyntaxWarning fixes

### Sprints 5-9 — Route Extraction & Pipeline
- Route extraction and modular router architecture
- EQS (Extraction Quality Scoring) engine
- Smart provider routing (QAPR)
- Pipeline integration and optimization
- Batch processing system

### Sprints 10-15 — Service Modules & React Frontend
- Next.js 16 frontend with React 19
- React Query for server state management
- 13 pages: Translate, Jobs, Write, Glossary, Dashboard, Profiles, Settings
- Component library: Button, Card, Badge, EmptyState, StatCard
- Translation job workflow (upload → translate → download/read)
- Cost analytics dashboard with Recharts
- Glossary management with bulk import/export

### Sprint 15.5 — Notion UI Overhaul
- Notion-inspired design system with CSS custom properties
- Instrument Serif display font
- Collapsible sidebar with localStorage persistence
- V2 job APIs with quality metrics (EQS, QAPR, Consistency)
- Translation language fix and detection
- Vietnamese i18n (480+ translation keys)
- In-app document reader (premium reading experience)

### Sprint 16 — Book Writer Pipeline
- **7-Agent Pipeline**: Analyst → Architect → Outliner → Writer → Enricher → Editor → Publisher
- **3 Input Modes**: From Ideas (seeds), Clean Up Draft (messy_draft), Enrich Draft (enrich)
- File upload with drag-and-drop for draft documents
- Outline approval workflow with chapter editing
- Real-time progress via WebSocket (per-chapter tracking)
- Chapter status tracking: pending → written → enriched → edited
- Auto-resume stalled projects on server restart
- In-app book reader (reuses ReaderLayout component)
- DOCX + Markdown output with download
- Pydantic serialization fix (`_to_dict` helper for model/dict handling)

### Sprint 16.5 — Global Dark Mode
- Dark/light theme toggle for entire application
- Notion-inspired dark palette (CSS custom properties)
- OS `prefers-color-scheme` detection on first visit
- Persists to localStorage
- Theme toggle in sidebar footer + mobile header
- Reader keeps independent theme (light/sepia/dark)

---

## 5. Feature Matrix

| Feature | Status | Details |
|---------|--------|---------|
| Document Translation | Done | PDF, DOCX, TXT, MD, EPUB → 6 output formats |
| Smart PDF Extraction | Done | FAST_TEXT/HYBRID/FULL_VISION/OCR routing |
| Parallel Translation | Done | 5x concurrency, 598p in 28min |
| Auto-Fallback | Done | OpenAI → Anthropic → DeepSeek → Gemini |
| Vision Fallback | Done | Claude Vision → OpenAI Vision for STEM |
| Book Writer | Done | 7-agent pipeline, 3 input modes |
| Draft Upload | Done | TXT/MD/DOCX upload with drag-and-drop |
| In-App Reader | Done | Premium reader for jobs + books |
| Glossary Management | Done | CRUD, bulk import, term matching |
| Translation Memory | Done | Fuzzy matching at 85% threshold |
| Cost Analytics | Done | Per-provider, per-language-pair breakdown |
| Real-time Progress | Done | WebSocket + polling fallback |
| Dark Mode | Done | Global toggle, OS detection, localStorage |
| Vietnamese i18n | Done | 480+ keys, EN/VI bilingual |
| Batch Processing | Done | Multi-file queue with priority |
| API Key Auth | Done | Scoped keys with CRUD management |
| Error Tracking | Done | Centralized dashboard |
| Publishing Profiles | Done | 20+ genre templates |
| Auto-Resume | Done | Stalled jobs restart on server boot |
| Checkpoint Recovery | Done | Resume interrupted translations |

---

## 6. API Endpoints Summary

### Translation (`/api/v2/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/publish` | Upload & translate document |
| GET | `/api/v2/jobs` | List translation jobs |
| GET | `/api/v2/jobs/{id}` | Get job details |
| DELETE | `/api/v2/jobs/{id}` | Delete job |
| GET | `/api/v2/jobs/{id}/reader-content` | Get reader content |
| GET | `/api/v2/profiles` | List publishing profiles |
| POST | `/api/v2/detect-language` | Detect source language |

### Book Writer (`/api/v2/books/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/books/` | Create book project |
| GET | `/api/v2/books/` | List book projects |
| GET | `/api/v2/books/{id}` | Get project detail |
| DELETE | `/api/v2/books/{id}` | Delete project |
| POST | `/api/v2/books/{id}/approve` | Approve outline |
| GET | `/api/v2/books/{id}/chapters/{n}` | Get chapter |
| PUT | `/api/v2/books/{id}/chapters/{n}` | Edit chapter |
| POST | `/api/v2/books/{id}/chapters/{n}/regenerate` | Regenerate chapter |
| GET | `/api/v2/books/{id}/reader-content` | Book reader |
| POST | `/api/v2/books/upload-draft` | Upload draft file |
| GET | `/api/v2/books/{id}/download/{fmt}` | Download book |
| WS | `/api/v2/books/{id}/ws` | Real-time progress |

### Glossary (`/api/glossary/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/glossary/` | Create glossary |
| GET | `/api/glossary/` | List glossaries |
| GET | `/api/glossary/{id}` | Get glossary |
| DELETE | `/api/glossary/{id}` | Delete glossary |
| POST | `/api/glossary/{id}/terms` | Add term |
| DELETE | `/api/glossary/{id}/terms/{eid}` | Remove term |
| POST | `/api/glossary/{id}/terms/bulk` | Bulk import |

### Dashboard (`/api/dashboard/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/overview` | Cost summary |
| GET | `/api/dashboard/providers` | Provider breakdown |
| GET | `/api/dashboard/language-pairs` | Language pair costs |

### Other
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| WS | `/ws` | Job progress WebSocket |
| POST | `/api/auth/login` | Session auth |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/keys` | Create API key |
| GET | `/api/keys` | List API keys |

---

## 7. Frontend Pages

| Page | Path | Description |
|------|------|-------------|
| Landing | `/` | Hero, 10-step pipeline, features, stats |
| Translate | `/translate` | Upload, configure, start translation |
| Jobs | `/jobs` | Job list with bulk actions |
| Job Detail | `/jobs/[id]` | Quality metrics, download, reader |
| Job Reader | `/jobs/[id]/read` | Premium document reader |
| Write | `/write` | Book writer with 3 input modes |
| Book Detail | `/write/[id]` | Outline approval, chapter progress |
| Book Reader | `/write/[id]/read` | Book reading experience |
| Dashboard | `/dashboard` | Cost analytics with charts |
| Glossary | `/glossary` | Glossary list & management |
| Glossary Edit | `/glossary/[id]` | Term editor |
| Profiles | `/profiles` | Publishing profiles |
| Settings | `/settings` | App configuration |

---

## 8. Design System

### Colors (Notion-Inspired)
| Token | Light | Dark |
|-------|-------|------|
| `--bg-primary` | #FFFFFF | #191919 |
| `--bg-secondary` | #F7F6F3 | #202020 |
| `--bg-tertiary` | #F1F1EF | #2A2A2A |
| `--bg-sidebar` | #FBFBFA | #1E1E1E |
| `--fg-primary` | rgb(55,53,47) | rgba(255,255,255,0.9) |
| `--fg-secondary` | rgba(55,53,47,0.65) | rgba(255,255,255,0.6) |
| `--fg-tertiary` | rgba(55,53,47,0.45) | rgba(255,255,255,0.4) |

### Accent Colors
Blue #2383E2 · Red #EB5757 · Green #0F7B6C · Yellow #CB912F · Orange #D9730D · Purple #9065B0 · Pink #C14C8A · Brown #9F6B53

### Typography
- **Display:** Instrument Serif (Google Fonts)
- **Body:** System sans-serif stack
- **Mono:** SFMono-Regular, Menlo, Consolas

### Layout
- Content width: 900px
- Sidebar: 240px expanded / 56px collapsed
- Border radius: 4px / 6px / 8px

---

## 9. Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Python 3.11+ | Runtime |
| FastAPI | Web framework |
| Pydantic v2 | Data validation |
| SQLite | Database (8 DBs) |
| Redis (optional) | Caching layer |
| WebSocket | Real-time updates |
| asyncio | Concurrent processing |
| PyMuPDF | PDF extraction |
| python-docx | DOCX generation |
| ReportLab | PDF generation |

### Frontend
| Technology | Purpose |
|-----------|---------|
| Next.js 16 | React framework |
| React 19 | UI library |
| TypeScript 5 | Type safety |
| Tailwind CSS 4 | Styling |
| React Query 5 | Server state |
| Recharts 3 | Chart library |
| Lucide React | Icon library |

### AI Providers
| Provider | Models | Use Case |
|----------|--------|----------|
| OpenAI | gpt-4o, gpt-4o-mini | Primary translation |
| Anthropic | claude-sonnet-4 | Creative/literary, Vision |
| Google Gemini | gemini-2.0-flash | Large context |
| DeepSeek | deepseek-chat | Cost-effective fallback |

---

## 10. Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| PDF Extraction (598p) | ~2 hours | ~30 sec | 240x faster |
| Translation (598p) | ~2.5 hours | ~28 min | 5x faster |
| Total Pipeline | ~4.5 hours | ~28 min | 10x faster |
| Cost per 598p | ~$15-30 | ~$0.28 | 50x cheaper |
| Codebase Size | 340MB | 75MB | 78% smaller |

---

## 11. Database Schema

| Database | Tables | Purpose |
|----------|--------|---------|
| `data/jobs.db` | jobs, job_outputs | Translation jobs |
| `data/aps_jobs.db` | aps_jobs | V2 publishing jobs |
| `data/glossary.db` | glossaries, terms | Terminology |
| `data/books/book_writer.db` | book_projects | Book authoring |
| `data/cache/chunks.db` | chunk_cache | Translation cache |
| `data/translation_memory/tm.db` | segments | Translation memory |
| `data/checkpoints/checkpoints.db` | checkpoints | Job recovery |
| `data/errors/error_tracker.db` | errors | Error monitoring |

---

## 12. Git History

```
1d6f385 feat: Book Writer pipeline, draft upload, in-app reader, and global dark mode
80b0481 feat: Add Vietnamese i18n, collapsible sidebar, and in-app reader
d220830 docs: Add handover document for Sprint 15.5 session (2026-02-09)
f39a769 feat: Sprint 15.5 — Notion UI overhaul, V2 job APIs, translation language fix
229fad0 feat: Sprints 10-15 — Service modules, tests, and React frontend
74e557f feat: Sprints 5-9 - Route extraction, EQS engine, pipeline integration
4f1db7b fix: Sprint 4 - Fix test_parallel.py and remaining silent exceptions
ed6848f feat: Sprint 3 - Security hardening and dead code removal
c9895d8 feat: Sprint 2 - Test coverage (230 tests) + bug fixes
1c27d4e feat: Document rendering quality - i18n, skill injection, profile-template binding
c2d8b9c feat: Sprint 1 - Technical debt elimination
b44e9b4 feat: Add provider/model selection, Vision Layout toggle
ea4fb90 feat: Add image embedding, translation engines, integration bridge
3d4f096 feat: Add Vision fallback - Claude Vision → OpenAI Vision for STEM
a5e81d2 feat: Dark Mode + Mobile Responsive + E2E Tests
7380e1e feat: Professional DOCX/PDF Template Engines with API integration
f917384 feat: Commercial book exporter with professional DOCX/PDF quality
e940af9 AI Publisher Pro v2.7 - Public Release
```

---

## 13. Summary

AI Publisher Pro has evolved from a simple translation tool into a comprehensive AI publishing platform with:

- **Translation Engine** — Smart extraction, parallel processing, multi-provider AI with auto-fallback
- **Book Writer** — Full authoring pipeline from idea seeds to polished DOCX output
- **Premium Reader** — In-app document reading with theme, font, and layout controls
- **Design System** — Notion-inspired UI with dark/light mode, Vietnamese i18n
- **Production Infrastructure** — Error tracking, cost analytics, auto-resume, checkpoint recovery

The platform handles the entire content lifecycle: **create → translate → review → publish → read**.
