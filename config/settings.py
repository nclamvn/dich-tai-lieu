#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings - Centralized configuration management
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # ========== API Keys ==========
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # OCR API Keys (Hybrid System)
    mathpix_app_id: Optional[str] = None
    mathpix_app_key: Optional[str] = None

    # ========== Provider & Model ==========
    provider: str = "openai"  # openai | anthropic
    model: str = "gpt-4o-mini"
    quality_mode: str = "balanced"  # fast | balanced | quality

    # ========== Languages ==========
    source_lang: str = "en"  # Source language code
    target_lang: str = "vi"  # Target language code

    # ========== Performance ==========
    concurrency: int = 4
    chunk_size: int = 3000
    context_window: int = 500
    max_retries: int = 5
    retry_delay: int = 3

    # ========== File Upload & Rate Limiting ==========
    max_upload_size_mb: int = 50
    max_ocr_image_size_mb: int = 10
    rate_limit: str = "60/minute"

    # ========== Security ==========
    # Security mode: development | internal | production
    # ⚠️ PRODUCTION WARNING: Change to "production" and enable auth before deploying!
    security_mode: str = "development"  # Default: no auth required

    # Session-based authentication (for internal deployment)
    # ⚠️ PRODUCTION WARNING: Enable this for production deployments!
    session_auth_enabled: bool = False  # Default OFF - enable per organization
    session_timeout_hours: int = 8  # Working day session
    # ⚠️ SECURITY: MUST be changed via SESSION_SECRET env var in production!
    session_secret: str = "INSECURE-DEV-SECRET-CHANGE-IN-PRODUCTION"
    # Session backend: memory | file (file persists across restarts)
    session_backend: str = "memory"
    session_file_path: str = "data/sessions.json"

    # CSRF Protection (only for internet-facing deployments)
    csrf_enabled: bool = False  # Default OFF - not needed for internal
    # ⚠️ SECURITY: MUST be changed via CSRF_SECRET_KEY env var in production!
    csrf_secret_key: str = "INSECURE-DEV-CSRF-CHANGE-IN-PRODUCTION"

    # API Key authentication (for API integrations)
    api_key_auth_enabled: bool = False
    api_keys: list = []  # List of valid API keys

    # CORS origins (comma-separated in env, parsed to list)
    cors_origins: str = ""  # Empty = use default dev origins

    # Rate limiting for auth endpoints
    auth_rate_limit: str = "5/minute"  # Prevent brute force

    # ========== Features ==========
    cache_enabled: bool = True
    quality_validation: bool = True
    quality_threshold: float = 0.7
    glossary_enabled: bool = True
    glossary_name: Optional[str] = None

    # Phase 5.1: Chunk Cache Settings
    chunk_cache_enabled: bool = True  # Enable chunk-level translation caching
    chunk_cache_ttl_days: int = 30  # Cache entry TTL (for future eviction)

    # Phase 5.2: Checkpoint Settings (Fault-Tolerant Resume)
    checkpoint_enabled: bool = True  # Enable job checkpointing for resume capability
    checkpoint_interval: int = 10  # Save checkpoint every N chunks

    # Phase 5.4: Multi-Format Streaming Pipeline (Memory Optimization + Live Preview)
    streaming_enabled: bool = True  # Enable memory-efficient batch processing
    streaming_batch_size: int = 100  # Chunks per batch (reduces memory usage)
    streaming_broadcast_chunks: bool = True  # Broadcast individual chunk completions
    streaming_partial_export: bool = True  # Export partial files per batch (DOCX, PDF, TXT)
    streaming_memory_limit_mb: int = 500  # Max memory per batch (monitoring)

    # Translation Memory
    tm_enabled: bool = True
    tm_fuzzy_threshold: float = 0.85  # 85% similarity for fuzzy matches

    # AST Pipeline (experimental - for PDF export enhancement)
    use_ast_pipeline: bool = False  # Default OFF for backward compatibility

    # Advanced Book Layout (Phase 4.3 - EXPERIMENTAL/OPTIONAL)
    # Adds professional book publishing features: cover, TOC, page numbering, headers, margins
    # WARNING: Has python-docx limitations (simplified odd/even headers, basic cover insertion)
    # Recommended: Keep False for stable production. Enable only for book publishing use cases.
    enable_advanced_book_layout: bool = False  # Default OFF - experimental feature

    # Document Beautification (Phase 4.4)
    # Applies 3-stage beautification pipeline: sanitization, styling, polishing
    # - Stage 1: Remove garbage chars, watermarks, normalize whitespace
    # - Stage 2: Auto-detect headings, apply professional styles, set page layout
    # - Stage 3: Add TOC, metadata, widow/orphan control
    # Safe to enable - has graceful fallback on errors
    enable_beautification: bool = True  # Default ON - improves output quality

    # ========== Database ==========
    database_backend: str = "sqlite"  # sqlite | postgresql (Sprint 2)
    database_url: Optional[str] = None
    database_dir: Path = BASE_DIR / "data"

    # ========== Cleanup / Retention ==========
    cleanup_upload_retention_days: int = 7
    cleanup_output_retention_days: int = 30
    cleanup_temp_max_age_hours: int = 24
    cleanup_checkpoint_retention_days: int = 7

    # ========== Directories ==========
    input_dir: Path = BASE_DIR / "data" / "input"
    output_dir: Path = BASE_DIR / "data" / "output"
    temp_dir: Path = BASE_DIR / "data" / "temp"
    cache_dir: Path = BASE_DIR / "data" / "cache"
    checkpoint_dir: Path = BASE_DIR / "data" / "checkpoints"  # Phase 5.2
    logs_dir: Path = BASE_DIR / "data" / "logs"
    analytics_dir: Path = BASE_DIR / "data" / "analytics"
    tm_dir: Path = BASE_DIR / "data" / "translation_memory"
    glossary_dir: Path = BASE_DIR / "glossary"

    # ========== OCR (Hybrid System) ==========
    # PaddleOCR Settings (local OCR, no API key needed)
    paddle_lang: str = "en"  # Language: en, ch, multilingual, etc.
    ocr_backend: str = "auto"  # auto, paddle, hybrid, mathpix, none

    # PDF Processing
    poppler_path: Optional[str] = None

    # Deprecated (will be removed in future version)
    # deepseek_ocr_api_url: str = ""
    # deepseek_ocr_api_key: str = ""

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env that aren't defined in model

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        for dir_path in [
            self.input_dir,
            self.output_dir,
            self.temp_dir,
            self.cache_dir,
            self.checkpoint_dir,  # Phase 5.2
            self.logs_dir,
            self.analytics_dir,
            self.tm_dir,
            self.glossary_dir
        ]:
            dir_path.mkdir(exist_ok=True, parents=True)

        # Security validation for production mode
        self._validate_security_settings()

    def _validate_security_settings(self):
        """Validate security settings for production mode."""
        import warnings

        insecure_secrets = [
            "INSECURE-DEV-SECRET-CHANGE-IN-PRODUCTION",
            "INSECURE-DEV-CSRF-CHANGE-IN-PRODUCTION",
            "change-this-in-production",
            "change-this-secret-key-in-production-asap",
        ]

        if self.security_mode == "production":
            errors = []

            # Check session secret
            if self.session_secret in insecure_secrets:
                errors.append(
                    "SESSION_SECRET must be set to a secure value in production! "
                    "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )

            # Check session secret minimum length
            if len(self.session_secret) < 32:
                errors.append(
                    "SESSION_SECRET must be at least 32 characters in production!"
                )

            # Check CSRF secret if enabled
            if self.csrf_enabled and self.csrf_secret_key in insecure_secrets:
                errors.append(
                    "CSRF_SECRET_KEY must be set to a secure value when CSRF is enabled! "
                    "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )

            # Check auth is enabled
            if not self.session_auth_enabled and not self.api_key_auth_enabled:
                errors.append(
                    "Production mode requires authentication! "
                    "Enable SESSION_AUTH_ENABLED=true or API_KEY_AUTH_ENABLED=true"
                )

            # Check CORS origins are explicitly set
            if not self.cors_origins:
                errors.append(
                    "CORS_ORIGINS must be explicitly set in production! "
                    "Example: CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
                )

            if errors:
                raise ValueError(
                    "SECURITY ERROR - Production mode requires secure configuration:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                )

        elif self.security_mode == "internal":
            # Internal mode: warn but don't block
            if self.session_secret in insecure_secrets:
                warnings.warn(
                    "Running internal mode with default secrets. "
                    "Set SESSION_SECRET env var for better security.",
                    UserWarning
                )

        elif self.security_mode == "development":
            # Warn about insecure defaults in development
            if self.session_secret in insecure_secrets:
                warnings.warn(
                    "Running with default insecure secrets. "
                    "Set SESSION_SECRET and CSRF_SECRET_KEY env vars for production.",
                    UserWarning
                )

    def get_cors_origins(self) -> list:
        """Get CORS origins as a list. Falls back to dev defaults if empty."""
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Dev defaults
        return [
            "http://localhost:3001",
            "http://localhost:8000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4000",
            "http://127.0.0.1:4000",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
        ]

    def get_api_key(self) -> str:
        """Get API key based on provider"""
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return self.openai_api_key
        elif self.provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in .env")
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_model_config(self) -> dict:
        """Get model configuration based on quality mode"""
        model_map = {
            "openai": {
                "fast": "gpt-4o-mini",
                "balanced": "gpt-4o",
                "quality": "gpt-4-turbo-preview"
            },
            "anthropic": {
                "fast": "claude-3-5-haiku-20241022",
                "balanced": "claude-3-5-sonnet-20241022",
                "quality": "claude-3-5-sonnet-20241022"
            }
        }

        # Use specified model or auto-select based on quality mode
        selected_model = self.model or model_map[self.provider][self.quality_mode]

        # Chunk parameters adaptive based on model
        chunk_params = {
            "gpt-4o-mini": {"max_chars": 2000, "context_window": 500},
            "gpt-4o": {"max_chars": 3000, "context_window": 800},
            "gpt-4-turbo-preview": {"max_chars": 4000, "context_window": 1000},
            "claude-3-5-haiku-20241022": {"max_chars": 2500, "context_window": 600},
            "claude-3-5-sonnet-20241022": {"max_chars": 3500, "context_window": 900},
        }

        default_chunk = {"max_chars": 2500, "context_window": 600}
        chunk_config = chunk_params.get(selected_model, default_chunk)

        return {
            "model": selected_model,
            "max_chars": chunk_config["max_chars"],
            "context_window": chunk_config["context_window"]
        }

    def print_config(self):
        """Print configuration summary"""
        print("\n" + "="*70)
        print("⚙️  CONFIGURATION")
        print("="*70)
        print(f"Provider:        {self.provider}")
        print(f"Model:           {self.model}")
        print(f"Quality Mode:    {self.quality_mode}")
        print(f"Concurrency:     {self.concurrency}")
        print(f"Chunk Size:      {self.chunk_size}")
        print(f"Context Window:  {self.context_window}")
        print(f"Cache Enabled:   {self.cache_enabled}")
        print(f"Glossary:        {self.glossary_name or 'default'}")
        print("="*70 + "\n")


# Global settings instance
settings = Settings()
