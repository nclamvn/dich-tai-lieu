# PROJECT X-RAY — AI Publisher Pro

> Chụp cắt lớp toàn dự án theo X-Ray Protocol (Vibecode Kit). Cập nhật
> **2026-08-23**, tại v3.3.1, sau khi Option A hoàn tất (AST là renderer duy
> nhất) và đợt dọn nợ kỹ thuật cùng ngày. Đây là tài liệu hiện-trạng thẩm
> quyền; các `docs/HANDOVER_*`, `docs/*XRAY*` cũ hơn là tư liệu lịch sử.

## 1. Overview

**AI Publisher Pro** (`nclamvn/dich-tai-lieu`) — nền tảng dịch & xuất bản tài
liệu AI, tiếng Việt first-class, 55+ ngôn ngữ. Người dùng upload tài liệu
(PDF/DOCX/TXT/MD/EPUB/SRT), hệ thống đọc (text-extract thông minh hoặc Claude
Vision), dịch theo ngữ cảnh (glossary + translation memory + cache), rồi xuất
bản chuyên nghiệp (DOCX/PDF/EPUB với template, mục lục, trang bìa). Ngoài lõi
dịch còn: Book Writer (v1/v2), Screenplay Studio, Book-to-Cinema, OCR, Editor.

- Backend: **FastAPI** (Python 3.11+), ~23K LOC `api/` + ~74K LOC `core/` +
  ~13.5K LOC `core_v2/`.
- Frontend: **Next.js 16** App Router (~18K LOC TS/TSX), TanStack Query, i18n VI/EN.
- AI: 4 provider auto-failover — thứ tự text `openai → anthropic → deepseek →
  gemini`, vision `anthropic → openai → gemini` (`ai_providers/unified_client.py`).
- Kiểm thử: **~3.200 test, xanh 100%** trên Python 3.11 & 3.12; CI đủ gate
  (ruff, import-smoke, pytest matrix, vitest, `tsc --noEmit`).

## 2. Quick Start

```bash
git clone https://github.com/nclamvn/dich-tai-lieu && cd dich-tai-lieu
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # điền ít nhất 1 provider API key
cd frontend && npm install && cd ..
bash dev.sh                    # backend :8000 + frontend :3000, Ctrl-C tắt cả hai
```

Mở http://localhost:3000. API docs: http://localhost:8000/docs (ẩn ở production).
Docker/production dùng cổng **3000 (backend) / 3001 (frontend)** — `DEPLOYMENT.md`.
Không cần API key vẫn test được upload/convert/bìa; chỉ bước dịch AI cần key.

## 3. Architecture

```
Browser (Next.js :3000)
   │  fetch (lib/api/client.ts, CSRF, X-Session-Token)
   ▼
FastAPI (api/main.py :8000) ── middleware: RequestContext → Metrics → SecurityHeaders → SlowAPI → CSRF
   │
   ├─ /api/v2/publish ──► APSV2Service (api/aps_v2_service.py)
   │        create_job → _process_job (semaphore MAX_CONCURRENT_JOBS)
   │        ▼
   │   UniversalPublisher.publish (core_v2/orchestrator.py)
   │     1. Đọc nguồn: smart_extraction (PyMuPDF/OCR) hoặc Claude Vision
   │     2. strip_running_furniture (bỏ header/footer lặp của sách nguồn)
   │     3. DocumentDNA (thể loại/giọng) → TermLedger (glossary + auto-terms)
   │     4. SemanticChunker → dịch song song (TM hints, chunk-cache, retry/backoff)
   │     5. Quality gate + repair pass → assemble
   │     6. _convert ──► OutputConverter (core_v2/output_converter.py)
   │              └─► AST renderers (core/rendering/*): DOCX/PDF/EPUB
   │                  + cover (template hoặc ảnh riêng) + font Việt đóng gói
   │     7. output_paths → tải về qua /api/v2/jobs/{id}/download/{format}
   │
   ├─ /api/auth/* (JWT) + /api/auth/login|session (session-token)
   ├─ /api/glossary, /api/tm, /api/usage, /api/keys, /api/errors, /api/dashboard
   ├─ /api/author, /api/v2/books(-v2), /api/screenplay, /api/cinema, /editor
   ├─ /api/ocr/*, /api/upload, /api/batch*, /api/cover-templates(+preview,upload)
   └─ /ws (WebSocket tiến độ job; fan-out Redis tùy chọn qua WS_REDIS_URL)
```

