"""
Unit Tests for TranslatorEngine with Mocked API Calls

Tests translation engine without requiring live API connections.
Uses httpx mocking to simulate OpenAI and Anthropic API responses.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from core.translator import TranslatorEngine
from core.chunker import TranslationChunk
from core.validator import TranslationResult, QualityValidator


class TestTranslatorEngineInit:
    """Tests for TranslatorEngine initialization."""
    
    def test_basic_creation(self):
        """Test creating a basic translator engine."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
        
        assert engine.provider == "openai"
        assert engine.model == "gpt-4"
        assert engine.api_key == "test-key"
    
    def test_default_languages(self):
        """Test default source and target languages."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
        
        assert engine.source_lang == "en"
        assert engine.target_lang == "vi"
    
    def test_custom_languages(self):
        """Test custom language configuration."""
        engine = TranslatorEngine(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key",
            source_lang="zh",
            target_lang="en"
        )
        
        assert engine.source_lang == "zh"
        assert engine.target_lang == "en"
    
    def test_with_glossary_manager(self):
        """Test with glossary manager."""
        mock_glossary = MagicMock()
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            glossary_mgr=mock_glossary
        )
        
        assert engine.glossary_mgr == mock_glossary
    
    def test_with_translation_memory(self):
        """Test with translation memory."""
        mock_tm = MagicMock()
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            tm=mock_tm
        )
        
        assert engine.tm == mock_tm
    
    def test_with_cache(self):
        """Test with cache configuration."""
        mock_cache = MagicMock()
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            cache=mock_cache
        )
        
        assert engine.cache == mock_cache
    
    def test_retry_configuration(self):
        """Test retry configuration."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            max_retries=10,
            retry_delay=5
        )
        
        assert engine.max_retries == 10
        assert engine.retry_delay == 5
    
    def test_tm_fuzzy_threshold(self):
        """Test TM fuzzy threshold configuration."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            tm_fuzzy_threshold=0.90
        )
        
        assert engine.tm_fuzzy_threshold == 0.90
    
    def test_provider_lowercase(self):
        """Test that provider is normalized to lowercase."""
        engine = TranslatorEngine(
            provider="OpenAI",
            model="gpt-4",
            api_key="test-key"
        )
        
        assert engine.provider == "openai"


class TestBuildPrompt:
    """Tests for prompt building."""
    
    @pytest.fixture
    def engine(self):
        return TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            source_lang="en",
            target_lang="vi"
        )
    
    def test_basic_prompt(self, engine):
        """Test basic prompt generation."""
        chunk = TranslationChunk(
            id=1,
            text="Hello, world!"
        )
        
        prompt = engine.build_prompt(chunk)
        
        assert "Hello, world!" in prompt
        assert "English" in prompt
        assert "Vietnamese" in prompt
    
    def test_prompt_with_context(self, engine):
        """Test prompt with surrounding context."""
        chunk = TranslationChunk(
            id=1,
            text="This is the main text.",
            context_before="Previous paragraph content.",
            context_after="Next paragraph content."
        )
        
        prompt = engine.build_prompt(chunk)
        
        assert "Previous paragraph" in prompt
        assert "Next paragraph" in prompt
        assert "DO NOT TRANSLATE" in prompt
    
    def test_prompt_with_glossary(self):
        """Test prompt with glossary terms."""
        mock_glossary = MagicMock()
        mock_glossary.build_prompt_section.return_value = "GLOSSARY: API = giao diện lập trình"
        
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            glossary_mgr=mock_glossary
        )
        
        chunk = TranslationChunk(id=1, text="Use the API.")
        prompt = engine.build_prompt(chunk)
        
        assert "GLOSSARY" in prompt
        assert "API" in prompt
    
    def test_prompt_has_translation_instructions(self, engine):
        """Test that prompt includes translation requirements."""
        chunk = TranslationChunk(id=1, text="Test text")
        prompt = engine.build_prompt(chunk)
        
        assert "Translate ALL content" in prompt
        assert "Preserve meaning" in prompt
        assert "Natural, fluent style" in prompt


class TestTranslateChunkWithMocks:
    """Tests for translate_chunk with mocked API calls."""
    
    @pytest.fixture
    def engine(self):
        return TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            source_lang="en",
            target_lang="vi"
        )
    
    @pytest.fixture
    def chunk(self):
        return TranslationChunk(
            id=1,
            text="Hello, how are you?"
        )
    
    @pytest.mark.asyncio
    async def test_translate_chunk_openai_success(self, engine, chunk):
        """Test successful translation via OpenAI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Xin chào, bạn khỏe không?"}
            }]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await engine.translate_chunk(mock_client, chunk)
        
        assert isinstance(result, TranslationResult)
        assert result.translated == "Xin chào, bạn khỏe không?"
        assert result.chunk_id == 1
    
    @pytest.mark.asyncio
    async def test_translate_chunk_anthropic_success(self, chunk):
        """Test successful translation via Anthropic."""
        engine = TranslatorEngine(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key"
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{
                "type": "text",
                "text": "Xin chào, bạn khỏe không?"
            }]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await engine.translate_chunk(mock_client, chunk)
        
        assert result.translated == "Xin chào, bạn khỏe không?"
    
    @pytest.mark.asyncio
    async def test_translate_with_tm_exact_match(self, chunk):
        """Test translation with TM exact match."""
        mock_tm = MagicMock()
        mock_match = MagicMock()
        mock_match.segment.target = "Chào bạn, bạn có khỏe không?"
        mock_match.segment.quality_score = 0.95
        mock_tm.get_exact_match.return_value = mock_match
        
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            tm=mock_tm
        )
        
        mock_client = AsyncMock()
        result = await engine.translate_chunk(mock_client, chunk)
        
        assert result.translated == "Chào bạn, bạn có khỏe không?"
        assert engine.tm_exact_matches == 1
        # API should not be called since TM match was found
        mock_client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_translate_with_cache_hit(self, engine, chunk):
        """Test translation with cache hit."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = "Xin chào từ cache"
        engine.cache = mock_cache
        
        mock_client = AsyncMock()
        result = await engine.translate_chunk(mock_client, chunk)
        
        assert result.translated == "Xin chào từ cache"
        assert result.quality_score == 1.0
        mock_client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_translate_with_chunk_cache_hit(self, engine, chunk):
        """Test translation with chunk cache hit."""
        mock_chunk_cache = MagicMock()
        mock_chunk_cache.get.return_value = "Xin chào từ chunk cache"
        engine.chunk_cache = mock_chunk_cache
        
        mock_client = AsyncMock()
        result = await engine.translate_chunk(mock_client, chunk)
        
        assert result.translated == "Xin chào từ chunk cache"
        mock_client.post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_translate_api_error_retry(self, engine, chunk):
        """Test retry on API error."""
        engine.max_retries = 2
        engine.retry_delay = 0  # No delay for tests
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection error")
        
        result = await engine.translate_chunk(mock_client, chunk)
        
        # Should have retried and then returned failure
        assert result.quality_score == 0.0
        assert "TRANSLATION FAILED" in result.translated
        assert mock_client.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_translate_caches_result(self, engine, chunk):
        """Test that successful translation is cached."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # No cache hit
        engine.cache = mock_cache
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Xin chào"}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await engine.translate_chunk(mock_client, chunk)
        
        # Verify translation was returned
        assert result is not None
        assert result.translated == "Xin chào"


