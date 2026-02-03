"""
Translation Engine Module for AI Publisher Pro
Supports multiple translation backends with automatic fallback
"""

from .engine_manager import EngineManager, get_engine_manager
from .engines.base import TranslationEngine, TranslationResult
from .engines.translategemma import TranslateGemmaEngine
from .engines.cloud_api import CloudAPIEngine
from .language_codes import LANGUAGE_CODES, get_language_name

__all__ = [
    # Manager
    "EngineManager",
    "get_engine_manager",
    # Base
    "TranslationEngine",
    "TranslationResult",
    # Engines
    "TranslateGemmaEngine",
    "CloudAPIEngine",
    # Utils
    "LANGUAGE_CODES",
    "get_language_name",
]