**Renderer (Option A hoàn tất):** một nguồn sự thật `DocumentAST`
(`core/rendering/document_ast.py`) → `docx_adapter` / `pdf_adapter` /
`epub_adapter`. Engine cũ đã xóa (stage 5); guard toàn vẹn nội dung:
`scripts/soak_render_coverage.py` (CI: `tests/eval/test_render_coverage.py`,
sàn DOCX ≥ 0.99, PDF ≥ 0.95). AST lỗi → raise → orchestrator fallback pandoc.

## 4. Key Components

| Thành phần | Đường dẫn | Vai trò |
|---|---|---|
| Orchestrator | `core_v2/orchestrator.py` (1.458) | Toàn pipeline publish (đọc→dịch→xuất) |
| Output converter | `core_v2/output_converter.py` (~1.0K) | Điều phối AST render + cover + fallback |
| AST render stack | `core/rendering/` (4.4K) | document_ast, docx/pdf/epub adapters, OMML |
| Cover engine | `core/rendering/cover_templates.py` + `cover_apply.py` | 12 template + ảnh riêng; PDF/DOCX/EPUB |
| Vision reader | `core_v2/vision_reader.py` | Claude Vision đọc PDF (công thức/layout) |
| Semantic chunker | `core_v2/semantic_chunker.py` + `token_chunking.py` | Chia chương/đoạn theo token budget |
| Term ledger | `core_v2/term_ledger.py` | Glossary + auto-terms nhất quán mỗi job |
| TM gateway | `core_v2/tm_gateway.py` + `core/tm/` | Gợi ý translation memory vào prompt |
| Quality gate | `core_v2/quality_gate.py` + `verifier.py` | Bắt chunk hỏng → repair pass |
| Smart extraction | `core/smart_extraction/` | Định tuyến PyMuPDF/OCR/Vision theo tài liệu |
| OCR | `core/ocr/` | PaddleOCR + MathPix hybrid |
| Provider client | `ai_providers/unified_client.py` (948) | 4 provider, failover, health, chi phí |
| Batch (v1) | `core/batch_processor.py` (2.170) + `core/batch/` | Hàng đợi dịch job kiểu cũ |
| Book Writer v2 | `core/book_writer_v2/` (8.1K) | Sinh sách theo số trang, kế hoạch minh họa |
| Screenplay Studio | `core/screenplay_studio/` (7.3K) | Chuyển thể kịch bản đa-agent |
| Cinema | `core/cinema/` (3.1K) | Book→video |
| Eval harness | `evalkit/` + `scripts/eval_translation.py` | Đo chất lượng dịch vs golden set (offline-testable) |
| Frontend picker bìa | `frontend/src/components/translate/cover-picker.tsx` | Chọn template/upload bìa theo job |

## 5. API Reference (tóm tắt)

~25 router, ~266 endpoint. Nhóm chính: `/api/v2/*` (publish/jobs/providers/batch),
`/api/auth/*`, `/api/glossary`, `/api/tm`, `/api/usage`, `/api/keys`,
`/api/author`, `/api/v2/books(-v2)`, `/api/screenplay`, `/api/cinema`,
`/api/ocr/*`, `/api/cover-templates`, `/health`, `/metrics`, `/ws`.
Danh sách auth-gating đầy đủ: `docs/PRODUCTION_CHECKLIST.md`. Swagger: `/docs` (dev).

## 6. Data Stores (SQLite, `data/`)

