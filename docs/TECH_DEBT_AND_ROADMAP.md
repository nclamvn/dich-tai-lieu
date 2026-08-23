# Sổ nợ kỹ thuật, Bottleneck & Hướng phát triển
### AI Publisher Pro v3.3.1 — `dich-tai-lieu`

Ngày rà soát: **2026-08-18** · Phạm vi: **toàn dự án** (backend FastAPI + engine `core`/`core_v2` + frontend Next.js + deploy) · Phương pháp: 4 audit agent song song đọc từng tầng, sau đó **đối chiếu lại từng phát hiện với file:line thật** trước khi ghi. Mọi mục P0 trong tài liệu này đã được xác minh trực tiếp trong lần rà soát này, không phải suy đoán.

> Tài liệu này KHÔNG sửa code. Nó là bản đồ nợ để anh quyết định thứ tự ưu tiên. Nhánh `feat/engine-quickwins` (7 phase vừa xong) đã trả một phần nợ ở tầng engine dịch — phần đó được đánh dấu ✅ *đã xử lý* ở cuối mỗi domain liên quan.

---

## 0. Tóm tắt điều hành

Dự án có nền tảng tính năng rất rộng (dịch tài liệu đa định dạng, glossary, TM, OCR, PDF/DOCX render, cinema/screenplay…) nhưng đang mang **ba khoản nợ gốc** chi phối gần như toàn bộ các lỗi con:

1. **Một cuộc refactor bỏ dở `core → core_v2` và `main.py → deps.py`.** Repo tồn tại hai bộ engine song song và hai bản `ConnectionManager`, hai chỗ định nghĩa cấu hình. Đường sống (live path) chỉ dùng `core_v2`, nhưng `core/` vẫn còn ~40+ thư mục/module, trong đó nhiều phần chết hoặc trùng lặp. Hệ quả trực tiếp: **`get_settings()` được 4 nơi gọi nhưng không tồn tại**, và **WebSocket tiến độ broadcast vào một manager, request đọc từ manager khác**.

2. **I/O đồng bộ chạy thẳng trên event loop async.** `sqlite3` (11 module), `subprocess.run` pandoc/soffice/ffmpeg (timeout tới 300–600s), trích xuất PDF, OCR tuần tự từng trang — tất cả nằm trong đường xử lý request/async, nên một job nặng **đóng băng toàn server** chứ không chỉ chậm job đó. Đây là trần hiệu năng thật sự của hệ, không phải tốc độ LLM.

3. **Vòng deploy chưa từng chạy sạch từ đầu (clean-room).** `Dockerfile` copy thư mục `ui/` không tồn tại; `sqlalchemy` bị 4 module import nhưng **không khai báo trong `requirements.txt`**; router provider bị **lồng prefix hai lần**; số worker của `render.yaml` (2) mâu thuẫn với state in-process của service. Nghĩa là bản build trên máy dev "chạy được" nhưng `docker build` / deploy Render sẽ **gãy hoặc lỗi runtime**.

**Sáu chốt chặn P0 (chi tiết ở §2):**

