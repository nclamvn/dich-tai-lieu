# Vibecode — Phase "Next" (Item 5): I/O đồng bộ ra khỏi event loop (VERIFY REPORT)

Ngày: 2026-08-18 · Nhánh: `feat/engine-quickwins` · Chủ thầu SCAN + VERIFY · Thợ (subagent) BUILD · 1 TIP.

Mục tiêu (roadmap §4 NEXT, mục #5 — "hạng mục hiệu năng quan trọng nhất"): gỡ trần hiệu năng do **I/O đồng bộ chạy thẳng trên event loop**. Job dịch chạy bằng `asyncio.create_task` trên **loop chính** (`api/aps_v2_service.py:320`), nên bất kỳ call đồng bộ nào bên trong `publish()` **đóng băng cả server** (mọi request/job khác) suốt thời gian nó chạy — không phải chỉ chậm job đó.

## Phát hiện thu hẹp phạm vi (SCAN)

Audit tổng nói "subprocess/PDF/OCR khắp nơi", nhưng soi đúng hot path v2 thì **converter pandoc đã async sẵn** (`asyncio.create_subprocess_exec`, không đụng). Thủ phạm chặn loop thật sự là 3 method **khai `async def` nhưng thân hoàn toàn đồng bộ** ("fake async"):

1. `core_v2/orchestrator.py::_extract_pdf_text_legacy` — `fitz`/`pdfplumber` đồng bộ.
2. `core_v2/output_converter.py::convert_markdown_to_docx_professional` — `python-docx` (DocxRenderer) đồng bộ.
3. `core_v2/output_converter.py::convert_markdown_to_pdf_professional` — `ReportLab` (PdfRenderer) đồng bộ.

Mỗi cái có thể chạy hàng trăm ms → nhiều giây cho tài liệu lớn, và trong lúc đó `/health` cũng treo.

## Cách làm

Module mới `core_v2/aio_utils.py::run_blocking(func, *args, **kwargs)` = wrapper mỏng quanh `asyncio.to_thread` (stdlib, Py3.9+). Chuyển thân đồng bộ của 3 method sang worker thread bằng `await run_blocking(...)`. **Hành vi byte-for-byte y hệt**, chỉ đổi thread chạy. An toàn thread: mỗi lần gọi tự tạo renderer/mở file riêng, không dùng state chung; số job đồng thời vẫn bị semaphore chặn.

## VERIFY (Chủ thầu chạy độc lập, không chỉ tin báo cáo Thợ)

- **Đọc diff**: xác nhận `_extract_pdf_text_sync` = bản trích byte-for-byte của thân cũ; hai `_render()` closure giữ nguyên logic (tạo renderer → `from_markdown` → set title → render) rồi `await run_blocking`. Import mới không tạo vòng lặp import.
- **Cơ chế (test then chốt, chạy 3 lần không flaky)**: trong lúc một `run_blocking(sleep 0.25s)` đang chạy, coroutine `ticker` vẫn tick đều ~0.02s → `max(gap) < 0.15s` → **loop KHÔNG bị chặn**. Nếu chạy on-loop sẽ có 1 gap ~0.25s.
- **Đúng nghiệp vụ**: `_extract_pdf_text_legacy` vẫn đọc đúng text từ PDF thật (fitz tạo file test); DOCX professional render chạy off-loop (ticker song song không bị nghẽn, file output tạo đúng).
- **Không hồi quy**: **286 test engine pass, 0 fail** (toàn bộ Phase 1–7 + item-5 mới + converter + orchestrator). `import api.main` sạch.

## OVERALL STATUS: READY

3 điểm chặn loop nặng nhất trên hot path dịch đã off-loop. Đây là bước tăng *khả năng phục vụ đồng thời* của server (một job xuất DOCX nặng không còn treo các request khác), không đổi kết quả dịch.

## Còn lại của NEXT (chưa làm phiên này — lý do)

- **sqlite đồng bộ rải rác trên loop** (progress `update_progress`, đọc TM/glossary): cần gom về tầng repository + xử thread-safety cho kết nối sqlite → nên làm thành 1 chunk riêng, cẩn thận.
- **Resume thật theo cache (#7)**: *giá trị đã giảm* — ChunkCache (Phase 1) khiến re-run tài liệu trùng gần như miễn phí + ra kết quả y hệt (đã chứng minh ở e2e smoke). Lợi ích còn lại chủ yếu là UX (%) + khỏi re-extract/re-assemble; ưu tiên thấp hơn.
- **State job ra store dùng chung (#6)** và **dọn hai-stack (#8)**: thay đổi kiến trúc lớn/nhiều rủi ro → mỗi cái là một phase riêng.
- **Frontend base-URL + error state (#9)**: gọn, verify offline được (tsc/build); ứng viên tốt cho phiên kế.

## Commit

- `a5416c8` perf(engine): run blocking PDF extraction and DOCX/PDF rendering off the event loop
