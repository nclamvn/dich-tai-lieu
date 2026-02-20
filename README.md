<p align="center">
  <img src="https://img.shields.io/badge/version-3.3.1-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.11+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-16-black.svg" alt="Next.js">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="License">
</p>

<h1 align="center">AI Publisher Pro</h1>
<h3 align="center">All-in-one AI Publishing Platform</h3>

<p align="center">
  <strong>Document Translation | AI Book Writer | Screenplay Studio | Translation Memory</strong>
</p>

---

## What is AI Publisher Pro?

An open-source, self-hosted platform that combines AI-powered document translation, book generation, screenplay production, and enterprise translation management. Built with FastAPI + Next.js 16, integrating 4 AI providers with automatic failover.

**Vietnamese-first** — optimized typography (Be Vietnam Pro + Source Serif 4), but supports 55+ languages.

---

## Features

### Core Platform

| Feature | Description | Status |
|---------|-------------|--------|
| **Document Translation** | PDF/DOCX/TXT with layout preservation, parallel processing (5x) | Production |
| **Smart Extraction** | PyMuPDF (free, 0.1s/page) for text, Vision LLM for scanned/STEM docs | Production |
| **Multi-AI Provider** | Auto-fallback: Claude → OpenAI → Gemini → DeepSeek | Production |
| **Translation Memory** | Fuzzy matching, TMX/CSV import/export, domain filtering | Production |
| **Glossary Management** | Term databases, bulk operations, pre-built glossaries | Production |
| **Export System** | PDF, DOCX, EPUB, MOBI output with layout preservation | Production |

### AI Creative Suite

| Feature | Description | Status |
|---------|-------------|--------|
| **Book Writer v2** | 9-agent pipeline: analyst, outliner, writer, editor, proofreader, formatter | Production |
| **Screenplay Studio** | Book-to-screenplay conversion, storyboard generation, Fountain export | Beta |
| **Book-to-Cinema** | AI video generation from books (Veo, Runway, DALL-E, Pika) | Alpha |
| **Editor / CAT Tool** | Segment-by-segment translation editing and review | Beta |

### Infrastructure

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-time WebSocket** | Live job progress, queue stats, filterable events | Production |
| **Batch Processing** | Multi-file queue with concurrent execution | Beta |
| **Authentication** | JWT tokens, API key management, role-based access | Production |
| **Settings System** | Per-section settings with validation and defaults | Production |
| **Dashboard** | Cost tracking, provider analytics, usage statistics | Production |
| **Error Monitoring** | Categorized error tracking, resolution workflow | Production |
| **Usage & Quotas** | Per-user limits, plan-based gating (Free/Basic/Pro/Enterprise) | Production |

---

## Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| 600-page extraction | ~2 hours | ~30 sec | **240x faster** |
| 600-page translation | ~2.5 hours | ~28 min | **5x faster** |
| Total time | ~4.5 hours | ~28 min | **10x faster** |
| Cost per 600 pages | ~$15-30 | ~$0.28 | **50x cheaper** |

---

## Quick Start

### Requirements
- Python 3.11+
- Node.js 20+
- At least 1 AI API key (OpenAI / Anthropic / DeepSeek / Google)

### Setup

```bash
# Clone
git clone https://github.com/nclamvn/dich-tai-lieu.git
cd dich-tai-lieu

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — add your API keys

# Start backend
uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### Environment Variables

```env
# At least 1 required
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
GOOGLE_API_KEY=...
```

---

## Architecture

```
                    +------------------+
                    |   Next.js 16     |
                    |   25 pages       |
                    |   React 19 + TS  |
                    +--------+---------+
                             |
                    REST (292 endpoints) + WebSocket
                             |
                    +--------+---------+
                    |   FastAPI        |
                    |   18 routers     |
                    |   Python 3.11+   |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
  +-------+-------+ +-------+-------+ +-------+-------+
  | Core Engine    | | AI Providers  | | Data Layer    |
  | 77 modules     | | 4 providers   | | 12 SQLite DBs |
  | ~157K LOC      | | Auto-fallback | | WAL mode      |
  +----------------+ +---------------+ +---------------+
```

### Key Directories

```
ai-publisher-pro/
├── api/                    # FastAPI routers & services (65 files)
├── core/                   # Business logic (77 modules)
│   ├── smart_extraction/   # PDF routing (text/vision/OCR)
│   ├── book_writer_v2/     # 9-agent book pipeline
│   ├── screenplay_studio/  # Script generation
│   ├── tm/                 # Translation memory
│   ├── glossary/           # Terminology management
│   ├── export/             # PDF/DOCX/EPUB/MOBI output
│   ├── auth/               # Authentication
│   └── database/           # DB abstraction layer
├── ai_providers/           # Claude, OpenAI, Gemini, DeepSeek
├── frontend/               # Next.js 16 app
│   └── src/app/            # 25 page routes
├── config/                 # Settings (Pydantic)
├── tests/                  # 2,377 test functions
└── data/                   # 12 SQLite databases
```

---

## API Usage

```python
import requests

# Upload and translate
response = requests.post(
    "http://localhost:3000/api/v2/publish",
    files={"file": open("document.pdf", "rb")},
    data={"target_language": "vi", "provider": "openai"}
)
job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:3000/api/v2/jobs/{job_id}")
print(status.json()["status"])

# Download result
result = requests.get(f"http://localhost:3000/api/v2/jobs/{job_id}/download/pdf")
with open("translated.pdf", "wb") as f:
    f.write(result.content)
```

Full API docs: http://localhost:3000/docs

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run without coverage threshold
pytest tests/ --no-cov

# Run specific module
pytest tests/unit/test_smart_extraction.py -v

# Run with coverage report
pytest tests/ --cov=core --cov-report=html
```

**Current:** 2,377 test functions, 1,352+ passing, 15% coverage (improving).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS v4 |
| State | TanStack React Query v5 |
| Database | SQLite with WAL mode (12 databases) |
| AI | OpenAI, Anthropic Claude, Google Gemini, DeepSeek |
| Real-time | WebSocket (native) |
| Auth | JWT + API key management |
| Fonts | Be Vietnam Pro (body), Source Serif 4 (display) |

---

## Roadmap

- [x] Smart Extraction Router (text/vision/OCR)
- [x] Multi-AI provider with auto-fallback
- [x] Book Writer v2 (9-agent pipeline)
- [x] Screenplay Studio
- [x] Translation Memory & Glossary
- [x] Next.js 16 frontend (25 pages)
- [x] Authentication & API keys
- [x] Security hardening (RRI audit — 67 fixes)
- [x] Vietnamese-optimized typography
- [ ] PostgreSQL migration option
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Docker deployment
- [ ] Real-time collaboration
- [ ] Mobile app

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git checkout -b feature/your-feature
git commit -m "Add your feature"
git push origin feature/your-feature
```

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Credits

- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [Next.js](https://nextjs.org/) — Frontend framework
- [OpenAI](https://openai.com/) / [Anthropic](https://anthropic.com/) / [Google](https://ai.google.dev/) / [DeepSeek](https://deepseek.com/) — AI providers
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF extraction
- [ReportLab](https://www.reportlab.com/) — PDF generation
- [python-docx](https://python-docx.readthedocs.io/) — DOCX generation

---

<p align="center">
  Made by <a href="https://github.com/nclamvn">nclamvn</a>
</p>
