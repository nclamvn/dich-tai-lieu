#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Keys Management Router

Provides REST endpoints for managing API keys.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import get_current_active_user, User
from core.api_keys import (
    APIKeyService, get_api_key_service,
    APIKeyCreate, APIKeyScope
)

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    description: str = Field("", max_length=500, description="Key description")
    scopes: Optional[List[str]] = Field(
        None,
        description="Scopes (permissions). Default: read, translate, upload, download, jobs"
    )
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Expiration in days (1-365). None = never expires"
    )
    rate_limit: str = Field("100/minute", description="Rate limit for this key")
    allowed_ips: Optional[List[str]] = Field(None, description="IP whitelist")


class KeyResponse(BaseModel):
    """Response with full API key (only on creation)."""
    id: str
    name: str
    key: str
    key_prefix: str
    scopes: List[str]
    rate_limit: str
    created_at: str
    expires_at: Optional[str]
    message: str = "Save this key - it will not be shown again!"


class KeyInfoResponse(BaseModel):
    """API key information (without the actual key)."""
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    rate_limit: str
    last_used: Optional[str]
    use_count: int
    created_at: str
    expires_at: Optional[str]
    description: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=KeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateKeyRequest,
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """
    Create a new API key.

    **Important:** The full API key is only returned once. Save it securely!

    Available scopes:
    - `read`: Read-only access
    - `translate`: Translation operations
    - `upload`: File upload
    - `download`: Download outputs
    - `jobs`: Job management
    - `glossary`: Glossary access
    - `tm`: Translation memory
    """
    # Check if user has API access
    from core.usage import get_usage_tracker
    tracker = get_usage_tracker()
    if not tracker.has_feature(current_user.id, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access requires a Pro or higher plan"
        )

    try:
        key_create = APIKeyCreate(
            name=request.name,
            description=request.description,
            scopes=request.scopes,
            expires_in_days=request.expires_in_days,
            rate_limit=request.rate_limit,
            allowed_ips=request.allowed_ips,
        )

        result = service.create_key(current_user.id, key_create)

        return KeyResponse(
            id=result.id,
            name=result.name,
            key=result.key,
            key_prefix=result.key_prefix,
            scopes=result.scopes,
            rate_limit=result.rate_limit,
            created_at=result.created_at.isoformat(),
            expires_at=result.expires_at.isoformat() if result.expires_at else None,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[KeyInfoResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """List all API keys for the current user."""
    keys = service.list_keys(current_user.id)

    return [
        KeyInfoResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            rate_limit=k.rate_limit,
            last_used=k.last_used.isoformat() if k.last_used else None,
            use_count=k.use_count,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            description=k.description,
        )
        for k in keys
    ]


@router.get("/{key_id}", response_model=KeyInfoResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """Get details of a specific API key."""
    key = service.get_key(key_id, current_user.id)

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return KeyInfoResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=[s.value for s in key.scopes],
        is_active=key.is_active,
        rate_limit=key.rate_limit,
        last_used=key.last_used.isoformat() if key.last_used else None,
        use_count=key.use_count,
        created_at=key.created_at.isoformat(),
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        description=key.description,
    )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """Revoke (deactivate) an API key."""
    if not service.revoke_key(key_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return {"message": "API key revoked", "key_id": key_id}


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """Permanently delete an API key."""
    if not service.delete_key(key_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return {"message": "API key deleted", "key_id": key_id}


@router.post("/{key_id}/regenerate", response_model=KeyResponse)
async def regenerate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    service: APIKeyService = Depends(get_api_key_service)
):
    """
    Regenerate an API key.

    This creates a new key value while keeping the same settings.
    The old key will no longer work.
    """
    result = service.regenerate_key(key_id, current_user.id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return KeyResponse(
        id=result.id,
        name=result.name,
        key=result.key,
        key_prefix=result.key_prefix,
        scopes=result.scopes,
        rate_limit=result.rate_limit,
        created_at=result.created_at.isoformat(),
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
    )


@router.get("/scopes/available")
async def list_available_scopes():
    """List all available API key scopes."""
    return {
        "scopes": [
            {"name": s.value, "description": _get_scope_description(s)}
            for s in APIKeyScope
        ],
        "default_scopes": [s.value for s in APIKeyScope.default_scopes()]
    }


def _get_scope_description(scope: APIKeyScope) -> str:
    """Get description for a scope."""
    descriptions = {
        APIKeyScope.READ: "Read-only access to job status and results",
        APIKeyScope.TRANSLATE: "Start translation jobs",
        APIKeyScope.UPLOAD: "Upload files for translation",
        APIKeyScope.DOWNLOAD: "Download translated documents",
        APIKeyScope.JOBS: "Full job management (create, cancel, delete)",
        APIKeyScope.GLOSSARY: "Access and manage glossaries",
        APIKeyScope.TM: "Access translation memory",
        APIKeyScope.ADMIN: "Full administrative access",
    }
    return descriptions.get(scope, "")
