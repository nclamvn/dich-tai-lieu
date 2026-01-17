#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error Integration Module - Connects ErrorTracker to API and Core modules

This module provides decorators and helper functions to automatically
track errors across the application.
"""

import functools
import logging
from typing import Callable, Optional, Any
from .error_tracker import (
    get_error_tracker,
    ErrorSeverity,
    ErrorCategory,
    track_error as _track_error
)

logger = logging.getLogger(__name__)


# ============================================================================
# Error Category Detection
# ============================================================================

def detect_error_category(error: Exception) -> ErrorCategory:
    """Auto-detect error category from exception type."""
    error_type = type(error).__name__.lower()
    error_msg = str(error).lower()

    # API/Network errors
    if any(x in error_type for x in ['connection', 'timeout', 'http', 'request']):
        if 'timeout' in error_type or 'timeout' in error_msg:
            return ErrorCategory.TIMEOUT_ERROR
        return ErrorCategory.NETWORK_ERROR

    # Validation errors
    if any(x in error_type for x in ['validation', 'value', 'type', 'key']):
        return ErrorCategory.VALIDATION_ERROR

    # Database errors
    if any(x in error_type for x in ['database', 'sqlite', 'sql', 'integrity']):
        return ErrorCategory.DATABASE_ERROR

    # File system errors
    if any(x in error_type for x in ['file', 'io', 'permission', 'path', 'notfound']):
        return ErrorCategory.FILESYSTEM_ERROR

    # API provider errors
    if any(x in error_msg for x in ['openai', 'anthropic', 'api key', 'rate limit', 'quota']):
        return ErrorCategory.API_ERROR

    # Translation errors
    if any(x in error_msg for x in ['translation', 'translate', 'chunk', 'llm']):
        return ErrorCategory.TRANSLATION_ERROR

    # OCR errors
    if any(x in error_msg for x in ['ocr', 'mathpix', 'paddle', 'recognition']):
        return ErrorCategory.OCR_ERROR

    # Configuration errors
    if any(x in error_msg for x in ['config', 'setting', 'environment', 'env']):
        return ErrorCategory.CONFIGURATION_ERROR

    return ErrorCategory.UNKNOWN_ERROR


def detect_error_severity(error: Exception, category: ErrorCategory) -> ErrorSeverity:
    """Auto-detect error severity based on error type and category."""
    error_msg = str(error).lower()

    # Critical - system cannot function
    if category in [ErrorCategory.DATABASE_ERROR, ErrorCategory.CONFIGURATION_ERROR]:
        return ErrorSeverity.CRITICAL

    if any(x in error_msg for x in ['critical', 'fatal', 'crash', 'corrupt']):
        return ErrorSeverity.CRITICAL

    # High - major functionality affected
    if category in [ErrorCategory.API_ERROR, ErrorCategory.NETWORK_ERROR]:
        return ErrorSeverity.HIGH

    if any(x in error_msg for x in ['failed', 'unavailable', 'denied', 'forbidden']):
        return ErrorSeverity.HIGH

    # Low - minor issues
    if category == ErrorCategory.VALIDATION_ERROR:
        return ErrorSeverity.LOW

    if any(x in error_msg for x in ['warning', 'skip', 'fallback']):
        return ErrorSeverity.LOW

    # Default to medium
    return ErrorSeverity.MEDIUM


# ============================================================================
# Decorators for Automatic Error Tracking
# ============================================================================

def track_errors(
    module: str = "",
    severity: Optional[ErrorSeverity] = None,
    category: Optional[ErrorCategory] = None,
    reraise: bool = True
):
    """
    Decorator to automatically track errors in functions.

    Usage:
        @track_errors(module="api.jobs", category=ErrorCategory.API_ERROR)
        async def create_job(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _handle_error(e, func, module, severity, category, kwargs)
                if reraise:
                    raise
                return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _handle_error(e, func, module, severity, category, kwargs)
                if reraise:
                    raise
                return None

        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _handle_error(
    error: Exception,
    func: Callable,
    module: str,
    severity: Optional[ErrorSeverity],
    category: Optional[ErrorCategory],
    context: dict
):
    """Handle error tracking logic."""
    try:
        # Auto-detect if not specified
        detected_category = category or detect_error_category(error)
        detected_severity = severity or detect_error_severity(error, detected_category)

        # Extract context
        job_id = context.get('job_id') or context.get('job', {}).get('id')
        user_id = context.get('user_id') or context.get('session', {}).get('user_id')

        # Track the error
        _track_error(
            error=error,
            severity=detected_severity,
            category=detected_category,
            module=module or func.__module__,
            function=func.__name__,
            job_id=job_id,
            user_id=user_id,
            metadata={k: str(v)[:200] for k, v in context.items() if k not in ['password', 'token', 'key']}
        )

        logger.error(
            f"[ErrorTracker] {detected_severity.value.upper()}/{detected_category.value}: "
            f"{type(error).__name__} in {func.__name__}: {str(error)[:100]}"
        )
    except Exception as track_error:
        # Don't let tracking errors break the application
        logger.warning(f"Failed to track error: {track_error}")


def asyncio_iscoroutinefunction(func):
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ============================================================================
# Context Manager for Error Tracking
# ============================================================================

class ErrorTrackingContext:
    """
    Context manager for tracking errors in code blocks.

    Usage:
        with ErrorTrackingContext(module="batch_processor", job_id="123"):
            # Code that might raise errors
            process_job()
    """

    def __init__(
        self,
        module: str = "",
        function: str = "",
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        reraise: bool = True
    ):
        self.module = module
        self.function = function
        self.job_id = job_id
        self.user_id = user_id
        self.severity = severity
        self.category = category
        self.reraise = reraise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # Auto-detect if not specified
            detected_category = self.category or detect_error_category(exc_val)
            detected_severity = self.severity or detect_error_severity(exc_val, detected_category)

            try:
                _track_error(
                    error=exc_val,
                    severity=detected_severity,
                    category=detected_category,
                    module=self.module,
                    function=self.function,
                    job_id=self.job_id,
                    user_id=self.user_id
                )
            except Exception as e:
                logger.warning(f"Failed to track error in context: {e}")

            # Return False to reraise, True to suppress
            return not self.reraise
        return False


# ============================================================================
# Convenience Functions
# ============================================================================

def track_api_error(
    error: Exception,
    endpoint: str,
    method: str = "GET",
    job_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> int:
    """Track an API error with context."""
    return _track_error(
        error=error,
        severity=detect_error_severity(error, ErrorCategory.API_ERROR),
        category=ErrorCategory.API_ERROR,
        module="api",
        function=endpoint,
        job_id=job_id,
        user_id=user_id,
        metadata={"method": method, "endpoint": endpoint}
    )


def track_translation_error(
    error: Exception,
    job_id: str,
    chunk_index: Optional[int] = None,
    provider: Optional[str] = None
) -> int:
    """Track a translation error with context."""
    return _track_error(
        error=error,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.TRANSLATION_ERROR,
        module="core.translator",
        function="translate_chunk",
        job_id=job_id,
        metadata={"chunk_index": chunk_index, "provider": provider}
    )


def track_job_error(
    error: Exception,
    job_id: str,
    stage: str = "unknown"
) -> int:
    """Track a job processing error."""
    category = detect_error_category(error)
    return _track_error(
        error=error,
        severity=ErrorSeverity.HIGH,
        category=category,
        module="core.batch_processor",
        function=f"process_{stage}",
        job_id=job_id,
        metadata={"stage": stage}
    )


# ============================================================================
# Error Statistics Helper
# ============================================================================

def get_error_summary(hours: int = 24) -> dict:
    """Get error summary for dashboard."""
    tracker = get_error_tracker()
    stats = tracker.get_statistics(time_window_hours=hours)
    recent = tracker.get_recent_errors(limit=10)
    unresolved = tracker.get_unresolved_errors()

    return {
        "stats": stats,
        "recent_errors": [
            {
                "id": e.id,
                "type": e.error_type,
                "message": e.error_message[:100],
                "severity": e.severity.value,
                "category": e.category.value,
                "count": e.occurrence_count,
                "last_seen": e.last_seen,
                "resolved": e.resolved
            }
            for e in recent
        ],
        "unresolved_count": len(unresolved),
        "critical_count": len([e for e in unresolved if e.severity == ErrorSeverity.CRITICAL]),
        "high_count": len([e for e in unresolved if e.severity == ErrorSeverity.HIGH])
    }
