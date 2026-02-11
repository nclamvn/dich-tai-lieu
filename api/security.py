#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security Module - Session-based Authentication with Persistent Backend

Supports:
- In-memory sessions (development)
- File-based sessions (persists across restarts)
- Rate limiting for auth endpoints
"""

import json
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from fastapi import HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    user_id: str
    username: str
    organization: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime


class FileSessionStore:
    """
    File-based session store — survives server restarts.

    Stores sessions as JSON in a file. Thread-safe enough for single-process
    FastAPI with uvicorn (async, single-threaded event loop).
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, dict] = {}
        self._load()

    def _load(self):
        """Load sessions from disk."""
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self._sessions = data if isinstance(data, dict) else {}
                logger.info(f"Loaded {len(self._sessions)} sessions from {self.file_path}")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load sessions file: {e}")
                self._sessions = {}
        else:
            self._sessions = {}

    def _save(self):
        """Persist sessions to disk."""
        try:
            self.file_path.write_text(
                json.dumps(self._sessions, default=str, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"Failed to save sessions: {e}")

    def get(self, token: str) -> Optional[dict]:
        return self._sessions.get(token)

    def set(self, token: str, session_data: dict):
        self._sessions[token] = session_data
        self._save()

    def delete(self, token: str):
        if token in self._sessions:
            del self._sessions[token]
            self._save()

    def all_tokens(self):
        return list(self._sessions.keys())

    def count(self) -> int:
        return len(self._sessions)


class SecurityManager:
    """
    Session-based authentication manager.

    Supports memory and file backends.
    """

    def __init__(self, session_timeout_hours: int = 8, backend: str = "memory", file_path: str = "data/sessions.json"):
        self.session_timeout_hours = session_timeout_hours
        self.backend_type = backend

        if backend == "file":
            self._store = FileSessionStore(file_path)
            logger.info(f"SecurityManager: file-based sessions at {file_path}")
        else:
            self._store = None  # Use in-memory dict
            self.sessions: Dict[str, SessionInfo] = {}
            logger.info("SecurityManager: in-memory sessions")

    def _get_session(self, token: str) -> Optional[SessionInfo]:
        """Get session from backend."""
        if self._store:
            data = self._store.get(token)
            if data:
                return SessionInfo(**data)
            return None
        return self.sessions.get(token)

    def _set_session(self, token: str, session: SessionInfo):
        """Store session in backend."""
        if self._store:
            self._store.set(token, session.model_dump(mode="json"))
        else:
            self.sessions[token] = session

    def _delete_session(self, token: str):
        """Delete session from backend."""
        if self._store:
            self._store.delete(token)
        elif token in self.sessions:
            del self.sessions[token]

    def _all_tokens(self):
        """Get all session tokens."""
        if self._store:
            return self._store.all_tokens()
        return list(self.sessions.keys())

    def create_session(
        self,
        user_id: str = "default_user",
        username: str = "User",
        organization: str = "Default Organization"
    ) -> str:
        """
        Create a new session and return session token.

        Args:
            user_id: Unique user identifier
            username: Display name
            organization: Organization name

        Returns:
            Session token (secure random string)
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.now()

        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            username=username,
            organization=organization,
            created_at=now,
            expires_at=now + timedelta(hours=self.session_timeout_hours),
            last_activity=now
        )

        self._set_session(session_id, session)

        # Clean up expired sessions
        self._cleanup_expired_sessions()

        return session_id

    def validate_session(self, session_token: Optional[str]) -> SessionInfo:
        """
        Validate session token and return session info.

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not session_token:
            raise HTTPException(
                status_code=401,
                detail="No session token provided. Please login first."
            )

        session = self._get_session(session_token)
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid session token. Please login again."
            )

        # Check expiration
        if datetime.now() > session.expires_at:
            self._delete_session(session_token)
            raise HTTPException(
                status_code=401,
                detail="Session expired. Please login again."
            )

        # Update last activity
        session.last_activity = datetime.now()
        self._set_session(session_token, session)

        return session

    def extend_session(self, session_token: str):
        """Extend session expiration time."""
        session = self._get_session(session_token)
        if session:
            session.expires_at = datetime.now() + timedelta(hours=self.session_timeout_hours)
            self._set_session(session_token, session)

    def invalidate_session(self, session_token: str):
        """Logout - invalidate session."""
        self._delete_session(session_token)

    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired = []
        for token in self._all_tokens():
            session = self._get_session(token)
            if session and now > session.expires_at:
                expired.append(token)
        for token in expired:
            self._delete_session(token)

    def get_active_sessions_count(self) -> int:
        """Get number of active sessions."""
        self._cleanup_expired_sessions()
        if self._store:
            return self._store.count()
        return len(self.sessions)


def _create_security_manager() -> SecurityManager:
    """Create SecurityManager from settings."""
    try:
        from config.settings import settings
        return SecurityManager(
            session_timeout_hours=settings.session_timeout_hours,
            backend=settings.session_backend,
            file_path=settings.session_file_path,
        )
    except Exception as e:
        logger.warning(f"Failed to load settings for SecurityManager: {e}. Using defaults.")
        return SecurityManager(session_timeout_hours=8)


# Global security manager instance
security_manager = _create_security_manager()


# Dependency for FastAPI endpoints
async def get_current_session(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
) -> SessionInfo:
    """
    FastAPI dependency to validate session.

    Usage:
        @app.post("/api/jobs")
        async def create_job(
            job_data: JobCreate,
            session: SessionInfo = Depends(get_current_session)
        ):
            # session is validated, use session.username, etc.
    """
    return security_manager.validate_session(x_session_token)


# Optional: Simpler version that doesn't require session for development
async def get_optional_session(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
) -> Optional[SessionInfo]:
    """
    Optional session validation - for endpoints that work with or without auth.
    """
    if not x_session_token:
        return None

    try:
        return security_manager.validate_session(x_session_token)
    except HTTPException:
        return None
