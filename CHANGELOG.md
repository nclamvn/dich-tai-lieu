# 📋 Changelog

All notable changes to AI Publisher Pro will be documented in this file.

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