| # | Nợ P0 | Bằng chứng | Hệ quả |
|---|-------|-----------|--------|
| P0-1 | `get_settings()` không tồn tại | `config/settings.py:433` chỉ có `settings = Settings()`; gọi ở `api/main.py:1224`, `api/deps.py:101`, `api/auth_router.py:138`, `api/aps_v2_service.py:167` | `/ws` 500, reset mật khẩu 500, auth **fail-open về `default_user`**, concurrency âm thầm ghim 10 |
| P0-2 | `sqlalchemy` không khai báo | import ở `core/glossary/{models,repository}.py`, `core/tm/{models,repository}.py`; **không có** trong `requirements.txt` | Cài sạch/Docker: glossary (21 endpoint) + TM v1 (18 endpoint) chết khi import |
| P0-3 | `Dockerfile` copy `ui/` không có | `Dockerfile:61 COPY ui/ ./ui/`; `ls ui/` → không tồn tại (frontend nằm ở `frontend/`) | `docker build` **fail** ở bước COPY |
| P0-4 | Router provider lồng prefix 2 lần | `api/provider_routes.py:120 prefix="/api/v2/providers"` **và** `api/main.py:612 include_router(..., prefix="/api/v2/providers")` | Đường thật thành `/api/v2/providers/api/v2/providers/…` → 404 |
| P0-5 | WebSocket split-brain | hai class + hai instance: `api/main.py:672,729` và `api/deps.py:32,58` (`manager = ConnectionManager()`) | Tiến độ job broadcast tới manager này, client subscribe manager kia → **thanh tiến độ đứng im** |
| P0-6 | Worker ≠ state model | `render.yaml:8 --workers 2` vs `Dockerfile:77 --workers 1`; `APSV2Service` giữ job/semaphore/asyncio state **trong tiến trình** | Chạy 2 worker trên Render: job tạo ở worker A, poll trúng worker B → **"job not found"** ngẫu nhiên |

Điểm son: **7 phase `feat/engine-quickwins`** đã dọn đúng phần nợ nặng nhất của *chất lượng dịch* (fail-loud thay `[TRANSLATION ERROR]`, token-cap sửa mega-chunk, glossary/TM/quality gate được đấu dây, prompt caching giảm 30–50% token vào). Những khoản dưới đây là phần *còn lại* — chủ yếu ở tầng vận hành, kiến trúc và frontend.

---

## 1. Cách đọc tài liệu

Mức ưu tiên:

- **P0 — Blocker.** Chặn deploy sạch hoặc gây lỗi runtime/bảo mật ngay. Phải xử trước mọi tính năng mới.
- **P1 — Nặng.** Không chặn chạy trên máy dev, nhưng bào mòn hiệu năng/độ tin cậy/khả năng bảo trì rõ rệt; sẽ thành P0 khi tải tăng.
- **P2 — Vừa.** Nợ thật, nên trả trong 1–2 quý; chưa gây đau hằng ngày.
- **P3 — Nhẹ / vệ sinh.** Dọn dẹp, nhất quán, giảm nhiễu.

Mỗi mục có **file:line làm bằng chứng** và **hướng sửa** (không phải bản vá sẵn). Con số định lượng đo trong lần rà soát này: **~610 `except` bắt rộng**, **~470 `print()` trong code thư viện** (không qua logging), **8 marker TODO/FIXME**, **11 module tự mở `sqlite3.connect`**, **50%** ngưỡng coverage gate (`pytest.ini:21`) so với coverage thực thấp hơn nhiều.

---

## 2. Sổ nợ kỹ thuật (Technical Debt Register)

### 2.1 · P0 — Chốt chặn (phải xử trước)

