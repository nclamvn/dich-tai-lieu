#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Key Service

Handles API key generation, validation, and management.
"""

import os
import secrets
import hashlib
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Set
from contextlib import contextmanager

from passlib.context import CryptContext

from core.database import get_db_backend
from .models import APIKey, APIKeyCreate, APIKeyResponse, APIKeyInfo, APIKeyScope

logger = logging.getLogger(__name__)

# Password hashing for API keys
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)


class APIKeyService:
    """API Key management service."""

    # Key format: aip_<random_32_chars>
    KEY_PREFIX = "aip_"
    KEY_LENGTH = 32

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize service."""
        if db_path is None:
            db_path = Path("data/api_keys/keys.db")

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._backend = get_db_backend("keys", db_dir=db_path.parent)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        with self._backend.connection() as conn:
            yield conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    key_prefix TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    rate_limit TEXT DEFAULT '100/minute',
                    is_active INTEGER DEFAULT 1,
                    last_used REAL,
                    use_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    description TEXT,
                    allowed_ips TEXT,
                    UNIQUE(user_id, name)
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)")

    def _generate_key(self) -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)
        return f"{self.KEY_PREFIX}{random_part}"

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return pwd_context.hash(key)

    def _verify_key(self, plain_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return pwd_context.verify(plain_key, hashed_key)

    # ========================================================================
    # Key Management
    # ========================================================================

    def create_key(self, user_id: str, request: APIKeyCreate) -> APIKeyResponse:
        """
        Create a new API key.

        Returns:
            APIKeyResponse with the actual key (only shown once!)
        """
        import uuid

        # Generate key
        key = self._generate_key()
        key_prefix = key[:12]  # "aip_" + 8 chars
        key_hash = self._hash_key(key)

        # Parse scopes
        if request.scopes:
            scopes = {APIKeyScope(s) for s in request.scopes if s in [e.value for e in APIKeyScope]}
        else:
            scopes = APIKeyScope.default_scopes()

        # Calculate expiration
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

        key_id = str(uuid.uuid4())
        now = datetime.utcnow()

        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO api_keys (
                        id, user_id, name, key_prefix, key_hash,
                        scopes, rate_limit, created_at, expires_at,
                        description, allowed_ips
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key_id,
                    user_id,
                    request.name,
                    key_prefix,
                    key_hash,
                    json.dumps([s.value for s in scopes]),
                    request.rate_limit,
                    now.timestamp(),
                    expires_at.timestamp() if expires_at else None,
                    request.description,
                    json.dumps(request.allowed_ips) if request.allowed_ips else None,
                ))
            except sqlite3.IntegrityError:
                raise ValueError(f"API key with name '{request.name}' already exists")

        logger.info(f"Created API key '{request.name}' for user {user_id}")

        return APIKeyResponse(
            id=key_id,
            name=request.name,
            key=key,  # Only returned on creation!
            key_prefix=key_prefix,
            scopes=[s.value for s in scopes],
            rate_limit=request.rate_limit,
            created_at=now,
            expires_at=expires_at,
        )

    def validate_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the key object if valid.

        Returns:
            APIKey if valid, None otherwise
        """
        if not key.startswith(self.KEY_PREFIX):
            return None

        key_prefix = key[:12]

        with self._get_connection() as conn:
            # Find keys with matching prefix
            rows = conn.execute("""
                SELECT * FROM api_keys
                WHERE key_prefix = ? AND is_active = 1
            """, (key_prefix,)).fetchall()

            for row in rows:
                if self._verify_key(key, row["key_hash"]):
                    # Found matching key
                    api_key = self._row_to_key(row)

                    if not api_key.is_valid():
                        return None

                    # Update last used
                    conn.execute("""
                        UPDATE api_keys
                        SET last_used = ?, use_count = use_count + 1
                        WHERE id = ?
                    """, (datetime.utcnow().timestamp(), api_key.id))

                    return api_key

        return None

    def get_key(self, key_id: str, user_id: str) -> Optional[APIKey]:
        """Get API key by ID (only for the owning user)."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM api_keys
                WHERE id = ? AND user_id = ?
            """, (key_id, user_id)).fetchone()

            if row:
                return self._row_to_key(row)

        return None

    def list_keys(self, user_id: str) -> List[APIKeyInfo]:
        """List all API keys for a user."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)).fetchall()

            keys = []
            for row in rows:
                scopes = json.loads(row["scopes"])
                keys.append(APIKeyInfo(
                    id=row["id"],
                    name=row["name"],
                    key_prefix=row["key_prefix"],
                    scopes=scopes,
                    is_active=bool(row["is_active"]),
                    rate_limit=row["rate_limit"],
                    last_used=datetime.fromtimestamp(row["last_used"]) if row["last_used"] else None,
                    use_count=row["use_count"],
                    created_at=datetime.fromtimestamp(row["created_at"]),
                    expires_at=datetime.fromtimestamp(row["expires_at"]) if row["expires_at"] else None,
                    description=row["description"] or "",
                ))

            return keys

    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """Revoke (deactivate) an API key."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE api_keys
                SET is_active = 0
                WHERE id = ? AND user_id = ?
            """, (key_id, user_id))

            if conn.rowcount > 0:
                logger.info(f"Revoked API key {key_id} for user {user_id}")
                return True

        return False

    def delete_key(self, key_id: str, user_id: str) -> bool:
        """Permanently delete an API key."""
        with self._get_connection() as conn:
            conn.execute("""
                DELETE FROM api_keys
                WHERE id = ? AND user_id = ?
            """, (key_id, user_id))

            if conn.rowcount > 0:
                logger.info(f"Deleted API key {key_id} for user {user_id}")
                return True

        return False

    def regenerate_key(self, key_id: str, user_id: str) -> Optional[APIKeyResponse]:
        """Regenerate an API key (new key, same settings)."""
        key = self.get_key(key_id, user_id)
        if not key:
            return None

        # Generate new key
        new_key = self._generate_key()
        new_prefix = new_key[:12]
        new_hash = self._hash_key(new_key)

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE api_keys
                SET key_prefix = ?, key_hash = ?, use_count = 0
                WHERE id = ? AND user_id = ?
            """, (new_prefix, new_hash, key_id, user_id))

        logger.info(f"Regenerated API key {key_id} for user {user_id}")

        return APIKeyResponse(
            id=key_id,
            name=key.name,
            key=new_key,
            key_prefix=new_prefix,
            scopes=[s.value for s in key.scopes],
            rate_limit=key.rate_limit,
            created_at=key.created_at,
            expires_at=key.expires_at,
        )

    def _row_to_key(self, row) -> APIKey:
        """Convert database row to APIKey object."""
        scopes = {APIKeyScope(s) for s in json.loads(row["scopes"])}
        allowed_ips = json.loads(row["allowed_ips"]) if row["allowed_ips"] else []

        return APIKey(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            key_prefix=row["key_prefix"],
            key_hash=row["key_hash"],
            scopes=scopes,
            rate_limit=row["rate_limit"],
            is_active=bool(row["is_active"]),
            last_used=datetime.fromtimestamp(row["last_used"]) if row["last_used"] else None,
            use_count=row["use_count"],
            created_at=datetime.fromtimestamp(row["created_at"]),
            expires_at=datetime.fromtimestamp(row["expires_at"]) if row["expires_at"] else None,
            description=row["description"] or "",
            allowed_ips=allowed_ips,
        )


# Global instance
_service: Optional[APIKeyService] = None


def get_api_key_service() -> APIKeyService:
    """Get global API key service instance."""
    global _service
    if _service is None:
        _service = APIKeyService()
    return _service
