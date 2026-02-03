"""
Unit Tests for Translation Engines
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestTranslationEngineBase:
    """Tests for base engine class"""

    def test_translation_result_creation(self):
        from core.translation.engines.base import TranslationResult

        result = TranslationResult(
            translated_text="Xin chào",
            source_lang="en",
            target_lang="vi",
            engine="test"
        )

        assert result.translated_text == "Xin chào"
        assert result.success == True
        assert result.cost is None

    def test_translation_result_error(self):
        from core.translation.engines.base import TranslationResult

        result = TranslationResult(
            translated_text="",
            source_lang="en",
            target_lang="vi",
            engine="test",
            success=False,
            error="Test error"
        )

        assert result.success == False
        assert result.error == "Test error"


class TestTranslateGemmaEngine:
    """Tests for TranslateGemma engine"""

    def test_engine_initialization(self):
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine(model_size="4b")

        assert engine.model_size == "4b"
        assert engine.engine_id == "translategemma_4b"
        assert "vi" in engine.supported_languages

    def test_language_support(self):
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()

        assert engine.supports_language("en") == True
        assert engine.supports_language("vi") == True
        assert engine.supports_language("zh") == True
        assert engine.supports_language("xyz") == False

    def test_device_detection(self):
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()

        # Should detect mps, cuda, or cpu
        assert engine.device in ["mps", "cuda", "cpu"]

    def test_engine_info(self):
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()
        info = engine.get_info()

        assert "id" in info
        assert "name" in info
        assert "model_size" in info
        assert info["offline"] == True
        assert info["cost_per_token"] == 0.0


class TestCloudAPIEngine:
    """Tests for Cloud API engine"""

    def test_engine_initialization(self):
        from core.translation.engines.cloud_api import CloudAPIEngine

        engine = CloudAPIEngine(provider="openai")

        assert engine.provider == "openai"
        assert engine.is_available() == True

    def test_language_support(self):
        from core.translation.engines.cloud_api import CloudAPIEngine

        engine = CloudAPIEngine()

        assert engine.supports_language("en") == True
        assert engine.supports_language("vi") == True


class TestEngineManager:
    """Tests for Engine Manager"""

    def test_manager_initialization(self):
        from core.translation.engine_manager import EngineManager

        manager = EngineManager(auto_register=True)

        assert len(manager.engines) >= 1  # At least cloud API

    def test_get_available_engines(self):
        from core.translation.engine_manager import EngineManager

        manager = EngineManager()
        engines = manager.get_available_engines()

        assert isinstance(engines, list)
        assert len(engines) >= 1

        for engine_info in engines:
            assert "id" in engine_info
            assert "name" in engine_info
            assert "available" in engine_info

    @pytest.mark.asyncio
    async def test_translate_with_fallback(self):
        from core.translation.engine_manager import EngineManager

        manager = EngineManager()

        # This will use cloud API fallback if TranslateGemma unavailable
        result = await manager.translate(
            "Hello",
            source_lang="en",
            target_lang="vi",
            fallback=True
        )

        assert result is not None
        assert result.source_lang == "en"
        assert result.target_lang == "vi"

    def test_singleton_instance(self):
        from core.translation.engine_manager import get_engine_manager, EngineManager

        # Reset singleton for clean test
        EngineManager._instance = None

        manager1 = get_engine_manager()
        manager2 = get_engine_manager()

        assert manager1 is manager2


class TestLanguageCodes:
    """Tests for language code utilities"""

    def test_translategemma_languages(self):
        from core.translation.language_codes import TRANSLATEGEMMA_LANGUAGES

        assert "en" in TRANSLATEGEMMA_LANGUAGES
        assert "vi" in TRANSLATEGEMMA_LANGUAGES
        assert "zh" in TRANSLATEGEMMA_LANGUAGES
        assert len(TRANSLATEGEMMA_LANGUAGES) >= 50

    def test_get_language_name(self):
        from core.translation.language_codes import get_language_name

        assert "Vietnamese" in get_language_name("vi")
        assert "English" in get_language_name("en")
        assert "中文" in get_language_name("zh")

    def test_get_language_code(self):
        from core.translation.language_codes import get_language_code

        assert get_language_code("Vietnamese") == "vi"
        assert get_language_code("English") == "en"


# Integration test (only run if GPU available)
class TestTranslateGemmaIntegration:
    """Integration tests - require actual model"""

    @pytest.mark.skipif(
        True,  # Change to False to run integration tests
        reason="Integration tests disabled by default"
    )
    @pytest.mark.asyncio
    async def test_real_translation(self):
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()

        if not engine.is_available():
            pytest.skip("TranslateGemma not available")

        result = await engine.translate(
            "Hello, how are you?",
            source_lang="en",
            target_lang="vi"
        )

        assert result.success == True
        assert len(result.translated_text) > 0
        assert result.cost == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
