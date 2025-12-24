"""
Smart Pipeline - Cost-Optimized Translation
AI Publisher Pro

Default model: GPT-4o-mini (best balance of quality/cost)

Modules:
- tiered_config: Model definitions and configuration
- content_analyzer: Content analysis for smart routing
- translation_service: Translation with intelligent model selection
- cost_optimizer: Legacy cost optimization (deprecated)
"""

from .tiered_config import (
    TranslationMode,
    ContentType,
    ModelConfig,
    TieredConfig,
    MODELS,
    get_economy_config,
    get_balanced_config,
    get_quality_config,
    estimate_cost,
)

from .content_analyzer import (
    ContentAnalysis,
    ContentAnalyzer,
)

from .translation_service import (
    TranslationResult,
    DocumentResult,
    TranslationService,
    translate_quick,
)

__all__ = [
    # Enums
    "TranslationMode",
    "ContentType",

    # Config
    "ModelConfig",
    "TieredConfig",
    "MODELS",
    "get_economy_config",
    "get_balanced_config",
    "get_quality_config",
    "estimate_cost",

    # Analyzer
    "ContentAnalysis",
    "ContentAnalyzer",

    # Service
    "TranslationResult",
    "DocumentResult",
    "TranslationService",
    "translate_quick",
]
