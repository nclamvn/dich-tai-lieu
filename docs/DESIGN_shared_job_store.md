# Thiết kế: Shared store cho job state (đa worker) — #6

Ngày: 2026-08-18 · Trạng thái: **BẢN THIẾT KẾ CHỜ DUYỆT — chưa code.** · Nhánh dự kiến: tách riêng khi anh duyệt.

> Em đưa thiết kế + phương án + khuyến nghị + câu hỏi cần anh quyết. **Chưa động vào code** cho tới khi anh chốt hướng.

## 1. Vì sao có tài liệu này

P0-6 (đã vá tạm): `render.yaml` chạy `--workers 2` nhưng state job giữ **trong tiến trình** → job tạo ở worker A, poll trúng worker B → "job not found". Em đã ép `--workers 1` cho an toàn. Muốn **scale ngang thật** (nhiều worker/nhiều máy) thì phải đưa state ra **store dùng chung**. Đây là thiết kế cho việc đó.

## 2. Hiện trạng — cái gì bền, cái gì chỉ trong tiến trình

`APSV2Service` (`api/aps_v2_service.py`):

| Thành phần | Nơi ở | Chia sẻ được giữa worker? |
|-----------|-------|---------------------------|
| **Bản ghi job** (status, progress, paths…) | **sqlite** `data/jobs.db` qua `JobRepository` | ✅ bền — nhưng backend hiện dùng **1 connection chung** (xem §6) |
| `self._jobs: Dict[str,Dict]` (cache runtime) | RAM tiến trình (dòng 174) | ❌ mỗi worker một bản, dễ stale |
| `asyncio.create_task(...)` (task đang chạy) | Event loop của **đúng worker tạo nó** | ❌ worker khác không thấy/không cancel được |
| `asyncio.Semaphore(max_jobs)` (giới hạn đồng thời) | RAM tiến trình (dòng 171) | ❌ mỗi worker giới hạn riêng → tổng = workers × max_jobs |
| WebSocket `ConnectionManager` (broadcast tiến độ) | RAM tiến trình (`api/deps.manager`) | ❌ client nối worker B **không** nhận tiến độ job chạy ở worker A |

**Điểm mấu chốt:** bản ghi job **đã bền** (sqlite). Bốn thứ còn lại (cache, task handle, semaphore, WS) là *điều phối runtime* — đó mới là phần chặn multi-worker.

## 3. Bốn bài toán con phải giải cho multi-worker

1. **Đọc state chéo worker** — worker nào cũng phải đọc được job (đã gần xong: `get_job` fallback về sqlite; chỉ cần bỏ cache stale hoặc cho cache TTL ngắn).
2. **Fan-out tiến độ WS** — tiến độ job ở worker A phải tới client nối ở worker B ⇒ cần **pub/sub**.
3. **Giới hạn đồng thời toàn cục** — semaphore phải đếm chung mọi worker.
4. **Điều khiển job chéo worker** (cancel) — worker B bấm cancel job đang chạy ở worker A ⇒ cần cờ dùng chung mà worker-chủ poll.

## 4. Các phương án

### Phương án A — Redis làm shared state + pub/sub  ⭐ khuyến nghị
- **Redis đã là dependency sẵn** (`requirements: redis[hiredis]`), Render có add-on Redis.
- State runtime (progress/status/heartbeat) ghi Redis; bản ghi bền vẫn ở sqlite (hoặc dời hẳn sang Redis + snapshot).
- Tiến độ **publish** lên kênh Redis; **mọi worker subscribe** và fan-out tới client WS cục bộ ⇒ giải bài toán 2.
- Semaphore toàn cục bằng bộ đếm/lease Redis ⇒ bài toán 3. Cancel bằng cờ Redis worker-chủ poll ⇒ bài toán 4.
- Job vẫn chạy như asyncio task trên **một** worker; các worker khác chỉ đọc/subscribe.
- **Ưu:** giải cả 4 bài toán; ít hạ tầng mới; hợp kiến trúc async hiện tại. **Nhược:** thêm Redis là điểm phụ thuộc; cần xử reconnect/mất Redis (degrade về single-worker).

### Phương án B — Task queue chuyên dụng (Arq / Celery / RQ)
- Job **enqueue** vào broker (Redis); tiến trình **worker riêng** kéo ra chạy. API chỉ enqueue + đọc state.
- **Ưu:** tách biệt scale API vs worker; có retry/backpressure/sống sót restart chuẩn mực; `arq` hợp async nhất. **Nhược:** thay đổi lớn nhất — thêm loại tiến trình worker, đổi deploy (thêm worker service trên Render), viết lại vòng đời job. Quá tầm cho bước kế.

### Phương án C — Giữ sqlite (WAL) làm store đa tiến trình + chỉ thêm Redis pub/sub cho WS
- sqlite WAL cho phép **nhiều tiến trình** đọc/ghi cùng file. Chỉ thêm Redis pub/sub cho fan-out WS; semaphore → bộ đếm Redis.
- **Ưu:** ít dời state nhất. **Nhược:** vẫn phải sửa backend sqlite (§6) cho ghi đa tiến trình; sqlite không mạnh khi ghi đồng thời cao; nửa Redis nửa sqlite hơi chắp vá.

