# Vibecode — Phase 2: Terminology Consistency Engine (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: khóa **nhất quán thuật ngữ / tên riêng** xuyên suốt mọi chunk — điểm yếu chất lượng lớn nhất còn lại sau Phase 1 (trước đây "ngữ cảnh" chỉ là 100 ký tự đầu chunk kề nên tên/thuật ngữ dịch lệch giữa các chương).

## Cách làm (Vibecode)

Chủ thầu (mình) SCAN → RRI rút gọn → Vision → Blueprint → viết 2 TIP. Thợ (subagent) BUILD từng TIP và nộp Completion Report. Chủ thầu VERIFY độc lập từng TIP (đọc code + tự chạy test + kiểm import-guard), commit sau khi đạt. Trust boundary giữ đúng: **Chủ thầu không code**, Thợ code theo TIP, thấy tốt hơn thì ghi SUGGESTIONS chứ không tự đổi kiến trúc.

## REQUIREMENT COVERAGE: 8/8 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-01 | Tự trích thuật ngữ/tên riêng (1 lượt LLM pre-pass) | ✅ `extract_terms()` + gọi trong `publish()` |
| REQ-02 | Nạp glossary người dùng (tùy chọn) | ✅ `load_glossary_ledger()`, lazy + guarded |
| REQ-03 | Merge có ưu tiên (glossary 9 > auto 5), khử trùng | ✅ `TermLedger.add/merge` |
| REQ-04 | Inject vào **khối system được cache** | ✅ slot `{glossary}` trong `TRANSLATION_SYSTEM` |
| REQ-05 | Ledger → cache key (đổi thuật ngữ ⇒ vô hiệu cache cũ) | ✅ fingerprint gấp vào key |
| REQ-06 | Degrade an toàn (thiếu key/sqlalchemy/trích lỗi ⇒ vẫn dịch) | ✅ guard mọi nhánh, đã kiểm chặn sqlalchemy |
| REQ-07 | Khớp diacritic/CJK-safe | ✅ `relevant_for` (substring casefold, không dùng `\b`) |
| REQ-08 | Test không cần mạng/sqlalchemy | ✅ 31 test (23 + 8) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- Có ledger → system message chứa khối `TERMINOLOGY` + đúng bản dịch target ("Mạng nơ-ron"). PASS
- `ledger=None` (mặc định) → không có khối TERMINOLOGY, hành vi y hệt Phase 1. PASS (back-compat)
- Chặn `sqlalchemy/anthropic/openai` khi import → module `term_ledger` vẫn nạp sạch; glossary loader trả rỗng; dịch vẫn chạy. PASS
- Merge ưu tiên: glossary (9) đè auto (5) cùng khóa không phân biệt hoa/thường. PASS
- Khớp CJK "机器学习" trong câu CJK (trường hợp regex `\b` bỏ sót). PASS
- Cache key đổi theo fingerprint ledger; fingerprint rỗng = "noterms" (khớp key tiền-ledger). PASS

## TECHNICAL HEALTH

- `py_compile` + `import core_v2.orchestrator` / `core_v2.term_ledger`: OK
- Test liên quan: **81 passed, 0 failed** (`test_glossary_wiring` 8 · `test_engine_quickwins` 24 · `test_term_ledger` 23 · `test_chunk_cache` 26) — Phase-1 **không hồi quy**.
- Pre-existing, KHÔNG do Phase 2 (đã đối chiếu baseline): 2 test `tests/integration/test_pdf_api_integration.py::TestPdfRouterSignature` (file API router không đụng tới); và lệch test `vision_fallback` do `gemini` thêm từ commit trước.

## OVERALL STATUS: READY — với các hạng mục hoãn (đã ghi rõ)

Hoãn có chủ đích (để Phase 2 gọn, đúng cơ chế):
1. **Translation Memory (tái dùng câu)** — cơ chế khác (memo cấp câu, chồng lấn chunk cache Phase 1). Sẽ làm ở phase riêng.
2. **Phân giải glossary theo tên → ID**: hiện dùng `TRANSLATION_GLOSSARY_IDS` (ID tường minh). Đấu `GLOSSARY_NAME` (async `GlossaryService`) để sau.
3. **Cắt token theo chunk** (`relevant_for` từng chunk): giữ nguyên cả-ledger để ổn định prompt-cache; chỉ cân nhắc khi glossary vượt `MAX_TERMS` thường xuyên.

## Rủi ro/giả định

- Chưa chạy end-to-end với API key thật (sandbox không có key) — verify ở mức compile/import/unit + `_translate_chunk` với client giả. Auto-extract thật cần 1 lượt LLM/tài liệu (đã guard, lỗi ⇒ rỗng).
- Ledger nằm trong khối cache → nếu tài liệu rất nhiều thuật ngữ, cap `MAX_TERMS` (mặc định 80) bảo vệ kích thước prompt.

## Commit (nhánh feat/engine-quickwins)

- `7f76621` feat(engine): term ledger module (TIP-01)
- `7d3d076` feat(engine): wire terminology ledger into live translation (TIP-02)

(Phase 1 trước đó: `ebcba1e`, `09c9191`, `c8b29ac`.)
