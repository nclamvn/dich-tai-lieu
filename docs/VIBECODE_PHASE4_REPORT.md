# Vibecode — Phase 4: Quality gate + bounded repair (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: biến verifier từ **chấm điểm thụ động** (Stage 6, lưu rồi bỏ đó) thành cơ chế **phát hiện & vá** chunk lỗi. Nhiều lỗi dịch không làm provider raise — chunk rỗng, cắt cụt, rớt công thức, mất nội dung — nên trước đây lọt thẳng vào file giao khách.

## Cách làm (Vibecode)

Chủ thầu SCAN verifier + luồng publish() → Blueprint → 2 TIP. Thợ BUILD, Chủ thầu VERIFY độc lập (đọc diff + tự chạy test + kiểm end-to-end với client giả + chống báo động giả) trước khi commit.

## REQUIREMENT COVERAGE: 4/4 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-41 | Phát hiện chunk lỗi tất định (empty/marker/too_short/wrong_lang/latex_lost/truncated) | ✅ `quality_gate.check_chunk` |
| REQ-42 | Pass sửa có giới hạn, re-translate chunk lỗi (bypass cache) | ✅ `_repair_suspect_chunks` + `force_refresh` |
| REQ-43 | Chèn giữa Stage 3–4, gated + đếm số sửa | ✅ Stage 3.5 trong `publish()` |
| REQ-44 | Test không cần mạng | ✅ 28 test (22 + 6) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- **Repair chỉ sửa chunk lỗi**: 3 chunk, chunk[1] rỗng → 1 LLM call, chunk[1] được vá, chunk[0]/[2] sạch giữ nguyên, count=1. PASS
- **force_refresh bypass cache**: cache seed 'CACHED-BAD' → gọi thường trả CACHED-BAD (0 call); gọi force_refresh gọi client, trả bản mới (khác CACHED-BAD). PASS
- **Adopt-only-if-better**: nếu bản sửa vẫn lỗi (ít hơn issue thì mới nhận), giữ bản gốc, count=0. PASS
- **Bounded**: nhiều suspect hơn `max_repairs` → chỉ sửa `max_repairs` đầu, log cảnh báo. PASS
- **Chống báo động giả** (gate): bản dịch VN dài hơn nguồn EN, bản CJK ngắn hơn, chunk có công thức bảo toàn → đều KHÔNG bị gán suspect; drop thật/rỗng/sai ngôn ngữ/rớt LaTeX → bắt được. PASS
- **Không NameError**: `cache_key` khởi tạo None trước block; nhánh force_refresh không đụng cache_key. PASS
- **Không hồi quy**: default path (`force_refresh=False`) byte-for-byte như cũ; toàn bộ Phase 1/2/3 xanh.

## TECHNICAL HEALTH

- `py_compile` + `import core_v2.orchestrator` / `core_v2.quality_gate`: OK
- Test: **166 passed, 0 failed** (quality_gate 22 · repair_pass 6 · engine_quickwins 24 · glossary_wiring 8 · term_ledger 23 · semantic_chunker 27 · token_chunking 22 · chunker_tokencap 8 · chunk_cache 26).

## OVERALL STATUS: READY

Cổng kiểm định là **tất định** (không phụ thuộc điểm số mờ của LLM) nên rẻ, ổn định, và chạy được không cần API key. Repair **có giới hạn** (bound theo config) và **chỉ nhận khi tốt hơn hẳn** nên không có nguy cơ vòng lặp vô hạn hay làm xấu đi.

## Còn lại (ghi rõ, cho phase sau)

1. Gate chưa nhận cờ `was_truncated` per-chunk ở tầng repair (translated_chunks là list[str] không mang cờ) — chunk cắt-cụt-nhưng-không-rỗng đã bị loại khỏi cache lúc dịch nên tác động nhỏ; muốn repair theo truncation thì thread thêm list[bool] cờ ra khỏi `_translate_chunks`.
2. Có thể phơi `repaired_count` vào `PublishingJob.to_dict()`/metrics để quan sát (hiện chỉ log INFO).
3. Có thể tích hợp thêm điểm số verifier LLM hiện có (Stage 6) làm tín hiệu bổ sung cho gate ở phase sau.

## Commit (nhánh feat/engine-quickwins)

- `e849666` feat(engine): deterministic quality gate (TIP-07)
- `71564ad` feat(engine): bounded repair pass (TIP-08)
