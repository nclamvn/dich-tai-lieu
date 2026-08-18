# Vibecode — Phase 3: Token-aware, structure-preserving chunking (VERIFY REPORT)

Ngày: 2026-08-17 · Nhánh: `feat/engine-quickwins` · Chủ thầu + Thợ (subagent) · 2 TIP.

Mục tiêu: vá lớp **chia chunk** — nguồn của lỗi cắt cụt âm thầm và phá cấu trúc. Trọng tâm là **bug mega-chunk**: `_detect_boundaries_with_claude` chỉ lấy mẫu 10.000 ký tự đầu, nhưng `_chunk_by_boundaries` nối `len(text)` làm mốc cuối → mọi thứ sau boundary ≤10k dồn vào **một chunk khổng lồ** vượt `max_tokens` của model.

## Cách làm (Vibecode)

Chủ thầu SCAN file thật + hợp đồng test `test_semantic_chunker.py` → Blueprint → 2 TIP. Thợ BUILD, Chủ thầu VERIFY độc lập (đọc diff + tự chạy test + kiểm bất biến trên input đối kháng) trước khi commit. Trust boundary giữ nguyên.

## REQUIREMENT COVERAGE: 7/7 (100%)

| REQ | Nội dung | Trạng thái |
|-----|----------|------------|
| REQ-31 | Ước lượng token VN/CJK-aware (không cần tokenizer) | ✅ `estimate_tokens` |
| REQ-32 | Vá bug mega-chunk (boundary ≤10k áp cho toàn văn) | ✅ token-cap pass trong `_finalize_chunks` |
| REQ-33 | `_simple_chunk` bảo toàn cấu trúc (bỏ `split()/join()`) | ✅ dùng `chunk_text_by_tokens` |
| REQ-34 | Log thay vì nuốt lỗi boundary | ✅ `logger.warning` |
| REQ-35 | Nhận heading tiếng Việt viết thường + markdown h1–h6 | ✅ pattern `\d+\.\s+\S.{4,60}` / `#{1,6}` |
| REQ-36 | Trần token cứng cho MỌI chunk | ✅ `_enforce_token_cap` áp mọi path |
| REQ-37 | Test không cần mạng/tokenizer | ✅ 30 test (22 + 8) |

## SCENARIO RESULTS (Chủ thầu verify độc lập)

- **Mega-chunk qua đường boundary thật** (văn bản ~110k ký tự, mock LLM trả `[2000,5000]`): 18 chunk, **token lớn nhất 1998 ≤ 2000** budget — chunk khổng lồ đuôi đã bị chẻ. PASS
- **Bảo toàn nội dung**: đường enforcement/`chunk_text_by_tokens` giữ **chính xác** 8000/8000 từ; đường boundary không mất chữ (16302 ≥ 16300; +2 là do char-slice của boundary, xem "còn lại"). PASS
- **Bất biến trần token** trên 5 input đối kháng × 3 ngân sách (blob 1 dòng, VN nhiều đoạn, CJK, khối LaTeX, token bất khả phân): mọi chunk ≤ budget. PASS
- **Cấu trúc**: đoạn nhiều `\n\n` giữ nguyên khi budget lớn; `_simple_chunk` giữ newline (không còn blob). PASS
- **Heading VN viết thường** "1. giới thiệu…" nhận ≥2 chương; văn xuôi thường vẫn 0 chương. PASS
- **Không hồi quy**: `test_semantic_chunker.py` (27) + toàn bộ Phase 1/2 xanh.

## TECHNICAL HEALTH

- `py_compile` + `import core_v2.semantic_chunker` / `core_v2.token_chunking`: OK
- Test: **138 passed, 0 failed** (token_chunking 22 · chunker_tokencap 8 · semantic_chunker 27 · engine_quickwins 24 · term_ledger 23 · glossary_wiring 8 · chunk_cache 26).

## OVERALL STATUS: READY

Cơ chế then chốt (token-cap trong `_finalize_chunks`) là **backstop cứng**: bất kể path nào tạo ra chunk quá khổ, nó luôn bị chẻ về dưới budget trước khi trả ra — nên bug mega-chunk bị vô hiệu tận gốc, và về sau thêm path mới cũng tự động được bảo vệ.

## Còn lại (pre-existing / ngoài phạm vi — ghi rõ)

1. `_chunk_by_boundaries` cắt tại offset ký tự do LLM trả → có thể cắt **giữa từ** (tách 1 từ thành 2 mảnh, không mất nội dung). Nhỏ, có sẵn; snap về ranh giới từ gần nhất là fix 1 dòng cho phase sau.
2. `_paragraph_chunk`/`_split_large_section` vẫn chia sơ bộ theo **ký tự** (TARGET/MAX_CHUNK); token-cap là backstop nên vẫn đúng, nhưng có thể chuyển hẳn sang sizing theo token để granularity khớp budget ngay từ đầu.
3. `isinstance(b, int)` chấp nhận `bool` (True→1) trong lọc boundary — có sẵn, thêm guard 1 dòng sau.
4. Hằng 3.5 ký tự/token là heuristic; nếu có tokenizer thật khi eval thì hiệu chỉnh theo ngôn ngữ đích.

## Commit (nhánh feat/engine-quickwins)

- `c7e6770` feat(engine): token-budgeted chunking primitives (TIP-05)
- `6186d0b` fix(engine): token-cap enforcement kills mega-chunk (TIP-06)
