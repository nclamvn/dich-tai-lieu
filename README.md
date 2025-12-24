# AI Translator Pro - Professional Translation System

🚀 Hệ thống dịch thuật tự động chuyên nghiệp với AI

## ✨ Tính Năng

### Phase 1 - Core Integration (✅ COMPLETED)
- ✅ **Modular Architecture**: Codebase được tổ chức theo modules chuyên biệt
- ✅ **Smart Chunking**: Tách văn bản thông minh với context preservation
- ✅ **Translation Cache**: Tránh dịch lại nội dung trùng lặp (tiết kiệm 30-50% chi phí)
- ✅ **Quality Validation**: Đánh giá chất lượng bản dịch tự động
- ✅ **Glossary Management**: Quản lý thuật ngữ chuyên ngành
- ✅ **Smart Merging**: Ghép chunks thông minh với overlap detection
- ✅ **Professional Export**: Export sang nhiều định dạng (DOCX, PDF, HTML, MD)

### Phase 2 - Quality & Performance (✅ COMPLETED)
- ✅ **Domain-Specific Glossaries**: 4 glossaries chuyên ngành (Finance, Literature, Medical, Technology)
  - 75-175 terms per domain
  - Auto-detection of domain from glossary
  - Customizable validation weights per domain
- ✅ **Enhanced Quality Validator**: Domain-aware validation với rules tùy chỉnh
  - Finance: Numeric format, currency symbols, financial abbreviations
  - Literature: Dialogue formatting, paragraph structure, narrative tense
  - Medical: Dosage preservation (critical!), medical abbreviations, safety warnings
  - Technology: Code blocks, inline code, technical abbreviations, identifier preservation
  - General: Punctuation consistency, capitalization preservation
  - Detailed domain_scores for analytics
- ✅ **Parallel Processing**: Xử lý đồng thời nhiều chunks
  - Semaphore-based rate limiting
  - Automatic retry with exponential backoff
  - Progress tracking with tqdm
  - Batch processing for large projects
  - Task-level statistics and error reporting
  - Full async/await implementation
- ✅ **Performance Analytics**: Comprehensive metrics và reporting
  - Translation session tracking
  - Quality distribution analysis
  - Performance metrics (throughput, speed)
  - Cache effectiveness tracking
  - Cost estimation (tokens + USD)
  - Session history và reports (TXT, CSV, JSON)
  - Domain-specific analytics
  - Summary reports across multiple sessions

### Phase 3 - Translation Memory (✅ COMPLETED)
- ✅ **SQLite TM Database**: File-based, local, không cần cloud
  - FTS5 full-text search
  - Automatic indexing
  - Context preservation
  - Quality tracking
- ✅ **Fuzzy Matching Algorithms**: Multi-method similarity
  - Levenshtein distance (edit distance)
  - Character bigram similarity
  - Word overlap matching
  - Weighted combination (85% threshold mặc định)
- ✅ **TMX Import/Export**: Industry-standard format
  - Import from CAT tools (SDL Trados, memoQ, etc.)
  - Export by domain or all domains
  - Preserve metadata (quality, domain, dates)
- ✅ **TM Statistics & Reporting**: Comprehensive analytics
  - Usage statistics và reuse rate
  - Quality distribution
  - Most used segments
  - Domain breakdown
  - Cost savings estimation
- ✅ **Engine Integration**: Seamless workflow
  - Auto-check TM before API calls
  - Auto-save new translations to TM
  - Exact match (100%) → instant return
  - Fuzzy match (≥85%) → reuse with confidence
  - Track TM hits/misses

### Phase 4 - Multi-language Support (✅ COMPLETED)
- ✅ **Language Configuration System**: 10 languages supported
  - English (en), Vietnamese (vi)
  - Chinese Simplified (zh-Hans), Chinese Traditional (zh-Hant)
  - Japanese (ja), Korean (ko)
  - French (fr), Spanish (es), German (de)
  - Language pair configuration (bidirectional support)
  - Configurable via settings.py (SOURCE_LANG, TARGET_LANG)
- ✅ **Language Detection**: Rule-based detection
  - Unicode character range matching
  - Confidence scoring
  - Candidate filtering
- ✅ **Language-Specific Validation**: Custom rules per language
  - Vietnamese: Diacritics check, common words validation
  - Chinese: Character detection, spacing validation, character ratio
  - English: Word validation, common words check
  - Generic validation for other languages
