# Testing Guide - AI Translator Pro

## Overview

Comprehensive testing infrastructure for enterprise-grade translation system.

**Test Coverage:** 106/135 tests passing (78.5%)
**Test Framework:** pytest with async support
**Coverage Tool:** pytest-cov

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests for core modules
│   ├── test_chunker.py      # SmartChunker tests (27/30 passed)
│   ├── test_validator.py    # QualityValidator tests (28/29 passed)
│   ├── test_translation_memory.py  # TM tests (13/28 passed)
│   └── test_parallel.py     # Parallel processor tests (5/18 passed)
├── integration/             # API integration tests
│   └── test_api.py          # API endpoint tests (33/40 passed)
└── test_data/               # Test data files
```

---

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=core --cov=api --cov-report=html

# Run specific test file
pytest tests/unit/test_chunker.py

# Run specific test class
pytest tests/unit/test_chunker.py::TestSmartChunker

# Run specific test method
pytest tests/unit/test_chunker.py::TestSmartChunker::test_create_chunks_short_text
```

### Run by Category

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run tests with marker
pytest -m unit
pytest -m integration
pytest -m slow  # Slow tests
```

### Skip Tests

```bash
# Skip slow tests
pytest --ignore=tests/integration/

# Skip specific markers
pytest -m "not slow"
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Output options
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=core
    --cov=api
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=70

# Asyncio configuration
asyncio_mode = auto

# Markers
markers =
    unit: Unit tests for core modules
    integration: Integration tests for API endpoints
    slow: Slow running tests
    api_call: Tests that make real API calls (skip by default)
```

---

## Test Modules

### 1. Unit Tests

#### test_chunker.py

**Status:** ✅ 27/30 passed (90%)

Tests SmartChunker functionality:
- Text chunking with context preservation
- Sentence splitting
- Paragraph detection
- Chunk overlap
- Long text handling

**Known Issues:**
- 3 minor failures in sentence splitting edge cases

#### test_validator.py

**Status:** ✅ 28/29 passed (96.5%)

Tests QualityValidator:
- Length ratio calculation
- Completeness checking
- Vietnamese quality validation
- Domain-specific validation (finance, medical, literature, technology)
- Domain weights configuration

**Known Issues:**
- 1 assertion on exact length ratio (implementation uses ranges)

#### test_translation_memory.py

**Status:** ⚠️ 13/28 passed (46%)

Tests TranslationMemory system:
- Segment storage and retrieval
- Exact matching
- Fuzzy matching
- Similarity calculations
- Statistics and reporting

**Known Issues:**
- API signature mismatch for `get_fuzzy_matches()` (needs `max_results` param)
- Statistics keys differ from expected
- Some similarity thresholds need adjustment

#### test_parallel.py

**Status:** ⚠️ 5/18 passed (28%)

Tests ParallelProcessor:
- Async task processing
- Concurrency limiting
- Retry logic
- Timeout handling
- Statistics collection

**Known Issues:**
- Requires `pytest-asyncio` plugin
- Some async tests not properly configured

### 2. Integration Tests

#### test_api.py

**Status:** ✅ 33/40 passed (82.5%)

Tests API endpoints:
- Jobs CRUD operations
- Queue statistics
- System information
- Processor control
- OCR endpoints
- WebSocket connections

**Test Coverage:**
- ✅ POST /api/jobs
- ✅ GET /api/jobs
- ✅ GET /api/jobs/{id}
- ✅ PATCH /api/jobs/{id}
- ✅ DELETE /api/jobs/{id}
- ✅ POST /api/jobs/{id}/cancel
- ✅ GET /api/queue/stats
- ✅ GET /api/system/info
- ⚠️ OCR endpoints (requires real API keys)

---

## Fixtures

### Configuration Fixtures

```python
test_settings()        # Mock settings with test API keys
temp_dir()            # Temporary directory for test files
temp_tm_db()          # Temporary TM database
```

### Data Fixtures

```python
sample_texts()         # Sample text in multiple languages
sample_chunks()        # Pre-chunked text samples
sample_glossary_terms() # Glossary test data
```

### Component Fixtures

```python
mock_translator()      # Mocked translator
mock_validator()       # Mocked validator
real_chunker()        # Real chunker instance
real_validator()      # Real validator instance
real_glossary()       # Real glossary manager
real_tm()             # Real translation memory
```

### API Fixtures

```python
api_client()          # FastAPI test client
sample_job_payload()  # Job creation payload
mock_openai_response() # Mocked OpenAI response
mock_anthropic_response() # Mocked Anthropic response
```

---

## Coverage Report

### Current Coverage: 9% overall

**Core Modules:**
- core/chunker.py: **95%** ✅
- core/validator.py: 17%
- core/translation_memory.py: 22%
- core/parallel.py: 23%
- core/translator.py: 12%

**Uncovered Modules:**
- core/analytics.py: 0%
- core/batch_processor.py: 0%
- core/export.py: 0%
- core/job_queue.py: 0%
- core/logging_config.py: 0%
- core/error_tracker.py: 0%
- core/health_monitor.py: 0%
- api/main.py: 0%

**Target:** 70% coverage (will improve with more tests)

---

## Logging & Monitoring Tests

### Logging System

**Location:** `core/logging_config.py`

**Features:**
- ✅ Structured JSON logging
- ✅ Rotating file handlers (10MB, 5 backups)
- ✅ Colorized console output
- ✅ Context loggers
- ✅ Performance logging

**Test Manually:**
```python
from core.logging_config import app_logger, log_translation_job

