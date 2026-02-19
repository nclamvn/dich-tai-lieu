"""
Translation Engine Manager
Handles engine selection, fallback, and coordination
"""

import logging
from typing import Dict, List, Optional
from .engines.base import TranslationEngine, TranslationResult

logger = logging.getLogger(__name__)
from .engines.translategemma import TranslateGemmaEngine
from .engines.cloud_api import CloudAPIEngine
from .engines.llama_cpp import LlamaCppEngine


class EngineManager:
    """
    Manages multiple translation engines with automatic fallback.

    Usage:
        manager = EngineManager()
        result = await manager.translate("Hello", "en", "vi")
    """

    _instance: Optional['EngineManager'] = None

    def __init__(self, auto_register: bool = True):
        """
        Initialize engine manager.

        Args:
            auto_register: Automatically register default engines
        """
        self.engines: Dict[str, TranslationEngine] = {}
        self._default_engine: Optional[str] = None
        self._fallback_engine: str = "cloud_api_auto"

        if auto_register:
            self._register_default_engines()

    @classmethod
    def get_instance(cls) -> 'EngineManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_engines(self):
        """Register default translation engines"""
        # Always register cloud API as fallback
        self.register_engine(CloudAPIEngine(provider="auto"))

        # Try LlamaCpp (recommended for Apple Silicon)
        try:
            llama_engine = LlamaCppEngine()
            if llama_engine.is_available():
                self.register_engine(llama_engine)
                self._default_engine = llama_engine.engine_id
                logger.info("LlamaCpp available: %s", llama_engine.model_id)
            else:
                logger.debug("LlamaCpp not available: %s", llama_engine._error)
        except Exception as e:
            logger.debug("Could not initialize LlamaCpp: %s", e)

        # Try TranslateGemma PyTorch (fallback for CUDA systems)
        try:
            gemma_engine = TranslateGemmaEngine(model_size="4b")
            if gemma_engine.is_available():
                self.register_engine(gemma_engine)
                if not self._default_engine or self._default_engine == self._fallback_engine:
                    self._default_engine = gemma_engine.engine_id
                logger.info("TranslateGemma available on %s", gemma_engine.device)
            else:
                logger.debug("TranslateGemma not available")
        except Exception as e:
            logger.debug("Could not initialize TranslateGemma: %s", e)

        # Set default to cloud if no local engine
        if not self._default_engine:
            self._default_engine = self._fallback_engine

    def register_engine(self, engine: TranslationEngine):
        """Register a translation engine"""
        self.engines[engine.engine_id] = engine
        logger.info("Registered engine: %s", engine.name)

    def unregister_engine(self, engine_id: str):
        """Unregister a translation engine"""
        if engine_id in self.engines:
            del self.engines[engine_id]

    def get_engine(self, engine_id: str) -> Optional[TranslationEngine]:
        """Get engine by ID"""
        return self.engines.get(engine_id)

    def get_available_engines(self) -> List[dict]:
        """Get list of available engines for UI/API"""
        return [
            engine.get_info()
            for engine in self.engines.values()
        ]

    def get_default_engine_id(self) -> str:
        """Get default engine ID"""
        return self._default_engine or self._fallback_engine

    def set_default_engine(self, engine_id: str):
        """Set default engine"""
        if engine_id in self.engines:
            self._default_engine = engine_id
        else:
            raise ValueError(f"Engine '{engine_id}' not registered")

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        engine_id: Optional[str] = None,
        fallback: bool = True
    ) -> TranslationResult:
        """
        Translate text with automatic engine selection and fallback.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            engine_id: Specific engine to use (None for default)
            fallback: Enable fallback to cloud API on failure

        Returns:
            TranslationResult
        """
        # Select engine
        selected_id = engine_id or self._default_engine or self._fallback_engine
        engine = self.engines.get(selected_id)

        if not engine:
            if fallback:
                engine = self.engines.get(self._fallback_engine)
            if not engine:
                return TranslationResult(
                    translated_text="",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    engine="none",
                    success=False,
                    error=f"Engine '{selected_id}' not available"
                )

        # Check availability
        if not engine.is_available():
            if fallback and selected_id != self._fallback_engine:
                logger.warning("%s unavailable, falling back to Cloud API", engine.name)
                engine = self.engines.get(self._fallback_engine)
            else:
                return TranslationResult(
                    translated_text="",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    engine=selected_id,
                    success=False,
                    error=f"Engine '{selected_id}' is not available"
                )

        # Attempt translation
        try:
            result = await engine.translate(text, source_lang, target_lang)

            # Fallback on failure
            if not result.success and fallback and engine.engine_id != self._fallback_engine:
                logger.warning("%s failed: %s, falling back", engine.name, result.error)
                fallback_engine = self.engines.get(self._fallback_engine)
                if fallback_engine:
                    result = await fallback_engine.translate(text, source_lang, target_lang)

            return result

        except Exception as e:
            if fallback and engine.engine_id != self._fallback_engine:
                fallback_engine = self.engines.get(self._fallback_engine)
                if fallback_engine:
                    return await fallback_engine.translate(text, source_lang, target_lang)

            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=engine.engine_id,
                success=False,
                error=str(e)
            )

    def unload_all(self):
        """Unload all models to free memory"""
        for engine in self.engines.values():
            if hasattr(engine, 'unload_model'):
                engine.unload_model()


# Singleton accessor
def get_engine_manager() -> EngineManager:
    """Get the global engine manager instance"""
    return EngineManager.get_instance()
