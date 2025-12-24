"""
Pytest configuration and shared fixtures for AI Translator Pro tests.
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.translator import TranslatorEngine
from core.validator import QualityValidator
from core.chunker import SmartChunker
from core.translation_memory import TranslationMemory
from core.glossary import GlossaryManager
from config.settings import Settings


# ============================================================================
# Fixtures: Configuration & Settings
# ============================================================================

@pytest.fixture(scope="session")
def test_settings():
    """Test settings with mock API keys."""
    return Settings(
        OPENAI_API_KEY="test_openai_key",
        ANTHROPIC_API_KEY="test_anthropic_key",
        DEEPSEEK_API_KEY="test_deepseek_key",
        TRANSLATION_PROVIDER="openai",
        MODEL_NAME="gpt-4o-mini",
        ENABLE_CACHE=True,
        ENABLE_VALIDATION=True,
        ENABLE_GLOSSARY=True,
        ENABLE_TM=False,  # Disable TM for faster tests
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_tm_db(temp_dir: Path) -> Path:
    """Create a temporary translation memory database."""
    db_path = temp_dir / "test_tm.db"
    return db_path


# ============================================================================
# Fixtures: Sample Data
# ============================================================================

@pytest.fixture
def sample_texts():
    """Sample texts for testing translation."""
    return {
        "short_en": "Hello, world! This is a test.",
        "short_vi": "Xin chào thế giới! Đây là một bài kiểm tra.",
        "medium_en": (
            "Artificial intelligence is transforming the way we live and work. "
            "From healthcare to finance, AI is being applied across industries. "
            "Machine learning algorithms can now analyze vast amounts of data "
            "and make predictions with remarkable accuracy."
        ),
        "long_en": (
            "The global economy is experiencing unprecedented changes. "
            "Technology companies are leading the charge in innovation. "
            "Cloud computing, artificial intelligence, and blockchain are "
            "reshaping traditional business models. Companies must adapt "
            "quickly to remain competitive in this digital age. "
            "The future belongs to those who embrace change and invest "
            "in new technologies. Digital transformation is no longer optional."
        ) * 3,  # Make it longer for chunking tests
        "financial": (
            "The company reported quarterly earnings of $2.5 billion, "
            "representing a 15% increase year-over-year. Revenue grew "
            "across all segments, with particularly strong performance "
            "in the technology division."
        ),
        "medical": (
            "The patient presented with symptoms of acute myocardial infarction. "
            "ECG showed ST-segment elevation in leads V1-V4. "
            "Immediate percutaneous coronary intervention was performed."
        ),
    }


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing merging and parallel processing."""
    return [
        "This is the first chunk of text.",
        "This is the second chunk that follows.",
        "And here is the third chunk.",
        "Finally, this is the fourth chunk.",
    ]


@pytest.fixture
def sample_glossary_terms():
    """Sample glossary terms for testing."""
    return {
        "AI": "Artificial Intelligence",
        "ML": "Machine Learning",
        "API": "Application Programming Interface",
        "cloud computing": "điện toán đám mây",
        "revenue": "doanh thu",
    }


# ============================================================================
# Fixtures: Core Components (Mocked)
# ============================================================================

@pytest.fixture
def mock_translator(test_settings):
    """Create a mock translator with predefined responses."""
    translator = Mock(spec=TranslatorEngine)
    translator.settings = test_settings

    # Mock translate method
    async def mock_translate(text: str, target_lang: str, **kwargs):
        return f"[TRANSLATED to {target_lang}]: {text[:50]}..."

    translator.translate = AsyncMock(side_effect=mock_translate)
    translator.provider = "openai"
    translator.model = "gpt-4o-mini"

    return translator


@pytest.fixture
def mock_validator():
    """Create a mock validator."""
    validator = Mock(spec=QualityValidator)

    def mock_validate(original: str, translated: str, **kwargs):
        return {
            "is_valid": True,
            "score": 0.85,
            "issues": [],
            "metrics": {
                "length_ratio": 1.0,
                "completeness": 1.0,
                "quality": 0.85,
            },
        }

    validator.validate = Mock(side_effect=mock_validate)
    return validator


@pytest.fixture
def real_chunker(test_settings):
    """Create a real chunker instance for testing."""
    return SmartChunker(
        max_chars=1000,
        context_window=100,
    )


@pytest.fixture
def real_validator():
    """Create a real validator instance for testing."""
    return QualityValidator()


@pytest.fixture
def real_glossary():
    """Create a real glossary manager for testing."""
    return GlossaryManager()


@pytest.fixture
def real_tm(temp_tm_db: Path):
    """Create a real translation memory instance for testing."""
    tm = TranslationMemory(db_path=str(temp_tm_db))
    yield tm
    # Cleanup
    if temp_tm_db.exists():
        temp_tm_db.unlink()


# ============================================================================
# Fixtures: API Testing
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Translated text here"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80
        }
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Translated text here"}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 50,
            "output_tokens": 30
        }
    }


# ============================================================================
# Fixtures: FastAPI Testing
# ============================================================================

@pytest.fixture
def api_client():
    """Create a test client for the FastAPI application."""
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)


@pytest.fixture
def sample_job_payload():
    """Sample job creation payload for API testing."""
    return {
        "text": "This is a test document for translation.",
        "source_lang": "en",
        "target_lang": "vi",
        "domain": "general",
        "priority": 3,
        "options": {
            "enable_validation": True,
            "enable_glossary": True,
            "quality_mode": "balanced",
        }
    }


# ============================================================================
# Helpers
# ============================================================================

@pytest.fixture
def assert_translation_valid():
    """Helper to assert translation validity."""
    def _assert(original: str, translated: str, target_lang: str):
        assert translated is not None
        assert len(translated) > 0
        assert translated != original
        # Add more domain-specific checks as needed
        return True
    return _assert


# ============================================================================
# Session-level Setup/Teardown
# ============================================================================

def pytest_configure(config):
    """Configure pytest session."""
    # Create test data directories if needed
    test_data_dir = PROJECT_ROOT / "tests" / "test_data"
    test_data_dir.mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Auto-add 'unit' marker to test files in tests/unit/
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Auto-add 'integration' marker to test files in tests/integration/
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