- ✅ **Language Characteristics Modeling**:
  - Expected length ratios per language (e.g., Vietnamese 1.3x, Chinese 0.7x)
  - Diacritics requirements
  - Spacing patterns
  - Capitalization rules
- ✅ **Language-Agnostic Architecture**:
  - Dynamic prompts adapt to source/target pair
  - Validation weights adjust per language
  - TM supports all language pairs
  - Quality metrics language-aware

### Phase 5 - Batch Processing (✅ COMPLETED)
- ✅ **Job Queue System**: SQLite-based queue (no Redis/Celery needed)
  - TranslationJob model with full metadata
  - Job status tracking (pending, queued, running, completed, failed, etc.)
  - Job persistence across restarts
  - CRUD operations for job management
- ✅ **Priority Scheduling**: Fair resource allocation
  - 5 priority levels (LOW, NORMAL, HIGH, URGENT, CRITICAL)
  - Priority-based job ordering
  - FIFO within same priority
  - Scheduled jobs support (run at specific time)
- ✅ **Batch Processor**: Automated job execution
  - Concurrent job processing (configurable)
  - Automatic retry on failures (max 3 retries)
  - Real-time progress tracking
  - Quality metrics and cost estimation
  - Multiple output formats support (TXT, DOCX, PDF, HTML, MD)
- ✅ **Job Scheduler**: Time-based job execution
  - Schedule jobs for future execution
  - Automatic job queuing at scheduled time
  - Continuous monitoring
- ✅ **CLI Interface**: Comprehensive job management
  - Create jobs with full configuration
  - List/filter jobs by status
  - Check detailed job status
  - Cancel/delete jobs
  - Process queue (start worker)
  - Queue statistics and monitoring
  - Old job cleanup
- ✅ **Fault Tolerance & Recovery**:
  - Jobs persist in database
  - Automatic retry on transient errors
  - Error tracking and reporting
  - Failed chunk tracking
  - Resume capability

### Phase 6 - Web UI/Dashboard (✅ COMPLETED)
- ✅ **FastAPI Backend**: Modern REST API
  - Full RESTful endpoints for job management (CRUD)
  - Queue statistics and monitoring APIs
  - System information endpoints
  - Processor control (start/stop)
  - Health check endpoint
  - Auto-generated API documentation (Swagger/OpenAPI)
- ✅ **WebSocket Support**: Real-time updates
  - Live job status updates
  - Queue statistics streaming
  - System event broadcasting
  - Connection management
  - Auto-reconnect on disconnect
- ✅ **Modern Dashboard**: Single-page web interface
  - Real-time queue statistics
  - Job list with filtering
  - Progress bars and status indicators
  - Job creation form
  - Processor control panel
  - Toast notifications
  - Responsive design
- ✅ **API Features**:
  - CORS enabled for development
  - Pydantic models for validation
  - Background task processing
  - Error handling and HTTP exceptions
  - RESTful conventions

### Phase 7 - Product Capabilities Upgrade (✅ COMPLETED - v3.0.0)
- ✅ **Advanced Layout Preservation**: Multi-column detection and smart reading order
  - X-coordinate clustering for column detection
  - Column-aware reading order (left-to-right, top-to-bottom per column)
  - Block type classification (title, heading, caption, table, header, footer)
  - Font analysis (size, bold, family) for semantic understanding
  - Enhanced TextBlock with column_index, is_bold, confidence
- ✅ **Two Output Modes**: Preserve layout PDF or reflow DOCX
  - **Preserve Layout Mode**: Maintains original PDF layout, positioning, fonts
  - **Reflow DOCX Mode**: Creates structured, editable DOCX with semantic formatting
  - Auto-scaling fonts for overflow prevention
  - Block-type aware formatting for professional output
- ✅ **OCR Pipeline**: Full support for scanned/handwritten documents
  - Abstract OcrClient interface for pluggable implementations
  - DeepSeek OCR client with retry logic and exponential backoff
  - PDF-to-image conversion at configurable DPI (150-600)
  - Per-page OCR processing with progress tracking and error recovery
  - Structured output (text, confidence, blocks, metadata)
  - Two modes: document (printed) and handwriting
  - See [OCR_MODE.md](docs/OCR_MODE.md) for full guide
