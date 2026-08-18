# Vibecode — Phase 5: Rolling cross-chunk context (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: vá lỗi ngữ cảnh xuyên chunk (audit #3). `previous_summary`/`next_preview` trước đây chỉ là **100 ký tự ĐẦU** của chunk kề — sai cả hướng (đáng ra là phần CUỐI của chunk trước) lẫn chất lượng (cắt giữa từ) — làm mạch văn đứt gãy giữa các chương.

## Cách làm (Vibecode)

Chủ thầu SCAN `semantic_chunker._finalize_chunks` + hợp đồng test → Blueprint → 2 TIP. Thợ BUILD. Thiết kế giữ concurrency Phase 1: ngữ cảnh **tất định, không LLM** (đuôi chunk trước theo ranh giới câu + gist cuộn), tùy chọn tóm tắt LLM gated OFF.

**Ngoại lệ trust boundary (ghi theo Vibecode rule #8):** subagent Thợ của TIP-10 bị **ngắt giữa chừng do giới hạn phiên** SAU khi đã hoàn tất code (settings, `_finalize_chunks`, `_summarize_chunks`, pre-pass) nhưng TRƯỚC khi viết file test. Chủ thầu đã: (1) đọc & verify toàn bộ code Thợ để lại là đúng TIP; (2) tự viết `tests/unit/test_context_wiring.py`; (3) chạy verify đầy đủ. Lý do override: re-dispatch có nguy cơ lặp lại lỗi giới hạn phiên và tốn budget; phần còn thiếu là cơ học (test) trên code đã đúng.

## REQUIREMENT COVERAGE: 6/6 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-51 | Lấy ĐUÔI chunk trước theo ranh giới câu (không phải 100 ký tự đầu) | ✅ `last_sentences` |
| REQ-52 | Gist cuộn từ câu chủ đề chunk cũ (cửa sổ, ngân sách) | ✅ `build_running_gist` (loại trừ chunk liền trước → không lặp) |
| REQ-53 | Head chunk sau cho next-preview | ✅ `first_sentences` |
| REQ-54 | Wiring thay logic 100-ký-tự trong `_finalize_chunks`, giữ concurrency | ✅ tất định, 0 LLM call |
| REQ-55 | Tùy chọn tóm tắt LLM (gated OFF) | ✅ `_summarize_chunks` + `TRANSLATION_CONTEXT_SUMMARY_ENABLED=false` |
| REQ-56 | Test không mạng, giữ `test_semantic_chunker` xanh | ✅ 34 test (27 + 7) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- **Previous = ĐUÔI, không phải đầu**: chunker thật (3 chương, 9671 ký tự) → `chunk[1].previous_summary` chứa "KẾT chương một" (câu cuối chunk 0), KHÔNG phải câu đầu. PASS
- **Gist bao chunk cũ, không lặp đuôi**: `chunk[2].previous_summary` có cả "Bbb two." (đuôi liền trước) và "Aaa" (gist chunk 0), "Bbb two." xuất hiện đúng 1 lần. PASS
- **Ngữ nghĩa None biên**: `chunk[0].previous_summary is None`, `last.next_preview is None` — giữ đúng hợp đồng `test_semantic_chunker`. PASS
- **Summary pre-pass**: `_summarize_chunks` (client giả) trả 1 tóm tắt/chunk, chạy song song; summaries đưa được vào gist chunk sau. PASS
- **Guard**: `_summarize_chunks` với client raise → `["",""]` (giữ ngữ cảnh tất định). PASS
- **Không hồi quy**: toàn bộ Phase 1–4 xanh; default (summary OFF) không thêm LLM call nào.

## TECHNICAL HEALTH

- `py_compile` + import `core_v2.orchestrator`/`semantic_chunker`/`context_builder`: OK
- Test: **200 passed, 0 failed** (context_builder 27 · context_wiring 7 · semantic_chunker 27 · chunker_tokencap 8 · token_chunking 22 · engine_quickwins 24 · glossary_wiring 8 · term_ledger 23 · quality_gate 22 · repair_pass 6 · chunk_cache 26).

## OVERALL STATUS: READY

Ngữ cảnh mới **tất định, rẻ (0 LLM call mặc định), giữ concurrency**. Bản nâng LLM (tóm tắt thật) sẵn sàng nhưng tắt mặc định để không nhân đôi chi phí — bật 1 dòng `.env` khi cần chất lượng mạch văn cao nhất.

## Còn lại (cho phase sau)

1. Nối Translation Memory (tái dùng câu) vào pipeline.
2. Tích hợp điểm verifier LLM (Stage 6) vào quality gate.
3. Dọn code chết/trùng (2 stack provider, 3 glossary, Vision chết trong orchestrator).
4. Đấu GLOSSARY_NAME→ID; snap boundary về ranh giới từ; sizing paragraph theo token.

## Commit (nhánh feat/engine-quickwins)

- `655c35c` feat(engine): rolling cross-chunk context builder (TIP-09)
- `a68b2eb` feat(engine): wire rolling context + optional LLM summary (TIP-10)