| ID | Domain | Nợ & bằng chứng | Hướng sửa |
|----|--------|-----------------|-----------|
| **P0-1** | Config | `get_settings()` được import ở `api/main.py:1224`, `api/deps.py:101`, `api/auth_router.py:138`, `api/aps_v2_service.py:167` nhưng `config/settings.py` **chỉ có** `settings = Settings()` (dòng 433), không có hàm. | Thêm `def get_settings(): return settings` (hoặc `@lru_cache`) vào `config/settings.py`. **Sửa 1 dòng, gỡ 4 lỗi 500.** Sau đó viết 1 test import-smoke để CI bắt được loại lỗi này. |
| **P0-2** | Data/Deps | `sqlalchemy` import ở `core/glossary/{models,repository}.py` + `core/tm/{models,repository}.py`; không có trong `requirements.txt`. Máy dev chạy được vì SQLAlchemy đã cài lẻ. | Thêm `sqlalchemy>=2.0,<3` (kèm pin) vào `requirements.txt` **và** `requirements.lock`. Chạy lại clean-room build để xác nhận. |
| **P0-3** | Deploy | `Dockerfile:61 COPY ui/ ./ui/` — thư mục `ui/` không tồn tại; UI thật ở `frontend/`. | Xóa dòng 61 (backend không phục vụ static UI) **hoặc** sửa thành build `frontend/` multi-stage nếu muốn serve chung. |
| **P0-4** | API | Prefix lồng hai lần: `provider_routes.py:120` khai `prefix="/api/v2/providers"`, rồi `main.py:612` include lại với `prefix="/api/v2/providers"`. | Bỏ prefix ở **một** trong hai chỗ. Chuẩn hóa: prefix chỉ đặt lúc `include_router`, `APIRouter()` để trống. Rà toàn bộ router khác theo cùng quy tắc. |
| **P0-5** | API/Realtime | Hai `ConnectionManager`: `main.py:672`(class)/`729`(instance) và `deps.py:32`(class)/`58`(instance). Endpoint `/ws` và code broadcast tiến độ dùng **khác instance**. | Giữ **một** `ConnectionManager` (đưa về `deps.py`), mọi nơi import từ đó. Xóa bản trùng ở `main.py`. Đây cũng là gốc của "thanh tiến độ đứng im". |
| **P0-6** | Deploy/State | `render.yaml:8` chạy `--workers 2`; `APSV2Service` giữ dict job + `asyncio` task + semaphore **in-process** (không share store). `Dockerfile:77` lại để `--workers 1`. | Ngắn hạn: ép **1 worker** ở cả hai nơi (nhất quán, an toàn). Trung hạn: đẩy job state ra store dùng chung (SQLite WAL/Redis) để scale worker thật. |

### 2.2 · P1 — Nặng

**Kiến trúc / hai-stack**

- **P1-A1 · Hai bộ engine song song.** `core/` còn ~40+ mục (`translator.py`, `parallel.py`, `merger.py`, `chunker.py`, `translation/`, `layout*`, `pdf_renderer/` + `pdf_renderer_v2/`, `batch/` + `batch_processor.py` + `batch_queue/`, `book_writer/` + `book_writer_v2/`…) trong khi live path chỉ đi qua `core_v2/`. Ước lượng **11–14K LOC chết/trùng**. *Hệ quả:* mỗi lần sửa phải đoán "file nào đang sống", tăng rủi ro sửa nhầm bản chết, và làm loãng coverage. → **Khoanh vùng "đang sống" bằng import-graph từ `api/`, gắn nhãn `# DEAD (2026-08)` cho phần ngoài đồ thị, rồi xóa theo từng PR nhỏ có test canh.**
- **P1-A2 · Va chạm tên `export`.** Tồn tại **cả** `core/export/` (package) **và** `core/export.py` (module) cùng tên → phải dùng mẹo `importlib` để nạp, rất dễ gãy khi đổi Python/đóng gói. → Đổi tên một trong hai (`core/export.py` → `core/export_legacy.py` hoặc gộp vào package).
- **P1-A3 · Bốn hiện thực glossary.** `core/glossary/` (package), `core/glossary.py`, `core/glossary_legacy.py`, và top-level `glossary/`. → Chốt một, chuyển caller, xóa còn lại. (Engine-quickwins đã đấu dây glossary vào `core_v2` qua `term_ledger`; nay cần dọn phần cũ.)

**Hiệu năng / async**