- ✅ **STEM Extras**: Chemical formulas and improved code detection
  - **Chemical Formula Detection**: SMILES patterns (CH3CH2OH, H2SO4, C6H12O6)
  - Conservative heuristics to avoid false positives
  - Configurable enable/disable (off by default)
  - **Improved Inline Code Detection**: Symbol density, function calls, arrow functions
  - Pattern matching for CamelCase, snake_case, dot notation
  - False positive avoidance for common abbreviations (e.g., i.e., etc.)
- ✅ **Quality Checker**: Translation quality validation
  - Length ratio checks (configurable thresholds)
  - Placeholder consistency validation (⟪STEM_*⟫ preservation)
  - STEM preservation verification (detect unprotected formulas/code)
  - Comprehensive QualityReport with warnings and pass/fail status
  - Lightweight, non-blocking integration
  - See [docs/PHASE3_SUMMARY.md](docs/PHASE3_SUMMARY.md) for details

## 📁 Cấu Trúc Dự Án

```
translator_project/
├── api/                       # Web API (Phase 6)
│   ├── main.py               # FastAPI application
│   └── dashboard.html        # Web dashboard
│
├── core/                      # Core translation engine
│   ├── chunker.py            # Smart text chunking
│   ├── cache.py              # Translation cache
│   ├── validator.py          # Quality validation
│   ├── glossary.py           # Glossary management
│   ├── merger.py             # Smart merging
│   ├── translator.py         # Main translator
│   ├── translation_memory.py # Translation Memory (TM)
│   ├── tmx_handler.py        # TMX import/export
│   ├── language.py           # Language support & detection
│   ├── parallel.py           # Parallel processing
│   ├── analytics.py          # Performance analytics
│   ├── job_queue.py          # Job queue system (Phase 5)
│   ├── batch_processor.py    # Batch processor (Phase 5)
│   ├── export.py             # Document export
│   ├── stem/                 # STEM translation (Phase 7)
│   │   ├── code_detector.py      # Code block detection
│   │   ├── formula_detector.py   # Formula & chemical detection
│   │   ├── layout_extractor.py   # Multi-column layout extraction
│   │   ├── pdf_reconstructor.py  # PDF/DOCX output modes
│   │   ├── placeholder_manager.py# STEM content placeholders
│   │   └── stem_translator.py    # STEM-aware translation
│   ├── ocr/                  # OCR for scanned docs (Phase 7)
│   │   ├── base.py               # OcrClient interface
│   │   ├── deepseek_client.py    # DeepSeek OCR implementation
│   │   └── pipeline.py           # OCR processing pipeline
│   ├── quality/              # Quality validation (Phase 7)
│   │   └── quality_checker.py    # Translation quality checks
│   └── performance/          # Performance optimization
│       ├── adaptive_concurrency.py  # Adaptive rate limiting
│       ├── checkpoint_manager.py    # Translation checkpointing
│       ├── smart_scheduler.py       # Smart chunk scheduling
│       └── streaming_translator.py  # Streaming translation
│
├── config/                    # Configuration
│   └── settings.py           # Settings management
│
├── scripts/                   # Utility scripts
│   ├── job_cli.py            # Job management CLI (Phase 5)
│   ├── demo_batch.py         # Batch processing demo
│   └── demo_phase2.py        # Phase 2 demo
│
├── glossary/                  # Domain glossaries
│   ├── default.json          # Default terms
│   ├── finance.json          # Finance domain
│   ├── literature.json       # Literature domain
│   ├── medical.json          # Medical domain
│   └── technology.json       # Technology domain
│
├── data/                      # Data directories
│   ├── input/                # Input files
│   ├── output/               # Translated files
│   ├── cache/                # Translation cache
│   ├── logs/                 # Quality reports
│   ├── analytics/            # Analytics reports
│   ├── translation_memory/   # TM database
│   └── jobs.db               # Job queue database (Phase 5)
│
├── legacy/                    # Old scripts (archived)
├── start_server.sh           # Web server startup script (Phase 6)
├── .env                      # Environment variables
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env template
cp .env.example .env

# Edit .env với API key của bạn
# OPENAI_API_KEY=sk-...
```

### 2. Configuration

Edit `.env` file:

```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here

# Translation Config
PROVIDER=openai
MODEL=gpt-4o-mini
QUALITY_MODE=balanced
CONCURRENCY=4

# Languages (Phase 4)
SOURCE_LANG=en
TARGET_LANG=vi

# Feature Flags
CACHE_ENABLED=true
QUALITY_VALIDATION=true
GLOSSARY_ENABLED=true
TM_ENABLED=true
TM_FUZZY_THRESHOLD=0.85
```

### 3. Usage (Phase 1)

