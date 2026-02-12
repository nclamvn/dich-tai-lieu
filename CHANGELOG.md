# Changelog

All notable changes to AI Publisher Pro will be documented in this file.

## [3.3.0] - 2026-02-12

### New Feature: Screenplay Studio

Transform novels and stories into professional screenplays with AI-powered video generation.

#### Highlights

- **12-Agent Pipeline**: Complete screenplay adaptation from analysis to video
- **4 Pricing Tiers**: FREE, STANDARD, PRO, DIRECTOR
- **Bilingual Support**: English + Vietnamese with cultural adaptation
- **3 Video Providers**: Pika Labs, Runway Gen-3, Google Veo 2
- **Professional Exports**: Fountain, PDF, Storyboard PDF, Video

#### Backend

- 12 AI agents for screenplay generation pipeline
- 4 video/image providers (DALL-E, Runway, Veo, Pika)
- SQLite database for project storage
- 17 API endpoints for screenplay operations
- Cost calculator with tier-based pricing

#### Frontend

- Dashboard with project list and stats
- 3-step Create Wizard (Source, Settings, Review)
- Script Editor with scene navigation
- Storyboard Viewer with shot grid
- Video Player with render progress
- Export Panel for all formats

#### Pipeline Phases

1. **Analysis** (FREE): Story analysis + scene breakdown
2. **Screenplay** (FREE): Dialogue + action writing + formatting
3. **Pre-Visualization** (STANDARD): Shot lists + storyboard images
4. **Video Rendering** (PRO): AI video generation + editing

#### Technical

- 60+ new files created
- 1,328 tests passing
- 40 API endpoint tests
- Full integration testing completed
- 9 bugs found and fixed during integration

### Fixed

- API field name mismatches between frontend/backend
- Missing progress, visualize, render endpoints
- Missing export endpoints for storyboard-pdf and video
- Unicode emoji rendering in export panel
- Next.js API proxy configuration

---

## [2.7.0] - 2024-12-21

### 🎉 Initial Public Release

#### ✨ Features
- **Smart Extraction Router**: Automatically detect document type and choose optimal extraction strategy
  - FAST_TEXT: For text-only documents (FREE, 4000x faster)
  - FULL_VISION: For scanned documents and academic papers
  - HYBRID: For mixed content documents
  
- **Academic Paper Support**: Special handling for arXiv and academic papers
  - Keyword-based detection (theorem, lemma, proof, etc.)
  - Formula preservation via Vision API
  - LaTeX table rendering

- **Multi-Provider AI**: Support for multiple AI providers
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Anthropic (Claude Sonnet)
  - DeepSeek (DeepSeek Chat)

- **Multiple Output Formats**
  - PDF (ebook style with ReportLab)
  - PDF (academic style with LaTeX)
  - DOCX (Microsoft Word)
  - Markdown

- **Usage Statistics**: Real-time tracking of
  - Token usage
  - API costs
  - Processing time
  - Calls by provider

- **Web UI**: Modern, responsive interface
  - File upload with drag & drop
  - Real-time progress tracking
  - Download in multiple formats
  - Admin panel

#### 🐛 Bug Fixes
- Fixed PDF download with partial job ID matching
- Fixed academic paper formula detection
- Fixed table rendering in LaTeX output

#### 📊 Performance
- Text-only documents: 97% faster, 97% cheaper
- 600-page novel: ~5 minutes (vs ~3 hours)
- Optimized memory usage for large documents

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 3.3.0 | 2026-02-12 | Screenplay Studio - 12-agent pipeline |
| 2.7.0 | 2024-12-21 | Initial public release |

---

## Upgrade Guide

### From scratch
```bash
git clone https://github.com/nclamvn/dich-tai-lieu.git
cd dich-tai-lieu
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn api.main:app --port 3001
```

---

## Support

- 📝 [Issues](https://github.com/nclamvn/dich-tai-lieu/issues)
- 💬 [Discussions](https://github.com/nclamvn/dich-tai-lieu/discussions)
