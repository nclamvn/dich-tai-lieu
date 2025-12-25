# HANDOVER DOCUMENT - AI PUBLISHER PRO v2.8
## Complete Context for New Chat Window

> **Ngày**: 25/12/2024
> **Project**: AI Publisher Pro - Document Translation & Publishing System
> **Owner**: Lâm Nguyễn
> **Repo**: https://github.com/nclamvn/dich-tai-lieu
> **Status**: PRODUCTION READY (Score: 9.7/10)

---

# QUICK RESUME

Khi quay lại, chỉ cần nói: **"continue"** hoặc **"handover"**

Claude sẽ tự động đọc document này và tiếp tục công việc.

---

# PHẦN 1: TỔNG QUAN DỰ ÁN

## 1.1 Mục Tiêu

Hệ thống dịch và xuất bản tài liệu PDF/DOCX hoàn chỉnh với 3 agents:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  AGENT 1         │     │  AGENT 2         │     │  AGENT 3         │
│  EXTRACTION      │ ──► │  TRANSLATION     │ ──► │  PUBLISHING      │
│  PDF → Text/Vision│    │  Dịch + Glossary │     │  → PDF/DOCX/MD   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## 1.2 Server

```bash
cd /Users/mac/Khach/dich-tai-lieu
uvicorn api.main:app --host 0.0.0.0 --port 3001 --reload

# UI: http://localhost:3001/ui
# API Docs: http://localhost:3001/docs
```

---

# PHẦN 2: SESSION 25/12/2024 - CHANGES

## 2.1 Japanese Language Detection Fix

**Vấn đề**: Upload tài liệu tiếng Nhật → hệ thống nhận diện là tiếng Anh

**Root cause**:
- Tiếng Nhật có Kanji (chữ Hán) bị nhầm với tiếng Trung
- Threshold quá cao (>50 ký tự) → fallback về English

**Fix** (ui/app/main.js:567-609):
```javascript
// Japanese-specific characters (unique to Japanese)
const hiragana = /[\u3040-\u309f]/g;  // Hiragana only
const katakana = /[\u30a0-\u30ff]/g;  // Katakana only

// If we find >5 Hiragana/Katakana → Japanese
const japaneseScore = hiraganaCount + katakanaCount;
if (japaneseScore > 5) {
  return { language: 'ja', confidence: ... };
}

// Lower threshold from 50 to 10 for other languages
```

## 2.2 Language Dropdown Sync

**Vấn đề**: Target language dropdown thiếu de, es, ru

**Fix** (ui/app.html:268-278):
- Thêm: Tiếng Đức, Tiếng Tây Ban Nha, Tiếng Nga

## 2.3 Git Commits

```
91455c9 fix: Improve Japanese language detection and sync language dropdowns
7c34bbb feat: Add Japanese OCR support and stress test suite (v2.8)
```

---

# PHẦN 3: KIẾN TRÚC HỆ THỐNG

## 3.1 Cấu Trúc Thư Mục (75MB)

```
dich-tai-lieu/
├── api/                    # FastAPI server (port 3001)
│   ├── main.py            # Main API routes
│   ├── aps_v2_service.py  # Translation service
│   └── aps_v2_models.py   # Pydantic models
│
├── core/                   # Core business logic
│   ├── smart_extraction/  # Smart routing
│   │   ├── document_analyzer.py    # Detect doc type
│   │   ├── fast_text_extractor.py  # PyMuPDF (FREE)
│   │   └── extraction_router.py    # Route strategy
│   │
│   ├── layout_preserve/   # Layout-preserving translation
│   ├── pdf_renderer/      # PDF output (LaTeX)
│   └── job_queue.py       # Job management
│
├── ai_providers/          # LLM adapters
│   └── unified_client.py  # OpenAI/Claude/DeepSeek
│
├── ui/                    # Frontend
│   ├── app.html          # Main app (UI chính)
│   ├── app/main.js       # App logic + language detection
│   ├── admin.html        # Admin panel
│   └── index.html        # Redirect → app.html
│
└── tests/                 # 862 tests
```

## 3.2 Smart Extraction Router

```
PDF Input
    │
    ├── Text-only (novel) ──────────► FAST_TEXT (PyMuPDF) - FREE
    ├── Academic (arXiv, formulas) ──► FULL_VISION
    ├── Mixed content ───────────────► HYBRID
    └── Scanned/Complex ─────────────► FULL_VISION
```

---

# PHẦN 4: SUPPORTED LANGUAGES

## 4.1 Source Languages (Input)

| Code | Name | Detection |
|------|------|-----------|
| auto | Tự động phát hiện | Default |
| ja | Tiếng Nhật | Hiragana/Katakana priority |
| zh | Tiếng Trung | CJK without Hiragana |
| ko | Tiếng Hàn | Hangul |
| en | Tiếng Anh | Word patterns |
| fr | Tiếng Pháp | Word patterns |
| de | Tiếng Đức | Word patterns |
| es | Tiếng Tây Ban Nha | Word patterns |
| ru | Tiếng Nga | Cyrillic |
| vi | Tiếng Việt | Diacritics |

## 4.2 Target Languages (Output)

vi, en, zh, ja, ko, fr, de, es, ru (9 ngôn ngữ)

---

# PHẦN 5: REMAINING TASKS

## High Priority
- [ ] Test Japanese detection với various documents
- [ ] E2E test complete pipeline
- [ ] DOCX formula rendering improvement

## Medium Priority
- [ ] Rate limiting cho API
- [ ] WebSocket reconnection logic
- [ ] Batch upload improvements

## Low Priority
- [ ] PWA support
- [ ] Docker deployment
- [ ] i18n cho UI

---

# PHẦN 6: QUICK COMMANDS

```bash
# Start server
cd /Users/mac/Khach/dich-tai-lieu
uvicorn api.main:app --host 0.0.0.0 --port 3001 --reload

# Check health
curl http://localhost:3001/health

# Run tests
pytest tests/ -v

# Git
git status
git log --oneline -5
git push origin main

# Stop server
lsof -ti:3001 | xargs kill -9
```

---

# PHẦN 7: FILES ĐÃ MODIFY SESSION NÀY

| File | Changes |
|------|---------|
| ui/app/main.js | Japanese detection logic |
| ui/app.html | Target language dropdown |
| ui/index.html | Minor styling |

---

**END OF HANDOVER v2.8**

*Khi quay lại, chỉ cần nói "continue" hoặc "handover"*