| DB | Chủ sở hữu |
|---|---|
| `jobs.db` | `api/job_repository.py` (APS v2 jobs) + `core/job_queue.py` |
| `users/users.db` | `core/auth/` (JWT users) |
| `audit.db` | `core/services/audit_log.py` |
| `glossary.db` / `tm.db` | `core/glossary/` / `core/tm/` |
| `translation_memory/tm.db` | TM đường batch v1 (⚠ tách biệt với `tm.db` — nợ hợp nhất) |
| `cache/chunks.db`, `checkpoints/checkpoints.db` | chunk-cache dịch, checkpoint |
| `usage/usage.db`, `errors/error_tracker.db`, `api_keys/keys.db` | usage/quota, lỗi, API keys |
| `book_writer.db`, `screenplay_studio.db` | Book Writer, Screenplay |
| `aps_jobs.db` | ⚠ nghi mồ côi (chỉ backup script đụng tới) |

File: uploads vào `uploads/{v2,batch,covers}/`, kết quả vào `outputs/…` —
cả hai cây đã gitignore toàn phần. **`data/.encryption_key`** (Fernet, mã hóa
API key người dùng lưu trong Settings) tự sinh nếu thiếu — TUYỆT ĐỐI không
commit, và phải nằm trong backup riêng (mất key = mất toàn bộ key đã lưu).

## 7. Environment Variables

Đầy đủ trong `.env.example` + `config/settings.py`. Nhóm đáng nhớ:
provider keys (`OPENAI/ANTHROPIC/GOOGLE/DEEPSEEK_API_KEY`), bảo mật
(`SECURITY_MODE` — mặc định `development` = **auth TẮT**; production cần
`SESSION_SECRET`, `CSRF_SECRET_KEY`, `JWT_SECRET_KEY` cố định), rate limit
(`RATE_LIMIT*` — tự bật ở production), dịch (`TRANSLATION_*`, `CHUNK_*`),
glossary/TM (`TRANSLATION_GLOSSARY_*`, `TM_*`), bìa (`COVER_TEMPLATE`,
`COVER_IMAGE`), làm sạch nguồn (`STRIP_RUNNING_FURNITURE`), WS (`WS_REDIS_URL`).

## 8. Build History (trace các đợt lớn gần nhất)

| PR | Nội dung |
|---|---|
| #13–19 | Bảo mật nền: session auth fail-closed, boot guard, docs gating |
| #20–23 | Option A stage 1–3: AST + inline runs + front matter + flag + soak |
| #24–25 | Rate limiting (slowapi) + auth sweep 18 router + sanitize 500 |
| #26 | Strip running headers/footers (fix tiêu đề lặp 123 lần) |
| #27–30 | Cover templates 4 phase: engine 12 mẫu → PDF/DOCX → EPUB+ảnh riêng → picker UI |
| #31–32 | Font Việt đóng gói (Noto) + cache-bust preview |
| #33 | Suite 3.286 test xanh 100% + CI phủ mọi cây + tsc hard gate |
| #34 | **Option A stage 4+5**: AST mặc định + xóa engine cũ (−7.5K dòng) |
| #35 + đợt này | Dọn repo: untrack generated, xóa module mồ côi, hết deprecation |

## 9. Deployment

Docker: `Dockerfile` (backend, python:3.13-slim) + `docker-compose.yml`
(backend :3000, frontend :3001) + `deploy.sh` / `update.sh` / `backup.sh` /
`smoke-test.sh`; Render: `render.yaml`. Checklist bắt buộc trước khi mở
production: `docs/PRODUCTION_CHECKLIST.md` (SECURITY_MODE, secrets, residuals).
⚠ Lưu ý drift: image prod chạy Python **3.13** trong khi CI test 3.11/3.12.

## 10. Common Tasks

```bash
bash dev.sh                                       # chạy dev cả hai server
python3 -m pytest tests/ -q --no-cov              # toàn suite
ruff check . && (cd frontend && npx tsc --noEmit) # hai gate còn lại
python3 scripts/soak_render_coverage.py           # soak toàn vẹn render
python3 scripts/eval_translation.py --backend engine --save-baseline eval_baseline.json  # baseline dịch (cần key)
python3 scripts/backup_db.py                      # backup SQLite an toàn WAL
```

## 11. Troubleshooting

