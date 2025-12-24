"""
Phase 3.5 - Translation Quality Module

Post-translation quality polish layer for improving translated text quality.

Phase 3.5a: Rule-based polish (normalization, cleanup)
Phase 3.5b+: LLM-based rewrite (future)

Components:
  - TranslationQualityEngine: Main quality processing engine
  - TranslationQualityConfig: Configuration for quality processing
  - QualityReport: Quality analysis results

Architecture:
  - Default mode: OFF (must be explicitly enabled)
  - Config-driven with clear kill switches
  - Non-destructive, idempotent operations
  - Domain-aware (book vs STEM)

Safety:
  - Only processes when mode != "off"
  - Preserves semantic structures (headings, theorems, formulas)
  - Minimal risk of changing meaning
"""

from core.quality.translation_quality_engine import (
    TranslationQualityEngine,
    TranslationQualityConfig,
    QualityReport,
    create_default_config,
    create_light_config,
    create_aggressive_config
)

__all__ = [
    'TranslationQualityEngine',
    'TranslationQualityConfig',
    'QualityReport',
    'create_default_config',
    'create_light_config',
    'create_aggressive_config'
]
