<p align="center">
  <img src="https://img.shields.io/badge/version-2.8-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="License">
  <img src="https://img.shields.io/badge/status-production--ready-brightgreen.svg" alt="Status">
  <img src="https://img.shields.io/badge/Japanese-OCR%20Support-red.svg" alt="Japanese OCR">
</p>

<h1 align="center">🚀 AI Publisher Pro</h1>
<h3 align="center">Hệ thống dịch và xuất bản tài liệu thông minh</h3>

<p align="center">
  <strong>Dịch PDF/DOCX sang tiếng Việt với AI | Hỗ trợ tiếng Nhật | Giữ nguyên layout | Xuất PDF/DOCX/Markdown</strong>
</p>

---

## ✨ Tính năng nổi bật

| Tính năng | Mô tả |
|-----------|-------|
| 🧠 **Smart Extraction** | Tự động nhận diện loại tài liệu, chọn strategy tối ưu |
| 🇯🇵 **Japanese OCR** | Xử lý tài liệu scan tiếng Nhật với PaddleOCR (FREE) |
| 📚 **Đa dạng tài liệu** | Sách, tiểu thuyết, báo cáo kinh doanh, paper học thuật |
| 🔢 **Công thức toán học** | Preserve LaTeX formulas trong academic papers |
| 📊 **Bảng biểu** | Giữ nguyên cấu trúc tables |
| 🌐 **Multi-provider AI** | OpenAI, Claude, DeepSeek |
| 💰 **Tối ưu chi phí** | Text-only docs: FREE extraction (4000x faster) |
| 📄 **Multi-format** | Xuất PDF, DOCX, Markdown |

### 🇯🇵 Japanese Document Support (v2.8)

```
Japanese Scanned PDF + source_lang='ja'
           │
           ▼
┌─────────────────────────┐
│ Document Analyzer       │ ← Detect Japanese academic papers
│ (論文, 研究, 定理...)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ PaddleOCR lang='japan'  │ ← FREE, ~2-3s per page
│ 85-95% accuracy         │   vs Vision API $0.02/page
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ JA → VI Translation     │ ← Specialized prompts
│ + Glossary matching     │   (敬語, 擬音語, etc.)
└─────────────────────────┘
```

---

## 🚀 Hiệu suất

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 BENCHMARK: 600-page novel                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Traditional (Vision API):     ~3 hours  |  ~$15-30           │
│  Smart Extraction:             ~5 mins   |  ~$0.50            │
│                                                                 │
│  ⚡ 97% faster  |  💰 97% cheaper                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Cài đặt

### Yêu cầu
- Python 3.10+
- API key từ OpenAI / Anthropic / DeepSeek

### Bước 1: Clone repo

```bash
git clone https://github.com/nclamvn/dich-tai-lieu.git
cd dich-tai-lieu
```

### Bước 2: Tạo virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

### Bước 3: Cài dependencies

```bash
pip install -r requirements.txt

# Optional: Japanese OCR support (for scanned Japanese documents)
pip install paddleocr paddlepaddle

# Optional: Japanese word segmentation (for advanced features)
pip install fugashi unidic-lite
```

### Bước 4: Cấu hình API keys

```bash
cp .env.example .env
# Sửa file .env, thêm API keys
```

### Bước 5: Chạy server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 3001 --reload
```

### Bước 6: Mở trình duyệt

```
http://localhost:3001/ui
```

---

## 🎯 Cách sử dụng

### Web UI

1. Mở `http://localhost:3001/ui`
2. Upload file PDF/DOCX
3. Chọn ngôn ngữ đích (Tiếng Việt)
4. Chọn AI provider (GPT-4o, Claude, DeepSeek)
5. Click "Dịch"
6. Download kết quả (PDF/DOCX/Markdown)

### API

```python
import requests

# Upload và dịch
response = requests.post(
    "http://localhost:3001/api/v2/translate",
    files={"file": open("document.pdf", "rb")},
    data={
        "target_language": "vi",
        "provider": "openai"
    }
)

job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:3001/api/v2/jobs/{job_id}")
print(status.json())

# Download result
result = requests.get(f"http://localhost:3001/api/v2/jobs/{job_id}/download/pdf")
with open("translated.pdf", "wb") as f:
    f.write(result.content)
```

---

## 🏗️ Kiến trúc

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  AGENT 1         │     │  AGENT 2         │     │  AGENT 3         │
│  EXTRACTION      │ ──► │  TRANSLATION     │ ──► │  PUBLISHING      │
│                  │     │                  │     │                  │
│  • Smart Router  │     │  • Multi-LLM     │     │  • PDF (LaTeX)   │
│  • Fast Text     │     │  • Glossary      │     │  • DOCX          │
│  • Vision API    │     │  • Chunking      │     │  • Markdown      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### Smart Extraction Router

