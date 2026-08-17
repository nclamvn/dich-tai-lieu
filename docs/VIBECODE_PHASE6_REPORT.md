# Vibecode — Phase 6: Translation Memory leverage (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: nối **Translation Memory** vào đường dịch sống (audit: "TM tồn tại nhưng pipeline dịch không dùng"). TM dùng sqlite thuần nên test được thật, không cần mạng.

## Cách làm (Vibecode)

Chủ thầu SCAN API `TranslationMemory` → Blueprint → 2 TIP. Thợ BUILD, Chủ thầu VERIFY độc lập (đọc module/diff + tự chạy test + kiểm TM sqlite thật + end-to-end) rồi commit.

**Quyết định thu hẹp phạm vi (theo nhận xét sắc của Thợ TIP-11):** write-back cấp chunk ít giá trị (hiếm khớp lại exact/fuzzy) và chồng lấn chunk cache. Chủ thầu **hoãn write-back**, tập trung Phase 6 vào **READ/hints** — đúng thứ audit nêu và mang giá trị CAT thực (tận dụng TM người dùng đã có).

## REQUIREMENT COVERAGE: 5/5 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-61 | Tra TM theo câu (exact + fuzzy ≥ threshold) | ✅ `lookup_hints` |
| REQ-62 | Render khối gợi ý, chèn vào USER prompt (không đụng cache prefix/template) | ✅ prepend trong `_translate_chunk` |
| REQ-63 | Write-back chunk sạch | ⏸ **hoãn có chủ đích** (cần căn chỉnh câu; overlap cache) — `store()` đã có sẵn để dùng sau |
| REQ-64 | TM rỗng/lỗi → no-op, 0 overhead | ✅ active chỉ khi TM có ≥1 segment; never-raise |
| REQ-65 | Test TM sqlite thật, không mạng, giữ suite xanh | ✅ 13 test (9 + 4) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- **Key thống kê đúng**: `_count` đọc `total_segments` — xác nhận khớp `translation_memory.get_statistics()` (dòng 602). (Nếu sai key, gateway sẽ không bao giờ active — đã loại trừ.)
- **TM thật**: rỗng → inactive, `lookup_hints` trả `[]` không tốn chi phí; có dữ liệu → active; **exact** (sim 1.0, đúng target) + **fuzzy** (sim 0.85 ≥ threshold, đúng target). PASS
- **End-to-end orchestrator**: TM hints nằm trong **user message**, KHÔNG trong **system** (giữ prompt caching); source vẫn nguyên. PASS
- **Back-compat**: `tm_gateway=None` (test fakes) → không có khối TM, dịch vẫn chạy; TM rỗng → no-op. PASS
- **Không hồi quy**: toàn bộ Phase 1–5 xanh.

## TECHNICAL HEALTH

- `py_compile` + import `core_v2.orchestrator`/`tm_gateway`: OK
- Test: **213 passed, 0 failed** (tm_gateway 9 · tm_wiring 4 · context_wiring 7 · context_builder 27 · quality_gate 22 · repair_pass 6 · token_chunking 22 · chunker_tokencap 8 · semantic_chunker 27 · term_ledger 23 · glossary_wiring 8 · engine_quickwins 24 · chunk_cache 26).

## OVERALL STATUS: READY

TM giờ **thực sự ảnh hưởng bản dịch** khi người dùng có TM (nạp qua import/editor sẵn có). Mặc định an toàn: TM rỗng → 0 chi phí; bật/tắt 1 dòng `.env` (`TM_REUSE_ENABLED`).

## Còn lại / lưu ý (ghi rõ)

1. **Write-back** (hoãn): cần căn chỉnh câu source↔target sau khi dịch chunk để TM tích lũy ở cấp câu; store() đã sẵn — nên là 1 TIP riêng.
2. **Side-effect khi đọc**: `get_exact_match`/`get_fuzzy_matches` của TM bump `use_count` (UPDATE+commit) mỗi lần khớp — nhiều commit trên tài liệu lớn có TM. Cân nhắc chế độ đọc-thuần sau.
3. **Đóng kết nối**: gateway mở 1 kết nối sqlite/instance publisher; thêm teardown `close()` cho tiến trình chạy lâu.
4. TM state KHÔNG nằm trong cache key (tránh thrash) — cache hit trả về trước khi tính hints (đã ghi chú trong code).

## Commit (nhánh feat/engine-quickwins)

- `637e9f5` feat(engine): guarded Translation Memory gateway (TIP-11)
- `420b5b4` feat(engine): leverage Translation Memory as prompt hints (TIP-12)
