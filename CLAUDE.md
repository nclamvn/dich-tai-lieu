# CLAUDE.md — hướng dẫn cho AI agent làm việc với repo này

> Cập nhật 2026-08-23. File này là nguồn sự thật cho agent; các file
> `docs/HANDOVER_*` và `docs/*XRAY*` cũ hơn là TƯ LIỆU LỊCH SỬ, không phản ánh
> hiện trạng. Bức tranh hiện trạng đầy đủ: **`PROJECT_XRAY.md`** ở repo root.

## Dự án

**AI Publisher Pro** (repo `nclamvn/dich-tai-lieu`) — nền tảng dịch & xuất bản
tài liệu, tiếng Việt là first-class. FastAPI backend + Next.js 16 frontend.
Version hiện hành: **3.3.1** (`api/main.py`).

- 4 AI provider với auto-failover: OpenAI, Anthropic, DeepSeek, Gemini
  (`ai_providers/unified_client.py`; vision order: anthropic → openai → gemini).
- Renderer DOCX/PDF/EPUB **duy nhất** là AST stack (`core/rendering/*` —
  `document_ast.py` + docx/pdf/epub adapters). `core/docx_engine` và
  `core/pdf_engine` đã bị XÓA (Option A stage 5); flag `OUTPUT_PIPELINE`
  không còn tồn tại.
- Trang bìa: 12 template dựng sẵn + ảnh bìa riêng
  (`core/rendering/cover_templates.py`, `cover_apply.py`;
  API `/api/cover-templates`, picker ở `frontend/src/components/translate/cover-picker.tsx`).
- Font tiếng Việt đóng gói sẵn trong `assets/fonts/` (Noto Sans/Serif) — PDF
  và bìa render đủ dấu trên mọi máy.

## Chạy dev

```bash
bash dev.sh        # backend :8000 (uvicorn --reload) + frontend :3000 — Ctrl-C tắt cả hai
```

Mở http://localhost:3000. Backend docs: http://localhost:8000/docs (chỉ hiện
ngoài production). Docker/production dùng cổng 3000 (backend) + 3001 (frontend)
— xem `DEPLOYMENT.md`; hai bộ cổng này KHÁC nhau, đừng trộn.

## Kiểm thử & gate

```bash
python3 -m pytest tests/ -q --no-cov     # toàn suite ~3.2K test — phải XANH 100%
ruff check .                             # lint gate (CI chặn)
cd frontend && npx tsc --noEmit          # type gate (CI chặn)
```

CI (`.github/workflows/ci.yml`): ruff + import-smoke (prod deps only) + pytest
matrix 3.11/3.12 (unit/api/security/core/eval/integration + batch/rri_t/e2e/
streaming/v2/root) + vitest + tsc. Coverage guard nội dung render:
`tests/eval/test_render_coverage.py` (DOCX ≥ 0.99, PDF ≥ 0.95).

## Kiến trúc — đường dịch chính

```
POST /api/v2/publish (api/aps_v2_router.py)
  → APSV2Service.create_job / _process_job (api/aps_v2_service.py)
  → UniversalPublisher.publish (core_v2/orchestrator.py)
      vision read → strip running furniture → DNA → term ledger (glossary)
      → semantic chunk → translate (TM hints, cache, retry/backoff)
      → repair pass → assemble → _convert
  → OutputConverter (core_v2/output_converter.py) → AST adapters + cover
  → job.output_paths → GET /api/v2/jobs/{id}/download/{format}
```

Chi tiết module-by-module, data stores, env vars: xem `PROJECT_XRAY.md`.

## Quy tắc bất di bất dịch

1. **`data/.encryption_key` KHÔNG BAO GIỜ được commit** (đã gitignore — đừng
   force-add). Tương tự: `.env`, `*.db`, `*.db-wal/shm`.
2. `outputs/`, `uploads/`, `tests/output/`, `data/authors|author_uploads|exports`
   là cây generated — đã ignore, đừng track lại.
3. Mọi PR: chạy đủ pytest (3.11 nếu chỉ có một version) + ruff trước khi giao.
4. `SECURITY_MODE=development` (mặc định) TẮT auth — đó là chủ đích cho dev;
   production đặt `SECURITY_MODE=production` (xem `docs/PRODUCTION_CHECKLIST.md`).
5. Muốn hiểu lịch sử một quyết định: `docs/BLUEPRINT_ast_convergence.md`
   (Option A), `docs/SOAK_RENDER_COVERAGE.md` (vì sao AST thắng engine),
   `docs/TECH_DEBT_AND_ROADMAP.md` (sổ nợ).
