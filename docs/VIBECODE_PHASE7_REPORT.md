# Vibecode — Phase 7: Semantic faithfulness verification (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: đóng vòng verifier (audit #9). Phase 4 chỉ bắt lỗi **tất định** (rỗng/cắt cụt/sai ngôn ngữ/rớt công thức); Phase 7 thêm tầng LLM soi **độ trung thành ngữ nghĩa** (dịch sai/thêm/bớt ý mà gate tất định không thấy), rồi cho chunk đó vào chính vòng repair đã có ở Phase 4.

## Cách làm (Vibecode)

Chủ thầu SCAN verifier + `_repair_suspect_chunks` → Blueprint → 2 TIP. Thợ BUILD, Chủ thầu VERIFY độc lập (đọc module/diff + tự chạy test + kiểm fail-open + end-to-end enabled/disabled) rồi commit.

## REQUIREMENT COVERAGE: 5/5 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-71 | `verify_chunk` 1 lượt LLM → JSON faithful/severity/issue, never-raise, lỗi→faithful | ✅ `semantic_verifier.py` |
| REQ-72 | Tích hợp vào repair: đếm-issue gộp, suspect & adopt dùng gộp | ✅ `_repair_suspect_chunks` |
| REQ-73 | Gated OFF + bounded (cap số chunk soi) | ✅ `TRANSLATION_SEMANTIC_VERIFY_*` |
| REQ-74 | Default OFF → hành vi Phase 4 y nguyên | ✅ `test_repair_pass` xanh không đổi |
| REQ-75 | Test không mạng (client giả) | ✅ 26 test (20 + 6) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- **verify_chunk fail-open**: unfaithful/major bị gán; minor bị ngưỡng chặn (mặc định major); malformed/client-raise → **faithful** (không gán oan); câu rỗng → bỏ qua client (0 call); temperature=0. PASS
- **Repair end-to-end (BẬT)**: chunk **trôi nghĩa nhưng sạch tất định** (đúng tiếng Việt, đủ độ dài) → verify #1 unfaithful → vào repair → re-translate → **verify #2 lại bản sửa** (faithful) → **nhận** (count=1). PASS
- **Repair (TẮT, mặc định)**: **0 verify call**, output y hệt — hành vi Phase 4 byte-for-byte. PASS
- **Bounded**: `semantic_max` giới hạn đúng số verify call. PASS (Thợ) — em xác nhận qua đường disabled/enabled.
- **Không hồi quy**: `test_repair_pass` (6) và toàn bộ Phase 1–6 xanh.

## TECHNICAL HEALTH

- `py_compile` + import `core_v2.orchestrator`/`semantic_verifier`: OK
- Test: **239 passed, 0 failed** (semantic_verifier 20 · semantic_repair 6 · repair_pass 6 · quality_gate 22 · tm_gateway 9 · tm_wiring 4 · context_builder 27 · context_wiring 7 · token_chunking 22 · chunker_tokencap 8 · semantic_chunker 27 · term_ledger 23 · glossary_wiring 8 · engine_quickwins 24 · chunk_cache 26).

## OVERALL STATUS: READY

Kiến trúc "một chunk là suspect-tất-định HOẶC suspect-ngữ-nghĩa, không cả hai" giữ logic adopt thống nhất và đơn giản. Fail-open đảm bảo tầng LLM **không bao giờ gán oan** khi lỗi. Mặc định TẮT → không thêm chi phí/không đổi hành vi; bật 1 dòng `.env` khi cần bắt lỗi ngữ nghĩa sâu (là 1 lượt LLM/chunk sạch, có cap).

## Còn lại (cho phase sau)

1. TM write-back cấp câu (cần alignment source↔target).
2. Dọn code chết/trùng (2 stack provider, 3 glossary, Vision chết trong orchestrator).
3. Đấu GLOSSARY_NAME→ID; sizing paragraph theo token; snap boundary về ranh giới từ; teardown TM.

## Commit (nhánh feat/engine-quickwins)

- `9ba3088` feat(engine): single-call semantic faithfulness verifier (TIP-13)
- `e2649c3` feat(engine): optional semantic verify feeds the repair loop (TIP-14)