- **Bìa/PDF ra ô vuông ▪**: backend chưa restart sau khi cập nhật font đóng gói
  — `Ctrl-C` rồi `bash dev.sh`; preview có version-stamp nên trình duyệt tự lấy mới.
- **401 hàng loạt ở production**: đúng thiết kế fail-closed — kiểm tra
  `SESSION_SECRET`/đăng nhập; xem PRODUCTION_CHECKLIST.
- **JWT "hết hạn" sau restart**: chưa đặt `JWT_SECRET_KEY` cố định (key sinh
  ngẫu nhiên mỗi lần khởi động).
- **Job treo/chậm**: xem `/api/v2/jobs/{id}` + log watchdog; concurrency chỉnh
  qua `MAX_CONCURRENT_JOBS`, `CONCURRENCY`.
- **Dịch không chạy, "Providers: NONE"**: chưa có key trong `.env`.

## 12. Nợ kỹ thuật còn lại (sổ theo dõi, xếp theo ưu tiên)

1. **FastAPI `@app.on_event` → lifespan** (9 chỗ `api/main.py`, 1 `provider_routes.py`)
   — deprecated, đổi cần cẩn trọng thứ tự khởi động.
2. **`datetime.utcnow()` ×~30** ngoài bridge — mechanical sweep sang
   `datetime.now(timezone.utc)`.
3. **Cổng sprawl**: dev :8000/:3000 vs Docker :3000/:3001 vs `Dockerfile.dev`
   :3001 — hợp nhất về một bản đồ cổng + cập nhật docs còn nhắc cổng cũ.
4. ~~**Python drift**: prod image 3.13, CI 3.11/3.12~~ — **ĐÃ TRẢ (P1 paydown)**:
   3.13 vào matrix CI, suite verify xanh trên 3.11/3.12/3.13.
5. **7 endpoint `/api/system|queue|cache|processor` định nghĩa trùng**
   (`api/main.py` inline che `api/routes/system.py`) — bỏ một bản.
6. **Hai DB translation-memory** (`data/tm.db` v2 vs
   `data/translation_memory/tm.db` v1) + `data/aps_jobs.db` nghi mồ côi — hợp
   nhất/khai tử có kiểm chứng.
7. **`settings.output_dir` (`data/output`) lệch cây thực dùng (`outputs/…`)**.
8. ~~**Router chưa gate khi production**: glossary (21 ep), usage (8), api_keys
   (7), metrics~~ — **ĐÃ TRẢ (P1 paydown)**: glossary session-gate cấp router;
   `/api/usage/plans` + `/api/api-keys/scopes/available` (2 lỗ cuối của cặp
   router JWT) đã đóng; `/metrics` gate bearer `METRICS_TOKEN`, fail-closed 403
   khi production không đặt token; boot-guard production bắt buộc
   `JWT_SECRET_KEY`; frontend `GLOSSARY_BASE` sửa prefix đôi. Test:
   `test_router_authz` + `test_jwt_routers_have_no_open_endpoints` +
   `test_metrics_gate` + `test_auth_enforcement` (JWT guard).
9. **CI chưa chạy** `tests/{stress,regression,cache,load}` (≈92 test) — cân
   nhắc đưa vào job nightly.
10. **`pytest.ini --disable-warnings`** — gỡ sau khi xử lý (1)+(2) để warning
    mới không bị nuốt.
11. Docs lịch sử (`docs/HANDOVER_*`, `docs/ui/*`, `docs/api/server.md`…) chưa
    gắn banner "historical" từng file — đã có tuyên bố chung ở đầu file này và
    CLAUDE.md.

## 13. Future Improvements (từ roadmap)

Baseline eval dịch trước beta rộng (mốc so sánh chất lượng); diễn tập
`SECURITY_MODE=production` + đóng residuals; observability (error tracking) +
kiểm backup + thử trọn đường deploy; E2E Playwright luồng upload→dịch→xuất-có-bìa
trong CI; glossary name→ID, TM write-back cấp câu (TECH_DEBT_AND_ROADMAP.md).
