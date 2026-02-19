"""
Settings models — dataclasses for each settings section.

These represent the user-configurable settings stored in settings.json.
The global Pydantic Settings in config/settings.py reads from .env;
these models are for runtime overrides via the UI.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GeneralSettings:
    """General application settings."""
    app_name: str = "AI Publisher Pro"
    source_lang: str = "en"
    target_lang: str = "vi"
    quality_mode: str = "balanced"  # fast | balanced | quality
    provider: str = "openai"  # openai | anthropic
    model: str = "gpt-4o-mini"
    theme: str = "system"  # light | dark | system
    locale: str = "en"  # en | vi


@dataclass
class TranslationSettings:
    """Translation pipeline settings."""
    concurrency: int = 4
    chunk_size: int = 3000
    context_window: int = 500
    max_retries: int = 5
    retry_delay: int = 3
    cache_enabled: bool = True
    chunk_cache_enabled: bool = True
    chunk_cache_ttl_days: int = 30
    checkpoint_enabled: bool = True
    checkpoint_interval: int = 10
    tm_enabled: bool = True
    tm_fuzzy_threshold: float = 0.85
    glossary_enabled: bool = True
    quality_validation: bool = True
    quality_threshold: float = 0.7


@dataclass
class BookWriterSettings:
    """Book Writer pipeline settings."""
    default_genre: str = "non-fiction"
    default_language: str = "en"
    default_output_formats: list = field(default_factory=lambda: ["docx"])
    words_per_page: int = 250
    sections_per_chapter: int = 4
    max_expansion_rounds: int = 3
    enable_enrichment: bool = True
    enable_quality_check: bool = True


@dataclass
class ApiKeySettings:
    """API key configuration (values stored encrypted)."""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    mathpix_app_id: str = ""
    mathpix_app_key: str = ""

    def to_masked_dict(self) -> dict:
        """Return dict with API keys masked for display."""
        result = {}
        for k, v in asdict(self).items():
            if v and len(v) > 8:
                result[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
            elif v:
                result[k] = "****"
            else:
                result[k] = ""
        return result


@dataclass
class ExportSettings:
    """Export and output settings."""
    default_format: str = "docx"
    enable_beautification: bool = True
    enable_advanced_book_layout: bool = False
    streaming_enabled: bool = True
    streaming_batch_size: int = 100
    max_upload_size_mb: int = 50


@dataclass
class AdvancedSettings:
    """Advanced / developer settings."""
    security_mode: str = "development"  # development | internal | production
    session_auth_enabled: bool = False
    api_key_auth_enabled: bool = False
    csrf_enabled: bool = False
    rate_limit: str = "60/minute"
    database_backend: str = "sqlite"
    use_ast_pipeline: bool = False
    cleanup_upload_retention_days: int = 7
    cleanup_output_retention_days: int = 30
    cleanup_temp_max_age_hours: int = 24
    debug_mode: bool = False


@dataclass
class AllSettings:
    """Container for all settings sections."""
    general: GeneralSettings = field(default_factory=GeneralSettings)
    translation: TranslationSettings = field(default_factory=TranslationSettings)
    book_writer: BookWriterSettings = field(default_factory=BookWriterSettings)
    api_keys: ApiKeySettings = field(default_factory=ApiKeySettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    advanced: AdvancedSettings = field(default_factory=AdvancedSettings)