app_logger.info("Test log message")
log_translation_job("job_123", "completed", duration_ms=1234.5, tokens_used=500)
```

**Log Files:**
- `logs/ai_translator.log` - Main application log
- `logs/api.json.log` - API requests (JSON)
- `logs/errors.json.log` - All errors (JSON)
- `logs/performance.json.log` - Performance metrics (JSON)

### Error Tracking

**Location:** `core/error_tracker.py`

**Features:**
- ✅ SQLite-based error tracking
- ✅ Error deduplication by hash
- ✅ Severity levels (low, medium, high, critical)
- ✅ Category classification (9 categories)
- ✅ Occurrence counting
- ✅ Resolution tracking

**Test Manually:**
```python
from core.error_tracker import track_error, ErrorSeverity, ErrorCategory

try:
    raise ValueError("Test error")
except Exception as e:
    track_error(
        e,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.VALIDATION_ERROR,
        module="test",
        job_id="job_123"
    )
```

**Database:** `data/errors/error_tracker.db`

### Health Monitoring

**Location:** `core/health_monitor.py`

**Features:**
- ✅ System resource monitoring (CPU, memory, disk)
- ✅ Database health checks
- ✅ Storage availability
- ✅ API connectivity checks
- ✅ Cost tracking metrics

**API Endpoints:**
- `GET /health` - Basic health check
- `GET /api/health/detailed` - Comprehensive health status
- `GET /api/monitoring/costs?time_period_hours=24` - Cost metrics
- `GET /api/monitoring/errors?time_period_hours=24` - Error statistics
- `GET /api/monitoring/errors/recent?limit=50` - Recent errors

**Test Manually:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/health/detailed
curl http://localhost:8000/api/monitoring/costs
curl http://localhost:8000/api/monitoring/errors
```

---

## Writing New Tests

### Unit Test Template

```python
"""
Unit tests for core/module_name.py
"""
import pytest
from core.module_name import ClassName


class TestClassName:
    """Test ClassName class."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return ClassName()

    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        result = instance.method()
        assert result is not None

    @pytest.mark.parametrize("input,expected", [
        ("test1", "result1"),
        ("test2", "result2"),
    ])
    def test_multiple_inputs(self, instance, input, expected):
        """Test with multiple inputs."""
        assert instance.method(input) == expected
```

### Integration Test Template

```python
"""
Integration tests for feature X
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app


class TestFeatureX:
    """Test feature X integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_endpoint_success(self, client):
        """Test successful endpoint call."""
        response = client.get("/api/feature")
        assert response.status_code == 200
        data = response.json()
        assert "key" in data
```

---

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure project root is in path
export PYTHONPATH="${PYTHONPATH}:/Users/mac/translator_project"
```

**2. Async Tests Failing**
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure asyncio_mode is set in pytest.ini
asyncio_mode = auto
```

**3. Coverage Not Working**
```bash
# Install pytest-cov
pip install pytest-cov

# Run with coverage
pytest --cov=core --cov=api
```

**4. Database Locked Errors**
```bash
# Delete test databases
rm -rf data/test_*
rm -rf /tmp/test_*.db
```

**5. Missing Dependencies**
```bash
# Install all test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=core --cov=api --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Next Steps

### Priority 1 (High Impact)
- [ ] Fix async test configuration (add pytest-asyncio)
- [ ] Fix TranslationMemory API signature mismatches
- [ ] Add tests for translator.py main class

### Priority 2 (Medium Impact)
- [ ] Increase coverage for validator.py (17% → 70%)
- [ ] Add integration tests for WebSocket connections
- [ ] Test OCR endpoints with mock data

### Priority 3 (Nice to Have)
- [ ] Add performance benchmarking tests
- [ ] Test batch processor edge cases
- [ ] Add load testing for API endpoints

---

## Test Maintenance

### Regular Tasks

**Daily:**
- Run full test suite before commits
- Check test failures in CI/CD

**Weekly:**
- Review coverage reports
- Update failing tests for API changes
- Clean up old test databases

**Monthly:**
- Update test fixtures with new sample data
- Review and update test documentation
- Refactor duplicate test code

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Last Updated:** 2025-11-13
**Test Framework Version:** pytest 9.0.1
**Python Version:** 3.13.5
