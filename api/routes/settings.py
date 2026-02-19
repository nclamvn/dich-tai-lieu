"""Settings API routes — CRUD per section."""

from fastapi import APIRouter, HTTPException, Request
from dataclasses import asdict

from api.schemas.settings import (
    GeneralSettingsSchema,
    TranslationSettingsSchema,
    BookWriterSettingsSchema,
    ApiKeySettingsSchema,
    ExportSettingsSchema,
    AdvancedSettingsSchema,
)
from core.settings.service import get_settings_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])

SECTION_SCHEMAS = {
    "general": GeneralSettingsSchema,
    "translation": TranslationSettingsSchema,
    "book_writer": BookWriterSettingsSchema,
    "api_keys": ApiKeySettingsSchema,
    "export": ExportSettingsSchema,
    "advanced": AdvancedSettingsSchema,
}


@router.get("/")
async def get_all_settings():
    """Get all settings (API keys masked)."""
    svc = get_settings_service()
    all_s = svc.load()
    result = {}
    for section in SECTION_SCHEMAS:
        obj = getattr(all_s, section)
        if section == "api_keys":
            result[section] = obj.to_masked_dict()
        else:
            result[section] = asdict(obj)
    return result


@router.get("/{section}")
async def get_section(section: str):
    """Get a single settings section."""
    if section not in SECTION_SCHEMAS:
        raise HTTPException(404, f"Unknown section: {section}")
    svc = get_settings_service()
    return svc.load_section(section)


@router.put("/{section}")
async def update_section(section: str, request: Request):
    """Update a settings section."""
    if section not in SECTION_SCHEMAS:
        raise HTTPException(404, f"Unknown section: {section}")

    data = await request.json()

    # Validate via Pydantic schema
    schema_cls = SECTION_SCHEMAS[section]
    try:
        validated = schema_cls(**data)
    except Exception as e:
        raise HTTPException(422, str(e))

    svc = get_settings_service()
    updated = svc.save_section(section, validated.model_dump())
    return updated


@router.post("/{section}/reset")
async def reset_section(section: str):
    """Reset a section to defaults."""
    if section not in SECTION_SCHEMAS:
        raise HTTPException(404, f"Unknown section: {section}")
    svc = get_settings_service()
    return svc.reset_section(section)
