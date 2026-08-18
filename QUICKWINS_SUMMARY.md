# Nâng cấp lõi dịch — Quick-wins (2026-08-17)

Nhánh: `feat/engine-quickwins` · 3 commit · 9 file (+516 / −87) · 28 unit test mới, không gây hồi quy.

Toàn bộ tập trung vào **đường dịch sống** (`api → aps_v2_service → core_v2/orchestrator → ai_providers/unified_client`) — đúng nơi tài liệu người dùng thực sự đi qua. Ba trục anh chọn: **chất lượng · tốc độ/độ tin cậy · chi phí**.

## Đã làm gì (và vì sao đáng)

| # | Thay đổi | Trục | Vì sao đáng |
|---|----------|------|-------------|
| QW1 | Dịch ở **temperature 0.3** (trước đây chạy mặc định nhà cung cấp ~1.0) | Chất lượng | Bản dịch trung thành, ít dao động — đây là đòn bẩy chất lượng lớn nhất mà chỉ sửa 1 tham số |
| QW1 | **Registry model theo env** + làm mới ID | Chất lượng/Bảo trì | `claude-sonnet-4-20250514` (cũ) → `claude-sonnet-4-5-20250929`; Gemini `-exp` → bản GA. Đổi model tương lai chỉ cần sửa `.env`, không đụng code |
| QW2 | **Không còn ghép `[TRANSLATION ERROR: n]`** vào tài liệu | Độ tin cậy | Trước đây 1 chunk lỗi → lỗ hổng âm thầm trong file giao cho khách. Giờ job **fail lớn tiếng** kèm số chunk |
| QW2 | **Backoff mũ + jitter** cho mọi lỗi tạm thời; 429 backoff-rồi-fallback; bench provider **có TTL** | Độ tin cậy | Trước: chỉ retry 429 với 15/30/45s cố định; provider lỗi 1 lần bị loại cả đời tiến trình. Giờ tự hồi phục |
| QW3 | **Tách prompt** tĩnh (system) / động (user) + **prompt caching** Anthropic | Chi phí | Khối tĩnh (luật LaTeX + profile + DNA) được cache → **giảm ~30–50% input token** trên tài liệu nhiều chunk |
| QW4 | **Nối ChunkCache** vào core_v2, key gồm model+temperature+profile+version | Chi phí/Tốc độ | Chạy lại tài liệu y hệt (workflow "dịch lại chỉnh tí") không tốn tiền dịch lại; key an toàn, không đụng độ giữa các model |

Thêm: retry khi lệch ngôn ngữ giờ **giữ nguyên system prompt** (không mất chỉ dẫn thuật ngữ/LaTeX); phát hiện **truncation** (`finish_reason=length`) và **không cache** chunk bị cắt cụt.

## Cách kiểm chứng

```bash
git checkout feat/engine-quickwins
pip install anthropic openai pytest pytest-asyncio --break-system-packages

# 28 test quick-win + 22 test cache (regression)
python3 -m pytest tests/unit/test_engine_quickwins.py tests/cache/test_chunk_cache.py -o addopts=""
# => 50 passed
```

Kết quả kiểm thử của phiên này:
- `test_engine_quickwins.py` + `test_chunk_cache.py`: **50 passed**.
- `test_parallel.py`: **xanh hoàn toàn** sau khi cài `pytest-asyncio`.
- `test_vision_fallback.py`: 4 fail **có sẵn từ trước** (không do thay đổi này) — xem dưới.

## Lưu ý: 4 test vision_fallback fail là lỗi có sẵn

Đã chứng minh bằng `git stash` (chạy trên code gốc cũng fail y hệt). Nguyên nhân: commit trước ("add DeepSeek/Gemini API key support") đã thêm `gemini` vào `PROVIDER_ORDER` và `VISION_PROVIDER_ORDER`, nhưng `tests/test_vision_fallback.py` cũ vẫn assert danh sách **chưa có gemini** (ví dụ mong `["anthropic","openai"]` nhưng code là `["anthropic","openai","gemini"]`). Đây là **lệch test-vs-code**, sửa rất nhanh nhưng em để anh quyết vì nó nằm ngoài phạm vi quick-win. Em có thể vá trong 1 commit nếu anh muốn.

## Rủi ro & giả định

- **ID model mặc định**: em đặt theo họ model repo đã dùng ở `book_writer` (`claude-sonnet-4-5-20250929`) và làm tất cả **override được qua `.env`**. Nếu anh muốn mặc định là Opus/khác, chỉ cần set `ANTHROPIC_TEXT_MODEL=...` — không cần sửa code.
- **Prompt caching** dùng `cache_control` (đã GA ở Anthropic SDK hiện hành). Với nhà cung cấp khác, việc tách system/user vẫn an toàn và có lợi (OpenAI tự cache prefix dài).
- Chưa chạy end-to-end với API key thật (sandbox không có key). Đã kiểm ở mức: compile, import, unit test logic thuần + `_translate_chunk` với client giả.

## Bước tiếp theo nên cân nhắc (từ bản audit, KHÔNG nằm trong quick-win)

Xếp theo đòn bẩy giảm dần:
1. **Ngữ cảnh xuyên chunk thật**: hiện `previous_summary`/`next_preview` chỉ là 100 ký tự đầu của chunk kề — nên thay bằng rolling summary + sổ thuật ngữ/nhân danh mang theo. Đây là nguyên nhân chính gây dịch tên/thuật ngữ không nhất quán trong sách dài.
2. **Chunking theo token** (thay vì ký tự) + vá bug boundary-detection (lấy mẫu 10k ký tự nhưng áp offset cho toàn văn → tạo mega-chunk cuối).
3. **Nối glossary + translation memory vào prompt sống** (hiện tồn tại nhưng không được pipeline dịch dùng).
4. **Đóng vòng verifier → dịch lại** các chunk điểm thấp (hiện chỉ chấm điểm rồi bỏ đấy).
5. Dọn code chết/trùng (2 stack provider, 3 bản glossary, đường Vision chết trong orchestrator).

---
*Sinh trong phiên Cowork. Chưa push lên GitHub — anh review diff xong, nếu OK em push nhánh và mở PR.*