```python
import asyncio
from pathlib import Path
from config.settings import settings
from core.chunker import SmartChunker
from core.cache import TranslationCache
from core.validator import QualityValidator
from core.glossary import GlossaryManager
from core.translator import TranslatorEngine
from core.merger import SmartMerger

async def translate_document(input_text: str) -> str:
    # Initialize components
    model_config = settings.get_model_config()

    chunker = SmartChunker(
        max_chars=model_config['max_chars'],
        context_window=model_config['context_window']
    )
    cache = TranslationCache(settings.cache_dir, settings.cache_enabled)
    glossary = GlossaryManager(settings.glossary_dir, settings.glossary_name)
    validator = QualityValidator()

    translator = TranslatorEngine(
        provider=settings.provider,
        model=model_config['model'],
        api_key=settings.get_api_key(),
        glossary_mgr=glossary,
        cache=cache,
        validator=validator
    )

    # Create chunks
    chunks = chunker.create_chunks(input_text)
    print(f"Created {len(chunks)} chunks")

    # Translate
    import httpx
    async with httpx.AsyncClient() as client:
        results = []
        for chunk in chunks:
            result = await translator.translate_chunk(client, chunk)
            results.append(result)
            print(f"Chunk {chunk.id}: quality {result.quality_score:.2f}")

    # Merge
    merger = SmartMerger()
    final_text = merger.merge_translations(results)

    # Save cache
    cache.save()

    return final_text

# Run
text = Path("data/input/document.txt").read_text()
result = asyncio.run(translate_document(text))
Path("data/output/translated.txt").write_text(result)
```

## 📊 Quality Metrics

### Base Metrics
- **Length Ratio Check**: EN→VI should be 1.2-1.4x
- **Completeness Check**: Không bỏ sót câu
- **Vietnamese Quality**: Kiểm tra dấu thanh, artifacts
- **Glossary Compliance**: Đúng thuật ngữ chuyên ngành
- **Punctuation Consistency**: Bảo toàn dấu câu quan trọng
- **Capitalization**: Giữ nguyên proper nouns và acronyms

### Domain-Specific Validation

**Finance Domain:**
- Numeric format preservation (percentages, decimals)
- Currency symbol integrity ($, €, £, ¥, ₫)
- Financial abbreviations (P/E, IPO, CEO, CFO, ETF)

**Literature Domain:**
- Dialogue formatting (quotation marks)
- Paragraph structure preservation
- Narrative tense consistency (temporal markers)

**Medical Domain:**
- ⚠️ **CRITICAL**: Dosage information preservation
- Medical abbreviations (ICU, MRI, CT, X-ray)
- Safety-critical term warnings (contraindication, toxic, fatal)

**Technology Domain:**
- Code block preservation (```)
- Inline code formatting (`)
- Technical abbreviations (API, SQL, HTTP, JSON)
- Code identifier preservation (camelCase, snake_case)

### Validation Weights by Domain
- Each domain has customized weights for different metrics
- Medical domain emphasizes glossary compliance (30%) for safety
- Literature domain emphasizes completeness (30%) and Vietnamese quality (30%)
- All domains include domain-specific validation scores

## 📤 Export Formats

Hệ thống hỗ trợ export sang nhiều định dạng chuyên nghiệp:

### DOCX (Word)
- ✅ Custom styles và formatting
- ✅ Headers/footers với page numbers
- ✅ Table of contents (TOC)
- ✅ Watermarks
- ✅ Structured content (headings, lists, quotes, code blocks)

### PDF
- ✅ Professional layout với ReportLab
- ✅ Custom fonts và colors
- ✅ Headers/footers
- ✅ Page numbering
- ✅ Compression options

### HTML
- ✅ Web-ready với embedded CSS
- ✅ Responsive design
- ✅ Syntax highlighting cho code blocks
- ✅ Clean, semantic markup

### Markdown
- ✅ GitHub-flavored markdown
- ✅ Perfect cho documentation
- ✅ Preserve code blocks và lists

### TXT
- ✅ Plain text với UTF-8 encoding
- ✅ Universal compatibility

### Demo Export
```bash
# Run demo to test all export formats
python scripts/demo_export.py
```

### Demo Phase 2 Features
```bash
# Run comprehensive Phase 2 demo (all domains + analytics)
python scripts/demo_phase2.py
```