- **P1-P1 · I/O đồng bộ trên event loop.** `sqlite3.connect` ở 11 module; `subprocess.run(...)` với `timeout=300/600` ở `core/screenplay_studio/agents/video_editor.py:135,189` và pandoc ở `core/rendering/omml_converter.py`; trích PDF/OCR trong đường request. Trên ASGI, các call blocking này **giữ event loop**, làm mọi request khác treo. → Bọc bằng `run_in_executor`/`anyio.to_thread`, hoặc đẩy sang worker/queue; DB dùng `aiosqlite` hoặc thread-pool.
- **P1-P2 · OCR tuần tự từng trang.** Vòng lặp OCR xử lý trang nối trang (không song song, không batch) → tài liệu scan nhiều trang chậm tuyến tính. → Song song hóa theo trang với giới hạn đồng thời (đã có sẵn semaphore ở tầng job để mượn mô hình).
- **P1-P3 · "Resume" = chạy lại từ 0%.** Cơ chế resume job thực chất khởi động lại từ đầu thay vì tiếp tục từ chunk đã dịch. *Nghịch lý:* engine-quickwins đã có ChunkCache nên re-run **gần như miễn phí** cho chunk trùng — nhưng UX vẫn báo 0% và dịch lại. → Đọc trạng thái chunk từ cache để nhảy tới chunk dở; báo tiến độ theo chunk đã có trong cache.

**Testing / CI**

- **P1-T1 · Coverage gate "diễn".** `pytest.ini:21 --cov-fail-under=50` nhưng coverage thực đo được thấp hơn nhiều (phần lớn `core/` chết không có test). Gate này hoặc đang bị tắt bằng cờ, hoặc CI không chạy đúng tập. *Hệ quả:* số xanh tạo cảm giác an toàn giả. → Hạ gate về mức **thật** (đo rồi đặt sàn = hiện trạng), rồi **chỉ tăng dần**; loại `core/` chết khỏi phép đo để con số phản ánh phần đang sống.
- **P1-T2 · Gần như không có test frontend có ý nghĩa.** 0 test kiểm hành vi thật (API hook, error state, WS). → Thêm test cho `lib/api/client.ts` + các hook, ưu tiên đường publish/poll.

**Frontend**

- **P1-F1 · Base-URL split-brain.** `frontend/src/lib/api/client.ts:47` và `lib/api/hooks.ts:13,277,481` mặc định `http://localhost:8000`, **nhưng** `app/jobs/[id]/page.tsx:597` (link tải PDF) mặc định `http://localhost:3000`. → Chốt **một** biến `NEXT_PUBLIC_API_URL`, dùng một hằng `API_BASE` duy nhất, xóa literal rải rác.
- **P1-F2 · Query error state bị nuốt.** Nhiều trang (đa số màn hình) không hiển thị nhánh `error` của TanStack Query → khi API lỗi, người dùng thấy màn trắng/loading vô tận thay vì thông báo. → Chuẩn hóa 1 `<QueryError>` component, gắn vào các `useQuery` chính.

### 2.3 · P2 — Vừa

- **P2-1 · Migration chưa có hệ thống.** `core/database/migrator.py` tồn tại nhưng không được wire vào khởi động; **không có Alembic** (`alembic.ini` vắng). Đổi schema hiện phải sửa tay/DB mới. → Chọn Alembic **hoặc** wire `migrator.py` vào startup, versioned.
- **P2-2 · ~610 `except` bắt rộng.** `except Exception`/`except:` che lỗi thật, gây "im lặng sai". → Thay dần bằng exception hẹp; chỗ buộc bắt rộng thì `logger.exception` rồi re-raise/đánh dấu.
- **P2-3 · ~470 `print()` trong code thư viện.** Không đi qua logging → không kiểm soát được ở prod. → Chuyển sang `logging` theo module; giữ `print` chỉ trong script CLI.
- **P2-4 · `requirements.txt` chỉ đặt sàn (floor-only).** Nhiều gói `>=` không trần → build không tất định, dễ vỡ khi upstream lên major. → Pin trần + duy trì `requirements.lock` là nguồn sự thật khi build/Docker.
- **P2-5 · SQLite phân mảnh.** 11 điểm tự mở kết nối, nhiều file `.db` tạo lúc runtime, không tầng truy cập chung. → Gom về một lớp repository/kết nối, bật WAL nhất quán, đóng kết nối tường minh.
- **P2-6 · WS reconnect sau unmount.** Frontend mở lại WebSocket sau khi component đã unmount → rò rỉ kết nối. → Cleanup trong `useEffect`, hủy reconnect khi unmount.

