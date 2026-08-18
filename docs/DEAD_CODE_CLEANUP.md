# Dọn code chết `core/` — bằng chứng & lộ trình (#8)

Ngày: 2026-08-18 · Nhánh: `feat/engine-quickwins`

**Phương pháp (không đoán):** (1) import `api.main` trong sandbox, chụp `sys.modules` → closure sống tĩnh; (2) AST-parse toàn repo, resolve cả relative import, tách import top-level vs lazy-trong-hàm; (3) audit `importlib`/late-import rồi import lại từng target lazy → closure **runtime thật 263 module**; (4) Chủ thầu **grep kiểm chứng độc lập** từng ứng viên trước khi xoá. Mọi verdict "chết" đều đối chiếu với 263-module runtime set.

## Đã xoá — Batch 1 (commit này) · ~13.7K dòng · 0 tham chiếu bất kỳ

Xoá + verify: `import api.main` OK, **2012 test collect không lỗi**, **378 test engine/api/security pass**.

| path | loại | vì sao chết |
|------|------|-------------|
| `core/batch_queue/` | pkg | 0 ref (live/dyn/test/script) |
| `core/pdf_templates/` | pkg | 0 ref |
| `core/performance/` | pkg | 0 ref |
| `core/smart_pipeline/` | pkg | 0 ref |
| `core/pdf_renderer/` | pkg | 0 ref ngoài; `pdf_renderer` sống là `pdf_engine` + `pdf_renderer_v2` (khác file) |
| `core/logging_config.py` | mod | logger sống là `config/logging_config.py` (57 ref) — `core.logging_config` 0 ref |
| `core/glossary.py` | mod | bị package `core/glossary/` che; **không** loader theo path (chỉ `export.py` có loader) |
| `core/ocr_deepseek.py.deprecated` | file | không import được, 0 ref |
| `core/ocr/deepseek_client.py.deprecated` | file | như trên |

## Bẫy — TRÔNG chết nhưng SỐNG (tuyệt đối không xoá)

Đây là phần khiến "dọn code chết" nguy hiểm nếu chỉ grep nông:

- `core/export.py` (module) — bị package `core/export/` che, **nhưng** `core/batch_processor.py:68` nạp nó **theo đường dẫn file** bằng `importlib.spec_from_file_location`. SỐNG.
- `core/layout_cleaner.py` — SỐNG **bắc cầu qua lazy**: `stem/__init__ → stem_translator → layout_cleaner`.
- `core/pdf_renderer_v2/` — SỐNG qua lazy trong `export.py:1066` (mà export.py lại được nạp động).
- `core/glossary_legacy.py` — SỐNG: import top-level bởi `core/translator.py:47` + `core/batch_processor.py:59`. *(Sổ nợ trước ghi "4 bản glossary gộp về 1" là chưa đúng: `glossary_legacy` đang được dùng thật.)*
- `core/book_writer/` — được tham chiếu (lazy từ `api/book_writer_service.py`) nhưng **đang lỗi `SyntaxError`** ở `core/book_writer/prompts.py:187` (f-string chứa backslash). Không phải chết → **cần sửa**, đừng xoá.
- Còn sống qua lazy: `health_monitor, latex, latex_utils, ocr, quality, services, stem, streaming`.
- `glossary/` (top-level) — **không phải code**, là thư mục **dữ liệu** `.json` (default/finance/stem…). Không thuộc diện code chết.

## Chờ anh duyệt — Batch 2 (chết cho app, chỉ test dùng)

Xoá được **nhưng phải xoá kèm test của chúng** (test đang test code chết). Vì việc này bỏ luôn phần coverage đó nên em để anh quyết:

| module chết | test phải xoá kèm |
|-------------|-------------------|
| `core/formatting/` (~8.5K dòng) | `test_format_003/004`, `rri_t/.../test_formatting_rri`, phần dùng trong `test_e2e_pipeline`/`test_stress_suite` |
| `core/shared/` | phần trong `test_e2e_pipeline` (và chỉ `core/formatting/` dùng ngoài test) |
| `core/layout_preserve/` | `tests/test_translategemma_integration.py` |
| `core/segmentation/` | `tests/stress/test_stress_suite.py` |

## Chờ anh xác nhận — Batch 3 (chết cho app, nhưng script/CLI còn gọi)

Xoá sẽ làm hỏng các entrypoint rời. Xác nhận các script/CLI này đã ngừng dùng rồi mới xoá:

| module | bị gọi bởi |
|--------|-----------|
| `core/analytics.py` | `scripts/demo_phase2.py` |
| `core/editorial/` | `scripts/benchmark_optimized.py`, `benchmark_template.py` |
| `core/layout/` | 2 script benchmark trên |
| `core/document_classifier.py` | `tests/core/test_document_classifier.py` + `translate_pdf.py` (CLI gốc) |
| `core/layout_preserving_translator.py` | `translate_pdf_preserve_layout.py` (CLI gốc) |

## Đề xuất

Batch 1 an toàn tuyệt đối → đã làm. Batch 2/3 cần quyết định của anh (xoá kèm test / xác nhận script ngừng dùng). Nói em batch nào thì em xoá tiếp theo cùng cách (xoá → verify import + test → commit từng mẻ nhỏ).