This demo showcases:
- Translation across 4 domains (Finance, Literature, Medical, Technology)
- Domain-specific validation
- Parallel processing with progress tracking
- Real-time analytics and cost estimation
- Session reports and summaries

### Demo Phase 5 - Batch Processing
```bash
# Run batch processing demo
python scripts/demo_batch.py
```

This demo showcases:
- Job creation with different priorities (LOW, NORMAL, URGENT)
- Queue management and statistics
- Priority-based scheduling
- Job status tracking
- CLI usage examples

### Phase 5 CLI Usage

**Create a translation job:**
```bash
python scripts/job_cli.py create \
    --input data/input/document.txt \
    --output data/output/translated.docx \
    --priority urgent \
    --domain technology \
    --format docx
```

**List all jobs:**
```bash
python scripts/job_cli.py list --stats
```

**Check job status:**
```bash
python scripts/job_cli.py status <job_id>
```

**Start processing queue:**
```bash
python scripts/job_cli.py process
```

**View queue statistics:**
```bash
python scripts/job_cli.py stats
```

**Cancel or delete jobs:**
```bash
python scripts/job_cli.py cancel <job_id>
python scripts/job_cli.py delete <job_id>
```

**Cleanup old jobs:**
```bash
python scripts/job_cli.py cleanup --days 30
```

### Phase 6 - Web Dashboard Usage

**Start the web server:**
```bash
# Quick start (automatic setup)
./start_server.sh

# Or manually
cd api && python3 main.py
```

**Access the dashboard:**
```
🎨 Dashboard:        http://localhost:8000/
📖 API Docs:         http://localhost:8000/docs
📊 Health Check:     http://localhost:8000/health
```

**API Endpoints:**

- `GET  /api/jobs` - List all jobs
- `POST /api/jobs` - Create new job
- `GET  /api/jobs/{job_id}` - Get job details
- `PATCH /api/jobs/{job_id}` - Update job
- `DELETE /api/jobs/{job_id}` - Delete job
- `POST /api/jobs/{job_id}/cancel` - Cancel job
- `GET  /api/queue/stats` - Queue statistics
- `GET  /api/system/info` - System information
- `POST /api/processor/start` - Start batch processor
- `POST /api/processor/stop` - Stop batch processor
- `WS   /ws` - WebSocket for real-time updates

**Example API Usage (curl):**

```bash
# Get queue statistics
curl http://localhost:8000/api/queue/stats

# Create a job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test Translation",
    "input_file": "data/input/test.txt",
    "output_file": "data/output/test_vi.txt",
    "priority": 10
  }'

# Start processor
curl -X POST http://localhost:8000/api/processor/start
```

**WebSocket Example (JavaScript):**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

## 🎯 Roadmap

### Phase 1: Core Integration ✅
- Modular architecture
- Core translation features
- Quality validation
- Professional export formats

### Phase 2: Quality & Performance ✅
- Domain-specific glossaries (4 domains)
- Enhanced quality validator với domain rules
- Parallel processing service
- Performance analytics và reporting

### Phase 3: Translation Memory ✅
- SQLite TM database với FTS5
- Fuzzy matching (Levenshtein + bigrams + word overlap)
- TMX import/export
- TM statistics và reporting
- Engine integration

### Phase 4: Multi-language ✅
- 10 languages supported (EN, VI, ZH, JA, KO, FR, ES, DE)
- Language pair configuration
- Language detection
- Language-specific validation
- Language-agnostic architecture

### Phase 5: Batch Processing ✅
- SQLite-based job queue (no Redis/Celery needed)
- Priority scheduling (5 levels)
- Batch processor with retry logic
- Job scheduler for time-based execution
- CLI interface for job management
- Fault tolerance and recovery

### Phase 6: Web UI/Dashboard ✅
- FastAPI REST API
- WebSocket real-time updates
- Modern web dashboard
- Processor control interface
- Full API documentation

## 📝 Legacy System

Old scripts đã được move vào `legacy/` folder:
- `translate_all.py` - Altman biography translator
- `translate_little_book.py` - Investment book translator
- `translate_the_secret.py` - Dan Brown novel translator

Các script này vẫn hoạt động và được giữ lại để tham khảo.

## 🙏 Credits

Built with:
- OpenAI GPT-4
- Anthropic Claude
- Python 3.x
- Pydantic
- httpx

---

**Version**: 3.0.0 (Phase 6 - Complete)
**Status**: ✅ All 6 Phases Complete - Production Ready! 🎉
**Achievements**: Full-featured professional translation system with web dashboard