### 2.4 · P3 — Nhẹ / vệ sinh

- **P3-1 ·** 8 marker `TODO/FIXME` rải rác — gom thành issue có chủ.
- **P3-2 ·** File `.deprecated` còn trong cây nguồn (`core/ocr_deepseek.py.deprecated`) — xóa hẳn.
- **P3-3 ·** `.env.example` giờ đã đầy đủ (engine-quickwins bổ sung) — rà để không sót key mới ở tài liệu onboarding.
- **P3-4 ·** Thống nhất tên model mặc định giữa `config/settings.py`, `.env.example` và tài liệu (tránh lệch phiên bản model).

---

## 3. Phân tích Bottleneck

Xếp theo mức độ **giới hạn thông lượng thật** của hệ, không theo cảm giác:

1. **Event loop bị chặn bởi I/O đồng bộ (trần cứng).** Đây là nút nghẽn số một. Vì `sqlite3`, `subprocess` (pandoc/soffice/ffmpeg tới 300–600s), trích PDF và OCR chạy blocking *trên chính event loop*, hệ **không đạt được** đồng thời mà kiến trúc async hứa hẹn: một job xuất DOCX nặng làm treo cả những request `/health`. Nới song song LLM sẽ **không** giúp gì tới khi phần này ra khỏi loop. *Đòn bẩy lớn nhất, chi phí trung bình.*

2. **State in-process chặn scale ngang.** `APSV2Service` giữ job/semaphore/task trong RAM tiến trình → không thể chạy >1 worker (P0-6) và không sống sót qua restart. Trần thông lượng bị khóa ở "1 tiến trình". *Đòn bẩy lớn, chi phí trung bình–cao.*

3. **OCR & xử lý trang tuần tự.** Với tài liệu scan, thời gian ≈ tuyến tính theo số trang. Song song hóa có thể cắt nhiều lần cho đúng nhóm tài liệu này. *Đòn bẩy trung bình, chi phí thấp.*

4. **Resume giả → trả tiền LLM 2 lần.** Mỗi lần "resume" chạy lại từ 0 đốt lại token cho phần đã dịch. ChunkCache (đã có) khiến chi phí *tính toán* re-run thấp, nhưng UX vẫn phát lệnh dịch lại. *Đòn bẩy trung bình về chi phí, sửa rẻ vì hạ tầng cache đã sẵn.*

5. **Không nghẽn: tốc độ LLM.** Sau engine-quickwins (prompt caching, temperature thấp, token-cap, failover TTL), tầng LLM **không còn là** nút nghẽn chính. Đừng tối ưu tiếp ở đây trước khi xử 1–3.

Thứ tự "tiền/công": **#1 và #2 trả lại nhiều thông lượng nhất cho mỗi giờ công**; #3, #4 là quick-win cho nhóm tài liệu cụ thể.

---

## 4. Hướng phát triển (Roadmap)

### NOW — Ổn định để deploy sạch (1 sprint, phần lớn ≤1 ngày mỗi mục)
Mục tiêu: `docker build` + deploy Render chạy sạch, không lỗi 500 nền.

1. **Gỡ 6 chốt P0** (P0-1…P0-6). Riêng P0-1 và P0-3 mỗi cái ~1 dòng.
2. Thêm **1 CI job "import-smoke"**: `python -c "import api.main"` trong môi trường **clean-room** (đúng `requirements.txt`) — sẽ bắt sống loại lỗi P0-1/P0-2 mãi về sau.
3. Ép **1 worker** nhất quán (`render.yaml` = `Dockerfile`) cho tới khi P0-6 giải bằng shared store.
4. Chạy `scripts/e2e_translation_smoke.py` với key thật (nghiệm thu engine-quickwins) — đóng luôn việc nghiệm thu nhánh đang treo.

