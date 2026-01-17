#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Key Models

Data models for API key management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Set
from enum import Enum


class APIKeyScope(str, Enum):
    """Available API key scopes (permissions)."""
    READ = "read"           # Read-only access
    TRANSLATE = "translate" # Translation operations
    UPLOAD = "upload"       # File upload
    DOWNLOAD = "download"   # Download outputs
    JOBS = "jobs"           # Job management
    GLOSSARY = "glossary"   # Glossary access
    TM = "tm"               # Translation memory
    ADMIN = "admin"         # Admin operations

    @classmethod
    def default_scopes(cls) -> Set["APIKeyScope"]:
        """Get default scopes for new API keys."""
        return {cls.READ, cls.TRANSLATE, cls.UPLOAD, cls.DOWNLOAD, cls.JOBS}

    @classmethod
    def all_scopes(cls) -> Set["APIKeyScope"]:
        """Get all available scopes."""
        return set(cls)


@dataclass
class APIKey:
    """API Key model."""
    id: Optional[str] = None
    user_id: str = ""
    name: str = ""

    # The actual key (only shown once on creation)
    key_prefix: str = ""  # First 8 chars for identification
    key_hash: str = ""    # bcrypt hash of full key

    # Permissions
    scopes: Set[APIKeyScope] = field(default_factory=APIKeyScope.default_scopes)

    # Rate limiting
    rate_limit: str = "100/minute"  # Per-key rate limit

    # Status
    is_active: bool = True
    last_used: Optional[datetime] = None
    use_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Metadata
    description: str = ""
    allowed_ips: List[str] = field(default_factory=list)  # IP whitelist

    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def has_scope(self, scope: APIKeyScope) -> bool:
        """Check if key has a specific scope."""
        return scope in self.scopes or APIKeyScope.ADMIN in self.scopes


@dataclass
class APIKeyCreate:
    """Request to create a new API key."""
    name: str
    description: str = ""
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = None
    rate_limit: str = "100/minute"
    allowed_ips: Optional[List[str]] = None


@dataclass
class APIKeyResponse:
    """Response after creating an API key."""
    id: str
    name: str
    key: str  # Full key (only shown once!)
    key_prefix: str
    scopes: List[str]
    rate_limit: str
    created_at: datetime
    expires_at: Optional[datetime]

    @property
    def key_display(self) -> str:
        """Display format for the key (masked)."""
        return f"{self.key_prefix}...{self.key[-4:]}"


@dataclass
class APIKeyInfo:
    """Public API key information (without the actual key)."""
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    rate_limit: str
    last_used: Optional[datetime]
    use_count: int
    created_at: datetime
    expires_at: Optional[datetime]
    description: str