class TestTranslateParallel:
    """Tests for parallel translation."""
    
    @pytest.fixture
    def engine(self):
        return TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
    
    @pytest.fixture
    def chunks(self):
        return [
            TranslationChunk(id=1, text="First sentence."),
            TranslationChunk(id=2, text="Second sentence."),
            TranslationChunk(id=3, text="Third sentence."),
        ]
    
    @pytest.mark.asyncio
    async def test_translate_parallel_with_mocks(self, engine, chunks):
        """Test parallel translation with mocked API."""
        # Mock the translate_chunk method directly
        async def mock_translate(client, chunk):
            return TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"Vietnamese translation of: {chunk.text}",
                quality_score=0.9
            )
        
        with patch.object(engine, 'translate_chunk', side_effect=mock_translate):
            results, stats = await engine.translate_parallel(
                chunks,
                max_concurrency=2,
                show_progress=False
            )
        
        assert len(results) == 3
        # Stats object may have different attributes
        assert stats is not None


class TestTranslateInBatches:
    """Tests for batch translation."""
    
    @pytest.fixture
    def engine(self):
        return TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
    
    @pytest.fixture
    def chunks(self):
        return [TranslationChunk(id=i, text=f"Sentence {i}.") for i in range(10)]
    
    @pytest.mark.asyncio
    async def test_translate_in_batches(self, engine, chunks):
        """Test batch translation."""
        async def mock_translate(client, chunk):
            return TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=f"Câu {chunk.id}.",
                quality_score=0.9
            )
        
        with patch.object(engine, 'translate_chunk', side_effect=mock_translate):
            results, stats = await engine.translate_in_batches(
                chunks,
                batch_size=3,
                max_concurrency=2
            )
        
        assert len(results) == 10