### NEXT — Gỡ trần hiệu năng & dọn hai-stack (2–4 sprint)
Mục tiêu: đạt đồng thời thật, giảm rủi ro bảo trì.

5. **Đưa I/O đồng bộ ra khỏi event loop** (P1-P1): bọc `subprocess`/PDF/OCR bằng thread-pool/executor; DB sang `aiosqlite` hoặc pool. *Đây là hạng mục hiệu năng quan trọng nhất.*
6. **State job ra store dùng chung** (P0-6/P1): mở đường chạy nhiều worker + sống sót restart.
7. **Resume thật theo ChunkCache** (P1-P3): tận dụng hạ tầng cache đã có; sửa rẻ, thắng cả tiền LLM lẫn UX.
8. **Dọn hai-stack có kiểm soát** (P1-A1/A2/A3): import-graph → nhãn DEAD → xóa từng PR nhỏ; gộp 4 glossary về 1; xử va chạm `export`.
9. **Frontend base-URL + error state** (P1-F1/F2): một `API_BASE`, một `<QueryError>`.

### LATER — Bền vững & mở rộng năng lực (quý sau)
10. **Migration versioned** (P2-1): Alembic hoặc wire `migrator.py`.
11. **Song song hóa OCR/trang** (P1-P2) cho nhóm tài liệu scan.
12. **Vệ sinh nợ diện rộng** (P2-2/2-3): thu hẹp `except`, thay `print()` bằng logging — làm dần theo module đụng tới.
13. **Coverage thật + test frontend** (P1-T1/T2): đặt sàn = hiện trạng rồi tăng dần; test cho đường publish/poll.
14. **TM write-back cấp câu** (đã hoãn từ engine-quickwins, cần alignment source↔target) — mở khóa tự học thuật ngữ theo thời gian.

---

## 5. `feat/engine-quickwins` đã trả khoản nợ nào

Để không kể trùng: nhánh 7-phase vừa xong **đã xử** phần lớn nợ *chất lượng dịch* — nên các mục đó **không** nằm trong sổ trên:

- ✅ `[TRANSLATION ERROR]` âm thầm nhét vào tài liệu → **fail-loud** (`ChunkTranslationError`).
- ✅ Mega-chunk vượt output limit → **token-cap** cắt đúng ngân sách (Phase 3).
- ✅ Glossary/TM/quality-gate "có mà không dùng" → **đã đấu dây** vào `core_v2` (Phase 2/4/6).
- ✅ Dịch lại nội dung y hệt mỗi lần chạy → **ChunkCache** wired (Phase 1) — cũng là hạ tầng cho "resume thật" ở NEXT.
- ✅ Chạy ở temperature ~1.0/model rẻ nhất → temperature 0.3 + model registry cấu hình được (Phase 1).
- ✅ Token vào cao → **prompt caching** giảm 30–50% (Phase 1).
- ✅ Ngữ cảnh chunk chỉ 100 ký tự đầu → **rolling context** từ đuôi chunk trước (Phase 5).
- ✅ Không tầng soi ngữ nghĩa → **semantic verifier** opt-in feeding repair loop (Phase 7).

Phần engine-quickwins **cố ý hoãn** (ghi lại trong CHANGELOG `[Unreleased]`; file `PR_feat-engine-quickwins.md` đã xóa 2026-08-23) trùng khớp với NEXT/LATER ở trên — riêng mục "dọn code chết/hai-stack" ĐÃ XONG (Option A stage 5, v3.3.1): glossary name→ID, TM write-back cấp câu, snap boundary còn lại.

---

### Phụ lục — Nguồn xác minh
Mọi P0 và phần lớn P1 trong tài liệu này được kiểm bằng `grep`/`ls` trực tiếp trên cây nguồn ngày 2026-08-18 (không dựa vào trí nhớ audit). File:line trích dẫn là vị trí thật ở thời điểm rà soát; nếu anh đã merge nhánh khác sau đó, hãy đối chiếu lại số dòng trước khi sửa.
