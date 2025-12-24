# Developer Guide - AI Translator Pro

This guide covers architecture, code organization, and development practices for the AI Translator Pro project.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Modules](#core-modules)
3. [API Layer](#api-layer)
4. [Code Conventions](#code-conventions)
5. [Testing](#testing)
6. [Common Tasks](#common-tasks)

---

## Architecture Overview

```
translator_project/
├── api/                    # FastAPI REST API
│   ├── main.py            # Main API server
│   ├── routes/            # Route modules
│   └── security.py        # Session management
├── core/                   # Core translation engine
│   ├── translator.py      # TranslatorEngine class
│   ├── chunker.py         # SmartChunker (text splitting)
│   ├── validator.py       # QualityValidator
│   ├── batch_processor.py # Job processing
│   ├── batch/             # Batch processing sub-modules
│   ├── cache/             # Caching (chunk cache, TM)
│   ├── export/            # DOCX/PDF export
│   ├── stem/              # STEM content handling
│   └── ocr/               # OCR integration
├── config/                # Configuration
│   ├── settings.py        # Global settings
│   └── logging_config.py  # Logging setup
├── ui/                    # Frontend (HTML/JS)
├── data/                  # Runtime data
│   ├── cache/             # Translation cache DB
│   ├── output/            # Generated files
│   └── uploads/           # Uploaded files
└── tests/                 # Test suite
```

### Data Flow

```
User Upload → API → BatchProcessor → TranslatorEngine → Export → Download
                         │
                         ├── SmartChunker (split text)
                         ├── QualityValidator (validate)
                         └── ChunkCache (cache results)
```

---

## Core Modules

### TranslatorEngine (`core/translator.py`)

Main translation engine with multi-provider LLM support.

```python
from core.translator import TranslatorEngine

engine = TranslatorEngine(
    provider="openai",       # or "anthropic"
    model="gpt-4o-mini",
    api_key="sk-...",
    source_lang="en",
    target_lang="vi"
)

# Single chunk translation
async with httpx.AsyncClient() as client:
    result = await engine.translate_chunk(client, chunk)

# Parallel translation
results, stats = await engine.translate_parallel(chunks, max_concurrency=10)
```

**Key Features:**
- Translation Memory (TM) for reuse
- Multi-level caching (chunk cache + legacy)
- Quality validation with auto-retry
- Glossary integration

### SmartChunker (`core/chunker.py`)

Intelligent text chunking with context preservation.

```python
from core.chunker import SmartChunker

# Standard chunking
chunker = SmartChunker(max_chars=2000, context_window=200)
chunks = chunker.create_chunks(document_text)

# STEM-aware chunking (preserves formulas/code)
stem_chunker = SmartChunker(max_chars=2000, context_window=200, stem_mode=True)
chunks = stem_chunker.create_chunks(latex_document)
```

**Features:**
- Paragraph/sentence boundary detection
- Context preservation between chunks
- STEM content protection (formulas, code blocks)
- Multi-language support (Latin, CJK)

### QualityValidator (`core/validator.py`)

Translation quality assessment with domain-specific rules.

```python
from core.validator import QualityValidator

result = QualityValidator.validate(
    source="The API returns JSON data",
    translated="API trả về dữ liệu JSON",
    domain="technology"
)

print(f"Quality: {result.quality_score:.2f}")
print(f"Warnings: {result.warnings}")
```

**Supported Domains:**
- `finance` - Preserves numbers, currencies, abbreviations
- `medical` - Validates dosage info (safety-critical)
- `literature` - Checks dialogue formatting, structure
- `technology` - Preserves code blocks, tech terms
- `default` - General-purpose validation

### Batch Processing (`core/batch/`)

Job lifecycle and parallel chunk processing.

```python
from core.batch import (
    JobHandler,
    ChunkProcessor,
    ResultAggregator,
    ProgressTracker
)

# Progress tracking
tracker = ProgressTracker(total_chunks=100, job_id="job_123")
tracker.add_callback(websocket_callback)
tracker.start_phase("translating", total_steps=100)
tracker.update(50, "Chunk 50/100", quality=0.95)
```

**Sub-modules:**
- `job_handler.py` - JobState, JobResult, lifecycle management
- `chunk_processor.py` - Parallel chunk processing
- `result_aggregator.py` - Merge results, STEM restoration
- `progress_tracker.py` - Real-time progress callbacks

### Export (`core/export/`)

Document export with multiple formats.

```python
from core.export import BasicDocxExporter, AcademicDocxExporter

# Basic export
exporter = BasicDocxExporter()
output_path = exporter.export(content, "output.docx")

# Academic export (with theorem blocks, proofs)
academic = AcademicDocxExporter()
output_path = academic.export(content, "thesis.docx")
```

**Exporter Classes:**
- `BasicDocxExporter` - Standard DOCX output
- `AcademicDocxExporter` - Semantic structure for papers
- `PresentationDocxExporter` - Slide-style layout

---

## API Layer

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs` | Create translation job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Get job details |
| POST | `/api/jobs/{id}/cancel` | Cancel job |
| GET | `/api/jobs/{id}/download/{fmt}` | Download output |
| POST | `/api/upload` | Upload file |
| POST | `/api/analyze` | Analyze file |
| GET | `/api/queue/stats` | Queue statistics |
| WS | `/ws` | Real-time updates |

### Creating a Job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "My Translation",
    "input_file": "/path/to/document.pdf",
    "output_file": "/path/to/output.docx",
    "source_lang": "en",
    "target_lang": "vi",
    "domain": "stem"
  }'
```

### WebSocket Events

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.event) {
    case "job_progress":
      console.log(`Progress: ${data.progress * 100}%`);
      break;
    case "job_completed":
      console.log(`Job ${data.job_id} finished`);
      break;
  }
};
```

---

## Code Conventions

### Docstrings (Google Style)

```python
def translate_chunk(
    self,
    client: httpx.AsyncClient,
    chunk: TranslationChunk
) -> TranslationResult:
    """
    Translate a single chunk with caching and validation.

    Args:
        client: httpx.AsyncClient for API calls.
        chunk: TranslationChunk containing text to translate.

    Returns:
        TranslationResult with translated text and quality score.

    Raises:
        ValueError: If provider is not supported.

    Note:
        Low quality translations (score < 0.5) trigger retry.
    """
```

### Logging

```python
from config.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Processing job", extra={"job_id": job_id})
logger.warning("Low quality translation", extra={"score": 0.4})
logger.error("API call failed", exc_info=True)
```

### Type Hints

```python
from typing import Optional, List, Dict, Any

def process_chunks(
    chunks: List[TranslationChunk],
    *,
    max_concurrency: int = 10,
    callback: Optional[Callable[[int, int], None]] = None
) -> tuple[List[TranslationResult], ProcessingStats]:
    ...
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_translator.py

# With coverage
pytest --cov=core --cov-api
```

### Test Structure

```
tests/
├── test_translator.py     # TranslatorEngine tests
├── test_chunker.py        # SmartChunker tests
├── test_validator.py      # QualityValidator tests
├── test_api.py            # API endpoint tests
└── fixtures/              # Test data files
```

### Writing Tests

```python
import pytest
from core.validator import QualityValidator

def test_finance_domain_validation():
    """Test finance domain preserves currency symbols."""
    result = QualityValidator.validate(
        source="Revenue was $50M in Q1",
        translated="Doanh thu là $50M trong Q1",
        domain="finance"
    )

    assert result.quality_score >= 0.8
    assert "currency" not in " ".join(result.warnings).lower()
```

---

## Common Tasks

### Adding a New Domain Validator

1. Add weights in `QualityValidator.DOMAIN_WEIGHTS`:

```python
DOMAIN_WEIGHTS = {
    'legal': {
        'length': 0.15,
        'completeness': 0.30,
        'vietnamese': 0.20,
        'glossary': 0.30,
        'domain_specific': 0.05
    },
    ...
}
```

2. Create validation method:

```python
@staticmethod
def validate_legal_domain(source: str, translated: str) -> tuple[float, List[str]]:
    """Validate legal domain translation requirements."""
    score = 1.0
    warnings = []

    # Check legal term preservation
    legal_terms = ['plaintiff', 'defendant', 'jurisdiction']
    for term in legal_terms:
        if term in source.lower() and term not in translated.lower():
            score -= 0.1
            warnings.append(f"Legal term '{term}' may need review")

    return max(0.0, score), warnings
```

3. Add case in `validate()` method:

```python
elif domain == 'legal':
    domain_score, domain_warnings = cls.validate_legal_domain(source, translated)
```

### Adding a New Export Format

1. Create exporter class extending `DocxExporterBase`:

```python
from core.export.docx_base import DocxExporterBase

class LegalDocxExporter(DocxExporterBase):
    """DOCX exporter for legal documents."""

    def _add_content(self, content: Any) -> None:
        # Add header with document ID
        self._add_header(f"Legal Document - {content.doc_id}")

        # Add content with legal formatting
        for section in content.sections:
            self._add_section(section)
```

2. Register in `core/export/__init__.py`:

```python
from .docx_legal import LegalDocxExporter

__all__ = [
    ...
    'LegalDocxExporter',
]
```

### Adding API Endpoints

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/custom", tags=["custom"])

@router.get("/stats")
async def get_custom_stats():
    """
    Get custom statistics.

    Returns:
        Dict with custom metrics.
    """
    return {"metric": 42}

# Include in main.py
app.include_router(router)
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key (required) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (optional) |
| `RATE_LIMIT` | `60/minute` | API rate limit |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max upload size |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/translator_project"
```

**Cache issues:**
```bash
# Clear translation cache
curl -X POST http://localhost:8000/api/cache/clear
```

**Low quality translations:**
- Check glossary terms are defined
- Verify domain is correctly set
- Review chunk size (smaller = better for complex text)

---

## Contributing

1. Follow Google-style docstrings
2. Add tests for new features
3. Run `pytest` before committing
4. Use type hints consistently
