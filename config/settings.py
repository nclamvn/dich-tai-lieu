#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings - Centralized configuration management
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings"""

    # ========== API Keys ==========
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""

    # OCR API Keys (Hybrid System)
    mathpix_app_id: Optional[str] = None
    mathpix_app_key: Optional[str] = None

    # ========== Provider & Model ==========
    provider: str = "openai"  # openai | anthropic
    model: str = "gpt-4o-mini"
    quality_mode: str = "balanced"  # fast | balanced | quality

    # ---- Per-provider model registry (env-overridable) ----
    # These feed ai_providers.unified_client so model IDs can be refreshed
    # from .env WITHOUT touching code. Defaults track the newest family the
    # repo already standardized on (see core/book_writer/prompts.py).
    anthropic_text_model: str = "claude-sonnet-4-5-20250929"
    anthropic_vision_model: str = "claude-sonnet-4-5-20250929"
    openai_text_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o"
    deepseek_text_model: str = "deepseek-chat"
    gemini_text_model: str = "gemini-2.0-flash"
    gemini_vision_model: str = "gemini-2.0-flash"

    # ---- Translation determinism & caching (live core_v2 path) ----
    # Low temperature => faithful, low-variance translation. The live
    # orchestrator previously ran at provider-default (~1.0).
    translation_temperature: float = 0.3
    # Anthropic prompt caching of the static system prefix (role + LaTeX
    # rules + profile + DNA). Cuts input tokens ~30-50% on multi-chunk docs.
    translation_prompt_cache_enabled: bool = True
    # Bump to invalidate all chunk-cache entries after a prompt/algorithm change.
    translation_prompt_version: str = "v2"

    # ---- Output pipeline (Option A: COMPLETE) ----
    # The DocumentAST + core/rendering adapters are the only DOCX/PDF renderer.
    # Stage 5 retired the legacy docx_engine/pdf_engine and the OUTPUT_PIPELINE
    # flag; content coverage is guarded by scripts/soak_render_coverage.py
    # (in CI as tests/eval/test_render_coverage.py).

    # Strip running headers/footers ("page furniture") — the book title and
    # "Author ◆ page-number" repeated on every source page — from extracted text
    # before DNA/chunking/TOC. Prevents the title from littering the translated
    # body and flooding the generated table of contents. No-op when the source
    # has no such repeats. Env override: STRIP_RUNNING_FURNITURE=false.
    strip_running_furniture: bool = True

    # Default pre-built cover template applied on export when the caller does not
    # pass one explicitly (empty = keep the plain cover). Env: COVER_TEMPLATE=noir.
    # Valid ids come from core/rendering/cover_templates.list_templates().
    cover_template: str = ""

    # Optional path to a user-supplied cover image used as a full-bleed cover on
    # export; wins over cover_template. Env: COVER_IMAGE=/path/to/cover.png.
    cover_image: str = ""

    # ---- Terminology ledger (auto-glossary + explicit glossaries) ----
    # Auto-extract key terms/proper nouns per document and inject them into the
    # cached system prompt so terminology stays consistent across every chunk.
    translation_auto_glossary_enabled: bool = True
    # Max terms rendered into the prompt terminology block (highest priority first).
    translation_glossary_max_terms: int = 80
    # Comma-separated explicit glossary IDs to load (empty = none). Glossary terms
    # outrank auto-extracted ones.
    translation_glossary_ids: str = ""

    # ---- Reliability: retry / backoff for transient API errors ----
    translation_max_retries: int = 4        # attempts per chunk before failing the job
    translation_backoff_base: float = 2.0   # exponential base (seconds)
    translation_backoff_cap: float = 60.0   # max single backoff (seconds)
    # How long a provider stays benched after a transient failure before it
    # is retried again (was: benched permanently for the whole process).
    provider_health_ttl_seconds: float = 300.0

    # ---- Bounded repair pass for suspect chunks ----
    # After translation, re-translate ONLY the chunks the deterministic quality
    # gate flags (empty / truncated / wrong-language / dropped-formula) and adopt
    # a retry only when it is strictly better. Off => today's behavior unchanged.
    translation_repair_enabled: bool = True
    # Cap how many suspect chunks a single job repairs (bounds cost/latency).
    translation_repair_max_chunks: int = 20

    # ---- Optional semantic faithfulness pass feeding the repair loop ----
    # Opt-in LLM check that judges whether a translation faithfully renders its
    # source (catches meaning drift the deterministic gate is blind to). Only
    # deterministically-clean chunks are checked, and any judged unfaithful feed
    # the SAME bounded repair loop. Off (default) => no extra LLM calls, repair
    # behavior byte-for-byte unchanged.
    translation_semantic_verify_enabled: bool = False
    # Cap how many chunks a single job semantically checks (bounds cost).
    translation_semantic_verify_max: int = 30

    # ---- Rolling cross-chunk context (deterministic, LLM-free by default) ----
    # How many older chunks feed each chunk's rolling-context gist (preceding =
    # older-context gist + exact tail of the immediately-preceding chunk).
    translation_context_window: int = 3
    # Optional LLM summary pre-pass: one short summary per chunk enriches the
    # gist. Default OFF => no extra API calls; deterministic context stands.
    translation_context_summary_enabled: bool = False

    # ---- Chunking: hard per-chunk token budget (structure-preserving) ----
    # No emitted semantic chunk exceeds this estimate_tokens count; oversized
    # chunks are split at the finest content-preserving boundary available.
    chunk_max_tokens: int = 2000

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

    # Security headers
    security_headers_enabled: bool = True

    # Cookie hardening (production should use secure=True, samesite=strict)
    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # "strict" recommended for production

    # ========== Features ==========
    cache_enabled: bool = True
    quality_validation: bool = True
    quality_threshold: float = 0.7
    glossary_enabled: bool = True
    glossary_name: Optional[str] = None

    # Global concurrency limit (max simultaneous jobs across all users)
    max_concurrent_jobs: int = 10  # Prevents API rate limit saturation

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

    # BIZ-20: Configurable cost rates & budget alerts
    cost_rate_input_per_1k: float = 0.003  # $ per 1K input tokens (default: GPT-4 class)
    cost_rate_output_per_1k: float = 0.006  # $ per 1K output tokens
    budget_limit_daily_usd: float = 0.0  # 0 = no limit; set e.g. 10.0 for $10/day
    budget_alert_threshold: float = 0.8  # Alert at 80% of daily budget

    # Translation Memory
    tm_enabled: bool = True
    tm_fuzzy_threshold: float = 0.85  # 85% similarity for fuzzy matches
    # Inject approved TM translations into the live prompt as reuse hints
    # (read/hints path only — no-op when the TM is empty/unavailable).
    tm_reuse_enabled: bool = True
    tm_max_hints: int = 5  # Max approved TM hints prepended to a chunk's prompt

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

    # WebSocket fan-out across workers (#6 Pha 1). Empty ws_redis_url => local-only
    # broadcast (single worker; current behaviour). Set to e.g. redis://host:6379/0.
    ws_redis_url: str = ""
    ws_pubsub_channel: str = "aps:events"

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

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", case_sensitive=False, extra="ignore")
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
            "CHANGE_ME",
            "changeme",
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

            # Check CSRF secret if enabled (placeholder value AND minimum length)
            if self.csrf_enabled and self.csrf_secret_key in insecure_secrets:
                errors.append(
                    "CSRF_SECRET_KEY must be set to a secure value when CSRF is enabled! "
                    "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if self.csrf_enabled and len(self.csrf_secret_key) < 32:
                errors.append(
                    "CSRF_SECRET_KEY must be at least 32 characters when CSRF is enabled in production!"
                )

            # Check auth is enabled
            if not self.session_auth_enabled and not self.api_key_auth_enabled:
                errors.append(
                    "Production mode requires authentication! "
                    "Enable SESSION_AUTH_ENABLED=true or API_KEY_AUTH_ENABLED=true"
                )

            # Check CORS origins are explicitly set — and not a wildcard, since the
            # app sends allow_credentials=True (credentialed "*" is a real hole).
            if not self.cors_origins:
                errors.append(
                    "CORS_ORIGINS must be explicitly set in production! "
                    "Example: CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
                )
            elif any(o.strip() == "*" for o in self.cors_origins.split(",")):
                errors.append(
                    "CORS_ORIGINS must not be '*' in production — credentials are allowed, "
                    "so a wildcard origin is insecure. List explicit origins instead."
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


def get_settings() -> Settings:
    """Return the process-wide ``Settings`` singleton.

    Several API modules import this accessor (``api.main``, ``api.deps``,
    ``api.auth_router``, ``api.aps_v2_service``). Before it existed those
    imports failed at call time, surfacing as HTTP 500 on ``/ws`` and on the
    password-reset flow, and — in ``api.deps.get_current_user_id`` — being
    swallowed by a broad ``except`` so auth silently fell through to
    ``"default_user"`` (auth fail-open). Returning the same instance created
    above keeps configuration consistent everywhere.
    """
    return settings
