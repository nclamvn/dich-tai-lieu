"""Pydantic schemas for Settings API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class GeneralSettingsSchema(BaseModel):
    app_name: str = "AI Publisher Pro"
    source_lang: str = "en"
    target_lang: str = "vi"
    quality_mode: str = "balanced"
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    theme: str = "system"
    locale: str = "en"


class TranslationSettingsSchema(BaseModel):
    concurrency: int = Field(4, ge=1, le=20)
    chunk_size: int = Field(3000, ge=500, le=10000)
    context_window: int = Field(500, ge=0, le=3000)
    max_retries: int = Field(5, ge=1, le=20)
    retry_delay: int = Field(3, ge=1, le=30)
    cache_enabled: bool = True
    chunk_cache_enabled: bool = True
    chunk_cache_ttl_days: int = Field(30, ge=1)
    checkpoint_enabled: bool = True
    checkpoint_interval: int = Field(10, ge=1)
    tm_enabled: bool = True
    tm_fuzzy_threshold: float = Field(0.85, ge=0.5, le=1.0)
    glossary_enabled: bool = True
    quality_validation: bool = True
    quality_threshold: float = Field(0.7, ge=0.0, le=1.0)


class BookWriterSettingsSchema(BaseModel):
    default_genre: str = "non-fiction"
    default_language: str = "en"
    default_output_formats: list[str] = ["docx"]
    words_per_page: int = Field(250, ge=100, le=500)
    sections_per_chapter: int = Field(4, ge=1, le=10)
    max_expansion_rounds: int = Field(3, ge=1, le=10)
    enable_enrichment: bool = True
    enable_quality_check: bool = True


class ApiKeySettingsSchema(BaseModel):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    mathpix_app_id: str = ""
    mathpix_app_key: str = ""


class ExportSettingsSchema(BaseModel):
    default_format: str = "docx"
    enable_beautification: bool = True
    enable_advanced_book_layout: bool = False
    streaming_enabled: bool = True
    streaming_batch_size: int = Field(100, ge=10, le=1000)
    max_upload_size_mb: int = Field(50, ge=1, le=500)


class AdvancedSettingsSchema(BaseModel):
    security_mode: str = "development"
    session_auth_enabled: bool = False
    api_key_auth_enabled: bool = False
    csrf_enabled: bool = False
    rate_limit: str = "60/minute"
    database_backend: str = "sqlite"
    use_ast_pipeline: bool = False
    cleanup_upload_retention_days: int = Field(7, ge=1)
    cleanup_output_retention_days: int = Field(30, ge=1)
    cleanup_temp_max_age_hours: int = Field(24, ge=1)
    debug_mode: bool = False


class AllSettingsResponse(BaseModel):
    general: GeneralSettingsSchema
    translation: TranslationSettingsSchema
    book_writer: BookWriterSettingsSchema
    api_keys: ApiKeySettingsSchema
    export: ExportSettingsSchema
    advanced: AdvancedSettingsSchema
