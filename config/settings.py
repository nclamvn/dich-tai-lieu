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
    security_mode: str = "development"  # Default: no auth required

    # Session-based authentication (for internal deployment)
    session_auth_enabled: bool = False  # Default OFF - enable per organization
    session_timeout_hours: int = 8  # Working day session
    session_secret: str = "change-this-in-production"  # Auto-gen per org

    # CSRF Protection (only for internet-facing deployments)
    csrf_enabled: bool = False  # Default OFF - not needed for internal
    csrf_secret_key: str = "change-this-secret-key-in-production-asap"

    # API Key authentication (for API integrations)
    api_key_auth_enabled: bool = False
    api_keys: list = []  # List of valid API keys

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
