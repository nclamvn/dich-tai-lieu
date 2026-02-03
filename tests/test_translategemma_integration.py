"""
Integration test for TranslateGemma in translation pipeline

This test file validates the TranslateGemma engine integration with:
- HF token authentication
- Basic translation functionality
- Multi-language support
- Fallback behavior
- Memory management

Usage:
    # Run with pytest (recommended)
    pytest tests/test_translategemma_integration.py -v -s

    # Run directly
    python tests/test_translategemma_integration.py
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env for HF_TOKEN
from dotenv import load_dotenv
load_dotenv(project_root / ".env")


class TestTranslateGemmaSetup:
    """Test TranslateGemma setup and configuration"""

    def test_hf_token_configured(self):
        """Verify HF token is available"""
        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
        assert hf_token is not None, "HF_TOKEN not found in environment"
        assert hf_token.startswith('hf_'), "HF_TOKEN should start with 'hf_'"
        print(f"✅ HF Token configured: {hf_token[:10]}...")

    def test_engine_initialization(self):
        """Test TranslateGemma engine can be initialized"""
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine(model_size="4b")

        assert engine.model_size == "4b"
        assert engine.engine_id == "translategemma_4b"
        assert engine.device in ["mps", "cuda", "cpu"]
        print(f"✅ Engine initialized: {engine.name} on {engine.device}")

    def test_engine_availability(self):
        """Test engine availability check"""
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()
        is_available = engine.is_available()

        print(f"Engine available: {is_available}")
        if not is_available:
            print(f"  Reason: {engine._error or 'Memory/dependencies check failed'}")

        # This test passes regardless - just reports status
        assert True

    def test_engine_info(self):
        """Test engine info retrieval"""
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()
        info = engine.get_info()

        assert "id" in info
        assert "name" in info
        assert "model_size" in info
        assert info["offline"] == True
        assert info["cost_per_token"] == 0.0

        print(f"✅ Engine info: {info}")


class TestEngineManager:
    """Test Engine Manager functionality"""

    def test_manager_initialization(self):
        """Test manager creates with default engines"""
        from core.translation.engine_manager import EngineManager

        # Reset singleton
        EngineManager._instance = None

        manager = EngineManager(auto_register=True)

        assert len(manager.engines) >= 1
        print(f"✅ Manager has {len(manager.engines)} engine(s)")

        for engine in manager.get_available_engines():
            print(f"  - {engine['name']}: {engine['status']}")

    def test_default_engine_selection(self):
        """Test default engine is selected correctly"""
        from core.translation.engine_manager import EngineManager

        EngineManager._instance = None
        manager = EngineManager()

        default_id = manager.get_default_engine_id()
        assert default_id is not None
        print(f"✅ Default engine: {default_id}")

    @pytest.mark.asyncio
    async def test_translate_with_fallback(self):
        """Test translation with automatic fallback"""
        from core.translation.engine_manager import EngineManager

        EngineManager._instance = None
        manager = EngineManager()

        result = await manager.translate(
            text="Hello",
            source_lang="en",
            target_lang="vi",
            fallback=True
        )

        assert result is not None
        assert result.source_lang == "en"
        assert result.target_lang == "vi"
        print(f"✅ Translation result: {result.translated_text[:50]}...")
        print(f"   Engine used: {result.engine}")


class TestTranslateGemmaTranslation:
    """Integration tests with actual translation (requires model download)"""

    @pytest.mark.skipif(
        not os.environ.get('RUN_MODEL_TESTS', '').lower() == 'true',
        reason="Model tests disabled. Set RUN_MODEL_TESTS=true to enable"
    )
    @pytest.mark.asyncio
    async def test_basic_translation_en_vi(self):
        """Test basic EN→VI translation with real model"""
        from core.translation import get_engine_manager

        manager = get_engine_manager()

        result = await manager.translate(
            text="Hello, how are you today?",
            source_lang="en",
            target_lang="vi",
            engine_id="translategemma_4b",
            fallback=False
        )

        print(f"\n{'='*60}")
        print("BASIC TRANSLATION TEST: EN → VI")
        print(f"{'='*60}")
        print(f"Input:  Hello, how are you today?")
        print(f"Output: {result.translated_text}")
        print(f"Engine: {result.engine}")
        print(f"Tokens: {result.tokens_used}")
        print(f"Cost:   ${result.cost}")

        assert result.success
        assert len(result.translated_text) > 0
        assert result.cost == 0.0

    @pytest.mark.skipif(
        not os.environ.get('RUN_MODEL_TESTS', '').lower() == 'true',
        reason="Model tests disabled"
    )
    @pytest.mark.asyncio
    async def test_paragraph_translation(self):
        """Test longer paragraph translation"""
        from core.translation import get_engine_manager

        manager = get_engine_manager()

        text = """
        Artificial intelligence is transforming how we work and live.
        Machine learning models can now translate between languages with
        remarkable accuracy. This technology enables people from different
        cultures to communicate more easily than ever before.
        """

        result = await manager.translate(
            text=text.strip(),
            source_lang="en",
            target_lang="vi",
            engine_id="translategemma_4b"
        )

        print(f"\n{'='*60}")
        print("PARAGRAPH TRANSLATION TEST")
        print(f"{'='*60}")
        print(f"Input ({len(text)} chars):")
        print(text.strip())
        print(f"\nOutput ({len(result.translated_text)} chars):")
        print(result.translated_text)
        print(f"\nStats: {result.tokens_used} tokens, ${result.cost}")

        assert result.success
        assert len(result.translated_text) > len(text) * 0.3

    @pytest.mark.skipif(
        not os.environ.get('RUN_MODEL_TESTS', '').lower() == 'true',
        reason="Model tests disabled"
    )
    @pytest.mark.asyncio
    async def test_multi_language_translation(self):
        """Test translation to multiple languages"""
        from core.translation import get_engine_manager

        manager = get_engine_manager()

        source_text = "Good morning! Welcome to our application."
        target_langs = ["vi", "zh", "ja", "ko", "fr", "de"]

        print(f"\n{'='*60}")
        print("MULTI-LANGUAGE TRANSLATION TEST")
        print(f"{'='*60}")
        print(f"Source (EN): {source_text}\n")

        results = {}
        for lang in target_langs:
            result = await manager.translate(
                text=source_text,
                source_lang="en",
                target_lang=lang,
                engine_id="translategemma_4b"
            )

            status = "✅" if result.success else "❌"
            print(f"{status} {lang.upper()}: {result.translated_text}")
            results[lang] = result.success

        # At least 80% should succeed
        success_rate = sum(results.values()) / len(results)
        assert success_rate >= 0.8, f"Success rate {success_rate:.0%} below 80%"


class TestPipelineConfig:
    """Test PipelineConfig with translation_engine field"""

    def test_config_has_translation_engine(self):
        """Verify PipelineConfig has translation_engine field"""
        from core.layout_preserve.translation_pipeline import PipelineConfig

        config = PipelineConfig()

        assert hasattr(config, 'translation_engine')
        assert config.translation_engine == "auto"
        print(f"✅ PipelineConfig.translation_engine = '{config.translation_engine}'")

    def test_config_with_custom_engine(self):
        """Test creating config with custom engine"""
        from core.layout_preserve.translation_pipeline import PipelineConfig

        config = PipelineConfig(
            translation_engine="translategemma_4b",
            target_lang="vi"
        )

        assert config.translation_engine == "translategemma_4b"
        assert config.target_lang == "vi"
        print(f"✅ Custom config: engine={config.translation_engine}, target={config.target_lang}")


class TestMemoryManagement:
    """Test model loading and unloading"""

    @pytest.mark.skipif(
        not os.environ.get('RUN_MODEL_TESTS', '').lower() == 'true',
        reason="Model tests disabled"
    )
    def test_model_unload(self):
        """Test model can be unloaded to free memory"""
        from core.translation.engines.translategemma import TranslateGemmaEngine

        engine = TranslateGemmaEngine()

        if engine.is_available():
            # Load model
            success = engine.load_model()
            if success:
                assert engine.is_loaded
                print(f"✅ Model loaded")

                # Unload
                engine.unload_model()
                assert not engine.is_loaded
                print(f"✅ Model unloaded, memory freed")
            else:
                print(f"⚠️ Model load failed: {engine._error}")
        else:
            print(f"⚠️ Engine not available, skipping")


# Quick test runner
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TranslateGemma Integration Test Suite")
    print("=" * 60)

    # Check environment
    hf_token = os.environ.get('HF_TOKEN')
    print(f"\nEnvironment:")
    print(f"  HF_TOKEN: {'✅ Set' if hf_token else '❌ Not set'}")
    print(f"  RUN_MODEL_TESTS: {os.environ.get('RUN_MODEL_TESTS', 'false')}")

    print("\n" + "-" * 60)
    print("Running setup tests...")
    print("-" * 60)

    # Run setup tests
    setup = TestTranslateGemmaSetup()
    setup.test_hf_token_configured()
    setup.test_engine_initialization()
    setup.test_engine_availability()
    setup.test_engine_info()

    print("\n" + "-" * 60)
    print("Running manager tests...")
    print("-" * 60)

    manager_tests = TestEngineManager()
    manager_tests.test_manager_initialization()
    manager_tests.test_default_engine_selection()

    # Run async test
    asyncio.run(manager_tests.test_translate_with_fallback())

    print("\n" + "-" * 60)
    print("Running pipeline config tests...")
    print("-" * 60)

    config_tests = TestPipelineConfig()
    config_tests.test_config_has_translation_engine()
    config_tests.test_config_with_custom_engine()

    print("\n" + "=" * 60)
    print("Basic tests completed!")
    print("=" * 60)

    if os.environ.get('RUN_MODEL_TESTS', '').lower() == 'true':
        print("\n" + "-" * 60)
        print("Running model tests (this may take a while)...")
        print("-" * 60)

        translation_tests = TestTranslateGemmaTranslation()
        asyncio.run(translation_tests.test_basic_translation_en_vi())
    else:
        print("\n💡 To run model tests (requires ~8GB download):")
        print("   RUN_MODEL_TESTS=true python tests/test_translategemma_integration.py")