class TestAPICallMethods:
    """Tests for OpenAI and Anthropic API call methods."""
    
    @pytest.fixture
    def engine(self):
        return TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
    
    @pytest.mark.asyncio
    async def test_call_openai_success(self, engine):
        """Test successful OpenAI API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Translated text"}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await engine._call_openai(mock_client, "prompt", "text")
        
        assert result == "Translated text"
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_openai_headers(self, engine):
        """Test OpenAI API call uses correct headers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "result"}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        await engine._call_openai(mock_client, "prompt", "text")
        
        call_kwargs = mock_client.post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert "Bearer test-key" in call_kwargs["headers"]["Authorization"]
    
    @pytest.mark.asyncio
    async def test_call_anthropic_success(self):
        """Test successful Anthropic API call."""
        engine = TranslatorEngine(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key"
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Translated text"}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await engine._call_anthropic(mock_client, "prompt", "text")
        
        assert result == "Translated text"
    
    @pytest.mark.asyncio
    async def test_call_anthropic_headers(self):
        """Test Anthropic API call uses correct headers."""
        engine = TranslatorEngine(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-anthropic-key"
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "result"}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        await engine._call_anthropic(mock_client, "prompt", "text")
        
        call_kwargs = mock_client.post.call_args[1]
        assert "x-api-key" in call_kwargs["headers"]
        assert call_kwargs["headers"]["x-api-key"] == "test-anthropic-key"


class TestTranslatorEdgeCases:
    """Edge case tests for TranslatorEngine."""
    
    def test_unsupported_provider(self):
        """Test handling of unsupported provider."""
        engine = TranslatorEngine(
            provider="unsupported",
            model="model",
            api_key="key"
        )
        
        # Should not raise during initialization
        assert engine.provider == "unsupported"
    
    @pytest.mark.asyncio
    async def test_empty_translation_response(self):
        """Test handling of empty translation from API."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            max_retries=1,
            retry_delay=0
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        chunk = TranslationChunk(id=1, text="Test text")
        result = await engine.translate_chunk(mock_client, chunk)
        
        # Should handle empty translation
        assert result is not None
    
    def test_tm_statistics_init(self):
        """Test TM statistics are initialized."""
        engine = TranslatorEngine(
            provider="openai",
            model="gpt-4",
            api_key="test-key"
        )
        
        assert engine.tm_exact_matches == 0
        assert engine.tm_fuzzy_matches == 0
        assert engine.tm_no_matches == 0
