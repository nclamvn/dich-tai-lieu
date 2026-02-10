"""
Settings service — load/save user settings from a JSON file.

Reads defaults from config/settings.py (env-based), allows UI overrides
stored in data/settings.json. API keys are optionally encrypted.
"""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from .models import (
    AllSettings,
    GeneralSettings,
    TranslationSettings,
    BookWriterSettings,
    ApiKeySettings,
    ExportSettings,
    AdvancedSettings,
)

logger = get_logger(__name__)

SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "settings.json"

# Optional Fernet encryption for API keys
_fernet = None
try:
    from cryptography.fernet import Fernet

    key = os.environ.get("SETTINGS_ENCRYPTION_KEY")
    if key:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
except ImportError:
    pass


def _encrypt(value: str) -> str:
    if _fernet and value:
        return _fernet.encrypt(value.encode()).decode()
    return value


def _decrypt(value: str) -> str:
    if _fernet and value:
        try:
            return _fernet.decrypt(value.encode()).decode()
        except Exception:
            return value
    return value


class SettingsService:
    """Load and save user-configurable settings."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or SETTINGS_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ── Load ──

    def load(self) -> AllSettings:
        """Load settings from JSON, falling back to env-based defaults."""
        settings = self._defaults_from_env()

        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                self._merge(settings, data)
            except Exception as e:
                logger.warning("Failed to load settings.json: %s", e)

        return settings

    def load_section(self, section: str) -> dict:
        """Load a single section as dict."""
        all_settings = self.load()
        obj = getattr(all_settings, section, None)
        if obj is None:
            raise ValueError(f"Unknown section: {section}")
        d = asdict(obj)
        if section == "api_keys":
            d = obj.to_masked_dict()
        return d

    # ── Save ──

    def save_section(self, section: str, data: dict) -> dict:
        """Update a single section and persist."""
        all_settings = self.load()
        obj = getattr(all_settings, section, None)
        if obj is None:
            raise ValueError(f"Unknown section: {section}")

        if section == "api_keys":
            data = self._handle_api_key_update(obj, data)

        for k, v in data.items():
            if hasattr(obj, k):
                setattr(obj, k, v)

        self._persist(all_settings)

        # Also sync key fields back to global config/settings.py singleton
        self._sync_to_global(all_settings)

        if section == "api_keys":
            return obj.to_masked_dict()
        return asdict(obj)

    def reset_section(self, section: str) -> dict:
        """Reset a section to defaults."""
        defaults_map = {
            "general": GeneralSettings,
            "translation": TranslationSettings,
            "book_writer": BookWriterSettings,
            "api_keys": ApiKeySettings,
            "export": ExportSettings,
            "advanced": AdvancedSettings,
        }
        cls = defaults_map.get(section)
        if cls is None:
            raise ValueError(f"Unknown section: {section}")

        all_settings = self.load()
        setattr(all_settings, section, cls())
        self._persist(all_settings)

        obj = getattr(all_settings, section)
        if section == "api_keys":
            return obj.to_masked_dict()
        return asdict(obj)

    # ── Internal ──

    def _defaults_from_env(self) -> AllSettings:
        """Build AllSettings from the global Pydantic Settings."""
        try:
            from config.settings import settings as env

            return AllSettings(
                general=GeneralSettings(
                    source_lang=env.source_lang,
                    target_lang=env.target_lang,
                    quality_mode=env.quality_mode,
                    provider=env.provider,
                    model=env.model,
                ),
                translation=TranslationSettings(
                    concurrency=env.concurrency,
                    chunk_size=env.chunk_size,
                    context_window=env.context_window,
                    max_retries=env.max_retries,
                    retry_delay=env.retry_delay,
                    cache_enabled=env.cache_enabled,
                    chunk_cache_enabled=env.chunk_cache_enabled,
                    chunk_cache_ttl_days=env.chunk_cache_ttl_days,
                    checkpoint_enabled=env.checkpoint_enabled,
                    checkpoint_interval=env.checkpoint_interval,
                    tm_enabled=env.tm_enabled,
                    tm_fuzzy_threshold=env.tm_fuzzy_threshold,
                    glossary_enabled=env.glossary_enabled,
                    quality_validation=env.quality_validation,
                    quality_threshold=env.quality_threshold,
                ),
                api_keys=ApiKeySettings(
                    openai_api_key=env.openai_api_key,
                    anthropic_api_key=env.anthropic_api_key,
                    google_api_key=env.google_api_key,
                    mathpix_app_id=env.mathpix_app_id or "",
                    mathpix_app_key=env.mathpix_app_key or "",
                ),
                export=ExportSettings(
                    enable_beautification=env.enable_beautification,
                    enable_advanced_book_layout=env.enable_advanced_book_layout,
                    streaming_enabled=env.streaming_enabled,
                    streaming_batch_size=env.streaming_batch_size,
                    max_upload_size_mb=env.max_upload_size_mb,
                ),
                advanced=AdvancedSettings(
                    security_mode=env.security_mode,
                    session_auth_enabled=env.session_auth_enabled,
                    api_key_auth_enabled=env.api_key_auth_enabled,
                    csrf_enabled=env.csrf_enabled,
                    rate_limit=env.rate_limit,
                    database_backend=env.database_backend,
                    use_ast_pipeline=env.use_ast_pipeline,
                    cleanup_upload_retention_days=env.cleanup_upload_retention_days,
                    cleanup_output_retention_days=env.cleanup_output_retention_days,
                    cleanup_temp_max_age_hours=env.cleanup_temp_max_age_hours,
                ),
            )
        except Exception as e:
            logger.warning("Could not load env settings: %s", e)
            return AllSettings()

    def _merge(self, settings: AllSettings, data: dict) -> None:
        """Merge JSON data into AllSettings."""
        for section_name in ("general", "translation", "book_writer", "api_keys", "export", "advanced"):
            section_data = data.get(section_name, {})
            if not section_data:
                continue
            obj = getattr(settings, section_name)
            for k, v in section_data.items():
                if hasattr(obj, k):
                    if section_name == "api_keys":
                        setattr(obj, k, _decrypt(v))
                    else:
                        setattr(obj, k, v)

    def _persist(self, settings: AllSettings) -> None:
        """Write all settings to JSON."""
        data = {}
        for section_name in ("general", "translation", "book_writer", "export", "advanced"):
            data[section_name] = asdict(getattr(settings, section_name))

        # Encrypt API keys
        api_dict = asdict(settings.api_keys)
        data["api_keys"] = {k: _encrypt(v) for k, v in api_dict.items()}

        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    def _handle_api_key_update(self, current: ApiKeySettings, data: dict) -> dict:
        """Preserve existing keys if masked values are sent back."""
        result = {}
        current_dict = asdict(current)
        for k, v in data.items():
            if not v or "****" in str(v):
                result[k] = current_dict.get(k, "")
            else:
                result[k] = v
        return result

    def _sync_to_global(self, settings: AllSettings) -> None:
        """Push key settings back to the global Pydantic Settings singleton."""
        try:
            from config.settings import settings as env

            g = settings.general
            env.source_lang = g.source_lang
            env.target_lang = g.target_lang
            env.quality_mode = g.quality_mode
            env.provider = g.provider
            env.model = g.model

            t = settings.translation
            env.concurrency = t.concurrency
            env.chunk_size = t.chunk_size
            env.cache_enabled = t.cache_enabled
            env.glossary_enabled = t.glossary_enabled
            env.tm_enabled = t.tm_enabled
        except Exception as e:
            logger.debug("Could not sync to global settings: %s", e)


# Singleton
_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    global _service
    if _service is None:
        _service = SettingsService()
    return _service