```
PDF Input
    │
    ▼
┌─────────────────────────────────────┐
│  Document Analyzer                  │
│  • Detect text/scanned/formulas     │
│  • Detect academic keywords (EN/JA) │
│  • Analyze complexity               │
└─────────────────────────────────────┘
    │
    ├── Text-only ──────► FAST_TEXT (FREE, 0.1s/page)
    ├── Academic ───────► FULL_VISION (preserve formulas)
    ├── Mixed ──────────► HYBRID (smart combination)
    ├── Scanned + JA ───► OCR (PaddleOCR, FREE)
    └── Scanned other ──► FULL_VISION (Vision API)
```

---

## 📁 Cấu trúc thư mục

```
dich-tai-lieu/
├── api/                    # FastAPI server
│   ├── main.py            # API routes
│   └── aps_v2_service.py  # Translation service
│
├── core/                   # Core logic
│   ├── smart_extraction/  # Smart routing (FAST_TEXT/HYBRID/OCR/VISION)
│   ├── ocr/               # PaddleOCR client (Japanese, Chinese, Korean)
│   ├── segmentation/      # Japanese word segmenter (fugashi)
│   ├── layout_preserve/   # Layout preservation
│   ├── pdf_renderer/      # PDF output
│   └── export.py          # Export formats
│
├── glossary/              # Translation glossaries
│   ├── ja_vi_academic.json  # Japanese academic terms
│   └── ja_vi_novel.json     # Japanese novel terms
│
├── ai_providers/          # LLM adapters
│   └── unified_client.py  # OpenAI/Claude/DeepSeek
│
├── ui/                    # Web interface
│   ├── app.html          # Main app
│   └── admin.html        # Admin panel
│
└── tests/                 # Test suite
    └── stress/           # Stress tests for stability
```

---

## 💰 Chi phí ước tính

### AI Provider Costs (per 1M tokens)

| Model | Input | Output | Best for |
|-------|-------|--------|----------|
| GPT-4o | $2.50 | $10.00 | High quality |
| GPT-4o-mini | $0.15 | $0.60 | Cost effective |
| Claude Sonnet | $3.00 | $15.00 | Long context |
| DeepSeek | $0.14 | $0.28 | Budget friendly |

### Ví dụ chi phí thực tế

| Tài liệu | Trang | Chi phí |
|----------|-------|---------|
| Tiểu thuyết 600 trang | 600 | ~$0.50 |
| Paper học thuật 30 trang | 30 | ~$1.50 |
| Báo cáo kinh doanh 50 trang | 50 | ~$2.00 |

---

## 🔧 Cấu hình

### Environment Variables

```env
# Required - Ít nhất 1 provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Optional
PORT=3001
HOST=0.0.0.0
LOG_LEVEL=INFO
```

### Supported Languages

| Source | Target |
|--------|--------|
| English | Vietnamese |
| Chinese | Vietnamese |
| Japanese | Vietnamese |
| Korean | Vietnamese |
| French | Vietnamese |
| German | Vietnamese |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/unit/test_smart_extraction.py -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run stress tests (stability testing)
python tests/stress/run_stress_tests.py --level low    # Quick test
python tests/stress/run_stress_tests.py --level medium # Normal test
python tests/stress/run_stress_tests.py --level high   # Full stress test
```

---

## 📊 Roadmap

- [x] Smart Extraction Router
- [x] Academic paper support
- [x] Table rendering
- [x] Multi-provider AI
- [x] Japanese OCR support (v2.8)
- [x] Japanese → Vietnamese translation
- [x] Stress test suite
- [ ] Real-time collaboration
- [ ] Browser extension
- [ ] Mobile app
- [ ] Batch processing UI

---

## 🤝 Đóng góp

Chúng tôi hoan nghênh mọi đóng góp! Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết.

```bash
# Fork repo
# Create branch
git checkout -b feature/amazing-feature

# Commit changes
git commit -m "Add amazing feature"

# Push & create PR
git push origin feature/amazing-feature
```

---

## 📄 License

MIT License - Xem [LICENSE](LICENSE) để biết thêm chi tiết.

---

## 🙏 Credits

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [ReportLab](https://www.reportlab.com/) - PDF generation
- [python-docx](https://python-docx.readthedocs.io/) - DOCX generation
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Japanese/Chinese/Korean OCR
- [fugashi](https://github.com/polm/fugashi) - Japanese morphological analyzer
- [OpenAI](https://openai.com/) - GPT models
- [Anthropic](https://anthropic.com/) - Claude models

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/nclamvn">nclamvn</a>
</p>

<p align="center">
  ⭐ Star repo này nếu bạn thấy hữu ích!
</p>
