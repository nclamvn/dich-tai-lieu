#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Key Middleware

FastAPI middleware and dependencies for API key authentication.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader

from .models import APIKey, APIKeyScope
from .service import APIKeyService, get_api_key_service
from core.auth.database import get_user_db

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    service: APIKeyService = Depends(get_api_key_service)
) -> Optional[APIKey]:
    """
    Dependency to extract and validate API key from header.

    Returns:
        APIKey if valid, None if no key provided
    """
    if not api_key:
        return None

    key = service.validate_key(api_key)

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return key


async def get_api_key_user(
    api_key: Optional[APIKey] = Depends(get_api_key)
):
    """
    Get the user associated with an API key.

    Returns the user if API key is valid, None otherwise.
    """
    if not api_key:
        return None

    db = get_user_db()
    user = db.get_user_by_id(api_key.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key user not found"
        )

    return user


def require_api_key(scope: Optional[APIKeyScope] = None):
    """
    Dependency factory that requires a valid API key.

    Args:
        scope: Optional required scope

    Usage:
        @app.get("/api/endpoint")
        async def endpoint(api_key: APIKey = Depends(require_api_key(APIKeyScope.TRANSLATE))):
            ...
    """
    async def dependency(
        api_key: Optional[APIKey] = Depends(get_api_key)
    ) -> APIKey:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        if scope and not api_key.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required scope: {scope.value}"
            )

        return api_key

    return dependency


class APIKeyMiddleware:
    """
    Middleware to process API key authentication.

    Adds api_key to request.state if valid key is provided.
    """

    def __init__(self, app, service: Optional[APIKeyService] = None):
        self.app = app
        self.service = service or get_api_key_service()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract headers
            headers = dict(scope.get("headers", []))
            api_key_value = headers.get(b"x-api-key", b"").decode()

            if api_key_value:
                api_key = self.service.validate_key(api_key_value)
                if api_key:
                    # Store in scope for later access
                    scope["state"] = scope.get("state", {})
                    scope["state"]["api_key"] = api_key
                    scope["state"]["api_key_user_id"] = api_key.user_id

        await self.app(scope, receive, send)


def check_ip_whitelist(api_key: APIKey, client_ip: str) -> bool:
    """
    Check if client IP is allowed for this API key.

    Returns True if:
    - No IP whitelist is set (allow all)
    - Client IP is in the whitelist
    """
    if not api_key.allowed_ips:
        return True

    return client_ip in api_key.allowed_ips
