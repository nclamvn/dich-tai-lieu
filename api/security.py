#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security Module - Simple Session-based Authentication
Designed for internal deployment to organizations
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Header
from pydantic import BaseModel


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    user_id: str
    username: str
    organization: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime


class SecurityManager:
    """
    Simple session-based authentication manager

    Features:
    - Session token generation
    - Session validation
    - Automatic expiration
    - Activity tracking

    Usage:
        security = SecurityManager()
        token = security.create_session({"username": "admin"})
        user = security.validate_session(token)
    """

    def __init__(self, session_timeout_hours: int = 8):
        self.sessions: Dict[str, SessionInfo] = {}
        self.session_timeout_hours = session_timeout_hours

    def create_session(
        self,
        user_id: str = "default_user",
        username: str = "User",
        organization: str = "Default Organization"
    ) -> str:
        """
        Create a new session and return session token

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

        self.sessions[session_id] = session

        # Clean up expired sessions
        self._cleanup_expired_sessions()

        return session_id

    def validate_session(self, session_token: Optional[str]) -> SessionInfo:
        """
        Validate session token and return session info

        Args:
            session_token: Session token from client

        Returns:
            SessionInfo if valid

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not session_token:
            raise HTTPException(
                status_code=401,
                detail="No session token provided. Please login first."
            )

        if session_token not in self.sessions:
            raise HTTPException(
                status_code=401,
                detail="Invalid session token. Please login again."
            )

        session = self.sessions[session_token]

        # Check expiration
        if datetime.now() > session.expires_at:
            del self.sessions[session_token]
            raise HTTPException(
                status_code=401,
                detail="Session expired. Please login again."
            )

        # Update last activity
        session.last_activity = datetime.now()

        return session

    def extend_session(self, session_token: str):
        """Extend session expiration time"""
        if session_token in self.sessions:
            session = self.sessions[session_token]
            session.expires_at = datetime.now() + timedelta(hours=self.session_timeout_hours)

    def invalidate_session(self, session_token: str):
        """Logout - invalidate session"""
        if session_token in self.sessions:
            del self.sessions[session_token]

    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        now = datetime.now()
        expired = [
            token for token, session in self.sessions.items()
            if now > session.expires_at
        ]
        for token in expired:
            del self.sessions[token]

    def get_active_sessions_count(self) -> int:
        """Get number of active sessions"""
        self._cleanup_expired_sessions()
        return len(self.sessions)


# Global security manager instance
security_manager = SecurityManager(session_timeout_hours=8)


# Dependency for FastAPI endpoints
async def get_current_session(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
) -> SessionInfo:
    """
    FastAPI dependency to validate session

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
    Optional session validation - for endpoints that work with or without auth
    """
    if not x_session_token:
        return None

    try:
        return security_manager.validate_session(x_session_token)
    except HTTPException:
        return None
