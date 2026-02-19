# AI Publisher Pro - Project Context

## TWO REPOSITORIES (Updated 2026-02-11)

### PRIVATE (Development) — WORK HERE
- **Path**: `~/ai-publisher-pro-public`
- **Purpose**: All development, new features, bug fixes
- **Status**: ACTIVE — Phase 2 development
- **Contains**: Full history, configs, secrets, internal docs

### PUBLIC (Open Source) — DO NOT DEVELOP HERE
- **Path**: `~/Dich-Viet` (local copy)
- **GitHub**: `github.com/nclamvn/Dich-Viet`
- **Purpose**: Community sharing, releases only
- **Status**: RELEASED v3.2.0
- **Contains**: Sanitized code, no secrets

### Workflow
1. ALL development happens in `~/ai-publisher-pro-public`
2. When ready for release: `./scripts/sync_to_public.sh vX.X.X`
3. NEVER develop directly in `~/Dich-Viet`

---

## Quick Resume
Khi quay lại dự án, chỉ cần nói: **"continue"** hoặc **"tiếp tục"**

Claude sẽ tự động đọc HANDOVER document và tiếp tục công việc.

### Handover Files:
- **Sprint 15.5 2026-02-09:** `docs/HANDOVER_2026-02-09.md` (Latest)
- **Vision Fallback 2026-02-03:** `docs/HANDOVER_2026-02-03.md`
- **UI Redesign 2026:** `docs/HANDOVER_UI_2026.md`
- **General:** `docs/HANDOVER_v2.7.md`

## Quick Start
```bash
cd /Users/mac/ai-publisher-pro-public
uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload
```
Then open: http://localhost:3000/ui

## Project Type
FastAPI web server for AI-powered document translation (PDF, DOCX, TXT).

## Current Status (2026-02-03)
- Server: Working (port 8000)
- Version: 2.8.1
- Score: 9.7/10 (Production Ready)
- Translation: Smart Extraction + Parallel (10x faster)
- **Vision Fallback:** Claude Vision → OpenAI Vision (for STEM docs)
- Academic: arXiv/formula detection fixed
- Performance: 598 pages in ~28 min (was 4.5 hours)
- Codebase: 75MB (↓78% from 340MB)
- Tests: 883+ (incl. 21 vision fallback tests)
- Git: Pushed to nclamvn/ai-translator-pro

## Key Modules (2025-12-22)
```
core/
├── smart_extraction/      # NEW: Smart PDF routing
│   ├── document_analyzer.py   # Detect PDF type
│   ├── fast_text_extractor.py # PyMuPDF (FREE, 0.1s/page)
│   └── extraction_router.py   # FAST_TEXT/HYBRID/FULL_VISION
│
├── layout_preserve/       # Vision LLM → giữ tables/columns
├── pdf_renderer/          # Agent 3: PDF output

core_v2/
├── orchestrator.py        # Parallel translation (concurrency=5)
└── ...

ai_providers/
├── unified_client.py      # Auto-fallback + Vision: Claude → OpenAI
└── ...                    # Text: OpenAI → Anthropic → DeepSeek
```

## Key Files
- `api/main.py` - Main FastAPI application
- `api/aps_v2_service.py` - V2 publishing service
- `core_v2/orchestrator.py` - Translation orchestrator
- `ui/app.html` - Main UI (3 agents)
- `.env` - API keys configuration

## URLs (port 3001)
- UI: http://localhost:3001/ui
- API Docs: http://localhost:3001/docs
- Health: http://localhost:3001/health

## Handover Document
**QUAN TRỌNG:** Để tiếp tục dự án sau khi nghỉ → đọc `docs/HANDOVER_v2.8.md`

## Features
- **Smart Extraction**: PyMuPDF for text-only, Vision for scanned/formulas
- **Parallel Translation**: 5x concurrent chunks
- **Auto-Fallback**: OpenAI → Anthropic → DeepSeek
- **Usage Stats**: Token/time/cost tracking
- PDF/DOCX/TXT translation
- Layout-Preserving Translation
- Real-time WebSocket progress

## Performance (2025-12-22)
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Extraction (598p) | ~2 hours | ~30 sec | **240x** |
| Translation | ~2.5 hours | ~28 min | **5x** |
| Total | ~4.5 hours | ~28 min | **10x** |
| Cost | ~$15-30 | ~$0.28 | **50x cheaper** |

## Common Commands
```bash
# Start server
uvicorn api.main:app --host 0.0.0.0 --port 3001 --reload

# Check health
curl http://localhost:3001/health

# Import checks
python -c "from core.smart_extraction import smart_extract; print('OK')"
python -c "from ai_providers.unified_client import get_unified_client; print('OK')"

# Stop server
lsof -ti:3001 | xargs kill -9
```

## Session 2025-12-24 Summary (v2.7)
1. ✅ Codebase X-Ray - Project: 340MB → 75MB (↓78%)
2. ✅ UI Cleanup - 664KB → 332KB (↓50%)
3. ✅ Technical Debt Fixed - 2 SyntaxWarnings, 1 test failure
4. ✅ Table → LaTeX rendering in pdf_renderer
5. ✅ Partial job ID matching (8-char prefix)
6. ✅ Academic paper detection (arXiv formulas fixed)
7. ✅ HANDOVER v2.7 created

## Session 2025-12-22 Summary
1. ✅ Smart Extraction Router - FAST_TEXT/HYBRID/FULL_VISION
2. ✅ Parallel Translation - concurrency 1→5
3. ✅ Codebase Cleanup - 57MB freed
4. ✅ Usage Stats Tracking - tokens/time/cost
5. ✅ Git pushed to nclamvn/ai-translator-pro

## UI (3 Agents)
```
Biên Tập Viên → Dịch Giả → Nhà Xuất Bản
(Document Analysis) → (Translation) → (Output Generation)
```
