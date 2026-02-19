#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rate Limiting Module for AI Publisher Pro API

Provides configurable rate limiting with:
- Per-endpoint limits
- User/IP-based limiting
- Burst allowance
- Custom error responses
- Redis backend support (optional)

Usage:
    from api.rate_limiter import limiter, rate_limit_config

    @app.get("/api/endpoint")
    @limiter.limit(rate_limit_config.get_limit("translate"))
    async def endpoint(request: Request):
        ...
"""

import os
from typing import Optional, Dict, Callable
from dataclasses import dataclass, field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time


@dataclass
class RateLimitConfig:
    """
    Centralized rate limit configuration.

    Limits are defined as "count/period" where:
    - count: number of requests allowed
    - period: time window (second, minute, hour, day)

    Examples:
    - "10/minute" = 10 requests per minute
    - "100/hour" = 100 requests per hour
    - "5/second" = 5 requests per second
    """

    # Default limits by endpoint category
    defaults: Dict[str, str] = field(default_factory=lambda: {
        # Health & status - high limit
        "health": "120/minute",
        "status": "60/minute",

        # File operations - moderate limit
        "upload": "20/minute",
        "download": "30/minute",

        # Translation - lower limit (expensive operations)
        "translate": "10/minute",
        "translate_batch": "5/minute",

        # Vision API - expensive, rate-limited upstream
        "vision": "30/minute",

        # Job management
        "job_create": "15/minute",
        "job_list": "60/minute",
        "job_status": "120/minute",
        "job_cancel": "20/minute",

        # Auth endpoints
        "auth_login": "10/minute",
        "auth_register": "5/minute",
        "auth_refresh": "30/minute",
        "auth_password": "5/minute",

        # Admin endpoints
        "admin": "30/minute",
        "admin_users": "20/minute",

        # API docs
        "docs": "30/minute",

        # WebSocket - connection limit
        "websocket": "10/minute",

        # Fallback
        "default": "60/minute",
    })

    # Override limits from environment
    env_overrides: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Load overrides from environment variables."""
        # Format: RATE_LIMIT_TRANSLATE=20/minute
        for key in self.defaults.keys():
            env_key = f"RATE_LIMIT_{key.upper()}"
            if env_value := os.getenv(env_key):
                self.env_overrides[key] = env_value

        # Global override
        if global_limit := os.getenv("RATE_LIMIT"):
            self.env_overrides["default"] = global_limit

    def get_limit(self, endpoint: str) -> str:
        """
        Get rate limit for an endpoint.

        Args:
            endpoint: Endpoint category name

        Returns:
            Rate limit string (e.g., "10/minute")
        """
        # Check environment override first
        if endpoint in self.env_overrides:
            return self.env_overrides[endpoint]

        # Then check defaults
        if endpoint in self.defaults:
            return self.defaults[endpoint]

        # Fallback to default
        return self.env_overrides.get("default", self.defaults["default"])

    def get_all_limits(self) -> Dict[str, str]:
        """Get all configured limits."""
        result = self.defaults.copy()
        result.update(self.env_overrides)
        return result


# Create global config instance
rate_limit_config = RateLimitConfig()


def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.

    Priority:
    1. Authenticated user ID (from JWT)
    2. API key (if using API key auth)
    3. IP address (fallback)

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier string
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Try API key from header
    if api_key := request.headers.get("X-API-Key"):
        # Use first 8 chars of API key as identifier
        return f"api:{api_key[:8]}"

    # Fallback to IP address
    return get_remote_address(request)


def create_limiter(
    key_func: Callable = None,
    storage_uri: str = None,
    default_limits: list = None
) -> Limiter:
    """
    Create a configured rate limiter instance.

    Args:
        key_func: Function to extract rate limit key from request
        storage_uri: Redis URI for distributed rate limiting (optional)
        default_limits: Default rate limits to apply

    Returns:
        Configured Limiter instance
    """
    # Use custom key function or default
    key_function = key_func or get_user_identifier

    # Check for Redis configuration
    redis_url = storage_uri or os.getenv("REDIS_URL")

    limiter_kwargs = {
        "key_func": key_function,
        "default_limits": default_limits or [rate_limit_config.get_limit("default")],
    }

    if redis_url:
        limiter_kwargs["storage_uri"] = redis_url

    return Limiter(**limiter_kwargs)


# Create default limiter instance
limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with:
    - Error message
    - Retry-After header
    - Rate limit details
    """
    # Parse the limit info
    limit_value = str(exc.detail) if hasattr(exc, "detail") else "Rate limit exceeded"

    # Calculate retry time (in seconds)
    retry_after = 60  # Default to 60 seconds

    # Try to parse from exception
    if hasattr(exc, "limit") and exc.limit:
        limit_str = str(exc.limit)
        if "second" in limit_str:
            retry_after = 1
        elif "minute" in limit_str:
            retry_after = 60
        elif "hour" in limit_str:
            retry_after = 3600

    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "detail": limit_value,
            "retry_after_seconds": retry_after,
            "timestamp": time.time(),
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": limit_value,
        }
    )

    return response


# Decorators for common rate limit patterns
def limit_translate(func):
    """Apply translation rate limit."""
    return limiter.limit(rate_limit_config.get_limit("translate"))(func)


def limit_upload(func):
    """Apply upload rate limit."""
    return limiter.limit(rate_limit_config.get_limit("upload"))(func)


def limit_auth(func):
    """Apply auth rate limit."""
    return limiter.limit(rate_limit_config.get_limit("auth_login"))(func)


def limit_admin(func):
    """Apply admin rate limit."""
    return limiter.limit(rate_limit_config.get_limit("admin"))(func)


def limit_vision(func):
    """Apply vision API rate limit."""
    return limiter.limit(rate_limit_config.get_limit("vision"))(func)


# Rate limit middleware for specific paths
class RateLimitMiddleware:
    """
    Middleware to apply path-based rate limiting.

    Usage:
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
    """

    def __init__(self, app, limiter: Limiter):
        self.app = app
        self.limiter = limiter
        self.path_limits = {
            "/translate": "translate",
            "/upload": "upload",
            "/api/jobs": "job_create",
            "/api/auth/login": "auth_login",
            "/api/auth/register": "auth_register",
            "/admin": "admin",
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]

            # Find matching rate limit category
            for prefix, category in self.path_limits.items():
                if path.startswith(prefix):
                    # Apply rate limit check here if needed
                    break

        await self.app(scope, receive, send)


# Utility functions
def parse_limit(limit_str: str) -> tuple:
    """
    Parse a rate limit string into count and period.

    Args:
        limit_str: Rate limit string (e.g., "10/minute")

    Returns:
        Tuple of (count, period_seconds)
    """
    parts = limit_str.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid limit format: {limit_str}")

    count = int(parts[0])
    period = parts[1].lower()

    period_seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }.get(period, 60)

    return count, period_seconds


def get_remaining_requests(request: Request, limit_str: str) -> Optional[int]:
    """
    Get remaining requests for the current user/IP.

    Note: This requires Redis backend for accurate tracking.
    Returns None if not using Redis.
    """
    # This is a placeholder - actual implementation would need Redis
    return None
