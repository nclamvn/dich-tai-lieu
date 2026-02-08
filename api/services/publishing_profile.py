"""
Custom Publishing Profiles — Built-in + user-defined output profiles.

Profiles control how translated documents are rendered:
- Output format (docx, pdf, epub)
- Style guide (typography, layout preferences)
- Template selection
- Special formatting instructions

Built-in profiles for common use cases.
Custom profiles persisted as JSON.

Standalone module — no core/ imports.

Usage::

    store = ProfileStore(storage_dir="data/profiles")

    # List built-in profiles
    profiles = store.list_profiles()

    # Get a profile
    profile = store.get_profile("novel")

    # Create custom profile
    pid = store.create_profile(
        name="My Style",
        output_format="epub",
        style_guide="Use simple language, short paragraphs",
    )

    # Generate LLM prompt instructions
    instructions = profile.to_prompt()
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PublishingProfile:
    """A publishing profile defining output style and format."""

    id: str
    name: str
    output_format: str = "docx"  # docx, pdf, epub
    style_guide: str = ""
    template: str = "auto"  # ebook, academic, business, auto
    special_instructions: str = ""
    font_family: str = ""
    font_size: str = ""
    line_spacing: float = 0.0
    is_builtin: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.updated_at == 0.0:
            self.updated_at = now

    def to_prompt(self) -> str:
        """Convert profile to LLM rendering instructions."""
        parts = []

        if self.style_guide:
            parts.append(f"Style Guide: {self.style_guide}")

        if self.template != "auto":
            parts.append(f"Template: {self.template}")

        if self.font_family:
            parts.append(f"Font: {self.font_family}")

        if self.font_size:
            parts.append(f"Font Size: {self.font_size}")

        if self.line_spacing > 0:
            parts.append(f"Line Spacing: {self.line_spacing}")

        if self.special_instructions:
            parts.append(f"Instructions: {self.special_instructions}")

        if not parts:
            return f"Output format: {self.output_format}"

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "output_format": self.output_format,
            "style_guide": self.style_guide,
            "template": self.template,
            "special_instructions": self.special_instructions,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PublishingProfile:
        return cls(
            id=data["id"],
            name=data["name"],
            output_format=data.get("output_format", "docx"),
            style_guide=data.get("style_guide", ""),
            template=data.get("template", "auto"),
            special_instructions=data.get("special_instructions", ""),
            font_family=data.get("font_family", ""),
            font_size=data.get("font_size", ""),
            line_spacing=data.get("line_spacing", 0.0),
            is_builtin=data.get("is_builtin", False),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

BUILTIN_PROFILES: List[PublishingProfile] = [
    PublishingProfile(
        id="novel",
        name="Novel / Fiction",
        output_format="epub",
        style_guide="Flowing prose, chapter breaks at major sections. "
                     "Preserve dialogue formatting and paragraph indentation.",
        template="ebook",
        is_builtin=True,
    ),
    PublishingProfile(
        id="academic",
        name="Academic Paper",
        output_format="pdf",
        style_guide="Formal academic tone. Preserve citations, footnotes, "
                     "and bibliography formatting. Keep section numbering.",
        template="academic",
        font_family="Times New Roman",
        font_size="12pt",
        line_spacing=2.0,
        is_builtin=True,
    ),
    PublishingProfile(
        id="business",
        name="Business Report",
        output_format="docx",
        style_guide="Professional tone. Clear section headers, bullet points, "
                     "and executive summary formatting.",
        template="business",
        font_family="Calibri",
        font_size="11pt",
        line_spacing=1.15,
        is_builtin=True,
    ),
    PublishingProfile(
        id="technical",
        name="Technical Documentation",
        output_format="pdf",
        style_guide="Precise technical language. Preserve code blocks, "
                     "command examples, and API references.",
        template="auto",
        font_family="Consolas",
        font_size="10pt",
        is_builtin=True,
    ),
    PublishingProfile(
        id="simple",
        name="Simple / Plain",
        output_format="docx",
        style_guide="Clean, minimal formatting. Simple paragraphs.",
        template="auto",
        is_builtin=True,
    ),
]


# ---------------------------------------------------------------------------
# ProfileStore
# ---------------------------------------------------------------------------

class ProfileStore:
    """Manage publishing profiles with JSON persistence.

    Built-in profiles are always available.
    Custom profiles are persisted as JSON files.
    """

    def __init__(self, storage_dir: str = "data/profiles") -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._builtins: Dict[str, PublishingProfile] = {
            p.id: p for p in BUILTIN_PROFILES
        }
        self._custom: Dict[str, PublishingProfile] = {}
        self._load_custom()

    def get_profile(self, profile_id: str) -> Optional[PublishingProfile]:
        """Get a profile by ID (checks custom first, then built-in)."""
        return self._custom.get(profile_id) or self._builtins.get(profile_id)

    def list_profiles(self, include_builtin: bool = True) -> List[PublishingProfile]:
        """List all available profiles."""
        profiles = []
        if include_builtin:
            profiles.extend(self._builtins.values())
        profiles.extend(self._custom.values())
        return profiles

    def list_builtin(self) -> List[PublishingProfile]:
        """List only built-in profiles."""
        return list(self._builtins.values())

    def list_custom(self) -> List[PublishingProfile]:
        """List only user-created profiles."""
        return list(self._custom.values())

    def create_profile(
        self,
        name: str,
        output_format: str = "docx",
        style_guide: str = "",
        template: str = "auto",
        special_instructions: str = "",
        font_family: str = "",
        font_size: str = "",
        line_spacing: float = 0.0,
    ) -> str:
        """Create a custom profile. Returns profile ID."""
        pid = uuid.uuid4().hex[:12]
        profile = PublishingProfile(
            id=pid,
            name=name,
            output_format=output_format,
            style_guide=style_guide,
            template=template,
            special_instructions=special_instructions,
            font_family=font_family,
            font_size=font_size,
            line_spacing=line_spacing,
            is_builtin=False,
        )
        self._custom[pid] = profile
        self._save(pid)
        logger.info("Created custom profile %s: %s", pid, name)
        return pid

    def update_profile(
        self,
        profile_id: str,
        **kwargs,
    ) -> Optional[PublishingProfile]:
        """Update a custom profile. Cannot update built-in profiles."""
        profile = self._custom.get(profile_id)
        if not profile:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key) and key not in ("id", "is_builtin", "created_at"):
                setattr(profile, key, value)

        profile.updated_at = time.time()
        self._save(profile_id)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a custom profile. Cannot delete built-in profiles."""
        if profile_id not in self._custom:
            return False
        del self._custom[profile_id]
        path = self._profile_path(profile_id)
        if path.exists():
            path.unlink()
        logger.info("Deleted custom profile %s", profile_id)
        return True

    def get_profile_for_format(self, output_format: str) -> Optional[PublishingProfile]:
        """Get default profile for an output format."""
        # Check custom first
        for p in self._custom.values():
            if p.output_format == output_format:
                return p
        # Then built-in
        for p in self._builtins.values():
            if p.output_format == output_format:
                return p
        return None

    # --- Persistence ---

    def _profile_path(self, profile_id: str) -> Path:
        return self._storage_dir / f"{profile_id}.json"

    def _save(self, profile_id: str) -> None:
        profile = self._custom.get(profile_id)
        if not profile:
            return
        try:
            path = self._profile_path(profile_id)
            path.write_text(
                json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save profile %s: %s", profile_id, exc)

    def _load_custom(self) -> None:
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                profile = PublishingProfile.from_dict(data)
                if not profile.is_builtin:
                    self._custom[profile.id] = profile
            except Exception as exc:
                logger.warning("Failed to load profile %s: %s", path, exc)

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    @property
    def builtin_count(self) -> int:
        return len(self._builtins)

    @property
    def custom_count(self) -> int:
        return len(self._custom)

    @property
    def total_count(self) -> int:
        return self.builtin_count + self.custom_count