### Phương án D — Giữ 1 worker + scale dọc (đứng yên có chủ đích)
- Giữ `--workers 1` (đang an toàn). Scale bằng máy to hơn. **Không đổi kiến trúc.**
- **Ưu:** 0 rủi ro, 0 hạ tầng mới. **Nhược:** không scale ngang.
- **Đáng cân nhắc:** sau item 5 (I/O ra khỏi loop), **một** worker đã phục vụ được nhiều job đồng thời hơn hẳn. Có thể anh **chưa cần** multi-worker ngay.

## 5. Khuyến nghị

**Trước mắt:** xác nhận anh có **thực sự cần multi-worker bây giờ** không. Nếu tải một-worker (đã nới nhờ item 5) còn dư → **Phương án D**, để #6 lại, làm việc giá trị hơn.

**Khi cần scale ngang:** **Phương án A**, làm **theo pha** để mỗi pha tự đứng được:
- **Pha 1 — WS pub/sub qua Redis:** ✅ **XONG** (commit trên nhánh). `ConnectionManager.broadcast` giờ publish lên kênh Redis; mỗi worker chạy subscriber → broadcast cục bộ. Mọi call site `manager.broadcast(...)` cũ tự động fan-out chéo worker, **0 thay đổi call site**. Degrade an toàn về local khi `WS_REDIS_URL` rỗng/không nối được (mặc định). Test thật với redis: cross-worker fan-out + không nhân đôi + skip trung thực khi vắng redis. *(Giá trị lớn nhất, rủi ro thấp nhất.)*
- **Pha 2 — Semaphore toàn cục** ✅ **XONG.** `api/coordination.py::JobCoordinator` giữ slot bằng **lease sorted-set Redis**, acquire **atomic bằng Lua** (zcard-rồi-zadd bị đua nếu không atomic), có heartbeat refresh lease và TTL thu hồi slot của worker chết. `_process_job_with_limit` giờ giữ slot của coordinator. Fallback: `asyncio.Semaphore` cục bộ khi không có Redis.
- **Pha 3 — Cancel chéo worker + đọc state không stale** ✅ **XONG.** `cancel_job` publish sự kiện cancel; subscriber mỗi worker cancel task **nếu worker đó sở hữu** (handler `CancelledError` sẵn có ghi CANCELLED vào sqlite). `get_job` giờ tin store bền hơn cache cục bộ cho job worker này không chạy.
- **Pha 4 — Bật `--workers N`** ✅ **SẴN SÀNG (opt-in).** `render.yaml` giữ `--workers 1` mặc định cho an toàn; bật multi-worker bằng cách **set `WS_REDIS_URL`** (Redis) rồi nâng `--workers`. **Không nâng workers khi chưa có Redis** — mỗi worker sẽ rơi về state cục bộ (đúng bug P0-6 cũ). Hướng dẫn + env mẫu đã ghi trong `render.yaml`.

A là bước đệm: nếu sau này cần retry/backpressure bền thì tiến hoá lên B (arq) mà không phí công.

## 6. Phụ thuộc bắt buộc: sửa backend sqlite (nối với "sqlite off-loop")

`core/database/sqlite_backend.py` hiện **dùng chung 1 connection** → (a) chưa an toàn chạy off-loop đa luồng (đã nêu khi làm sqlite pt.1), (b) chưa lý tưởng cho đa tiến trình. Dù chọn A hay C, nên nâng backend sang **connection-per-call (hoặc pool) + WAL + busy_timeout** trước. Việc này cũng **mở khoá** phần "sqlite off-loop" còn hoãn cho `JobRepository`. Đề xuất tách 1 PR nền: "sqlite backend: per-call conn + WAL + timeout", làm trước Pha 1.

## 7. Rủi ro & câu hỏi cần anh quyết

1. **Có cần multi-worker ngay không?** (Nếu chưa → chọn D, dừng #6.) — *quyết định lớn nhất.*
2. Nếu có: **được thêm Redis** trên Render (add-on) chứ? (A và C đều cần Redis cho WS pub/sub.)
3. Bản ghi job: **giữ ở sqlite** (đơn giản) hay **dời sang Redis + snapshot bền** (nhanh hơn, phức tạp hơn)?
4. Chấp nhận làm **PR nền sửa sqlite backend** trước không? (Em khuyến nghị có — lợi cả #6 lẫn sqlite off-loop.)
5. Mức độ đồng thời mục tiêu (bao nhiêu job song song, bao nhiêu worker/máy) để em định cỡ lease/semaphore.

---

**Bước kế:** anh chọn **D (hoãn)** hay **A (làm theo pha)**; nếu A, xác nhận Redis + trả lời §7 → em viết TIP Pha 1 (WS pub/sub) và bắt đầu code. Tới lúc đó mới đụng code.
