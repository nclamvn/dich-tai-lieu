#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error Dashboard API Router

Provides REST endpoints for error monitoring and management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime

from core.error_tracker import (
    get_error_tracker,
    ErrorTracker,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecord
)
from core.error_integration import get_error_summary

router = APIRouter(prefix="/api/errors", tags=["Error Monitoring"])


# ============================================================================
# Response Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Error record response."""
    id: int
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    severity: str
    category: str
    module: Optional[str] = None
    function: Optional[str] = None
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class ErrorStatsResponse(BaseModel):
    """Error statistics response."""
    time_window_hours: int
    total_unique_errors: int
    total_occurrences: int
    unresolved_count: int
    by_severity: dict
    by_category: dict


class ErrorSummaryResponse(BaseModel):
    """Error dashboard summary."""
    stats: ErrorStatsResponse
    recent_errors: List[dict]
    unresolved_count: int
    critical_count: int
    high_count: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/summary", response_model=ErrorSummaryResponse)
async def get_dashboard_summary(
    hours: int = Query(default=24, ge=1, le=168)
):
    """
    Get error dashboard summary.

    Returns:
    - Statistics for the time window
    - Recent errors (top 10)
    - Unresolved error counts by severity
    """
    summary = get_error_summary(hours)

    return ErrorSummaryResponse(
        stats=ErrorStatsResponse(**summary["stats"]),
        recent_errors=summary["recent_errors"],
        unresolved_count=summary["unresolved_count"],
        critical_count=summary["critical_count"],
        high_count=summary["high_count"]
    )


@router.get("/stats", response_model=ErrorStatsResponse)
async def get_error_stats(
    hours: int = Query(default=24, ge=1, le=720)
):
    """
    Get error statistics for a time window.

    Args:
        hours: Time window in hours (default: 24, max: 720 = 30 days)
    """
    tracker = get_error_tracker()
    stats = tracker.get_statistics(time_window_hours=hours)

    return ErrorStatsResponse(**stats)


@router.get("/recent", response_model=List[ErrorResponse])
async def get_recent_errors(
    limit: int = Query(default=50, ge=1, le=500),
    severity: Optional[str] = None
):
    """
    Get recent errors.

    Args:
        limit: Maximum number of errors to return
        severity: Filter by severity (low, medium, high, critical)
    """
    tracker = get_error_tracker()

    severity_filter = None
    if severity:
        try:
            severity_filter = ErrorSeverity(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity: {severity}. Must be: low, medium, high, critical"
            )

    errors = tracker.get_recent_errors(limit=limit, severity=severity_filter)

    return [_record_to_response(e) for e in errors]


@router.get("/unresolved", response_model=List[ErrorResponse])
async def get_unresolved_errors(
    category: Optional[str] = None
):
    """
    Get all unresolved errors.

    Args:
        category: Filter by category
    """
    tracker = get_error_tracker()

    category_filter = None
    if category:
        try:
            category_filter = ErrorCategory(category.lower())
        except ValueError:
            valid = [c.value for c in ErrorCategory]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category: {category}. Must be one of: {valid}"
            )

    errors = tracker.get_unresolved_errors(category=category_filter)

    return [_record_to_response(e) for e in errors]


@router.get("/{error_id}", response_model=ErrorResponse)
async def get_error(error_id: int):
    """
    Get error by ID.
    """
    tracker = get_error_tracker()
    error = tracker.get_error(error_id)

    if not error:
        raise HTTPException(
            status_code=404,
            detail=f"Error {error_id} not found"
        )

    return _record_to_response(error)


@router.post("/{error_id}/resolve")
async def resolve_error(
    error_id: int,
    notes: str = ""
):
    """
    Mark error as resolved.

    Args:
        error_id: Error ID to resolve
        notes: Resolution notes
    """
    tracker = get_error_tracker()

    # Check if error exists
    error = tracker.get_error(error_id)
    if not error:
        raise HTTPException(
            status_code=404,
            detail=f"Error {error_id} not found"
        )

    tracker.resolve_error(error_id, notes)

    return {
        "message": f"Error {error_id} marked as resolved",
        "error_id": error_id,
        "resolution_notes": notes
    }


@router.post("/{error_id}/unresolve")
async def unresolve_error(error_id: int):
    """
    Mark error as unresolved (reopen).
    """
    tracker = get_error_tracker()

    # Check if error exists
    error = tracker.get_error(error_id)
    if not error:
        raise HTTPException(
            status_code=404,
            detail=f"Error {error_id} not found"
        )

    # Update to unresolved
    cursor = tracker.conn.cursor()
    cursor.execute("""
        UPDATE errors SET resolved = 0, resolved_at = NULL, resolution_notes = ''
        WHERE id = ?
    """, (error_id,))
    tracker.conn.commit()

    return {
        "message": f"Error {error_id} reopened",
        "error_id": error_id
    }


@router.delete("/cleanup")
async def cleanup_old_errors(
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Clean up old resolved errors.

    Args:
        days: Remove resolved errors older than this many days
    """
    tracker = get_error_tracker()
    deleted = tracker.clear_old_errors(days=days)

    return {
        "message": f"Cleaned up {deleted} old errors",
        "deleted_count": deleted,
        "older_than_days": days
    }


@router.get("/categories/list")
async def list_categories():
    """
    List all error categories.
    """
    return {
        "categories": [
            {"value": c.value, "name": c.name}
            for c in ErrorCategory
        ]
    }


@router.get("/severities/list")
async def list_severities():
    """
    List all error severities.
    """
    return {
        "severities": [
            {"value": s.value, "name": s.name}
            for s in ErrorSeverity
        ]
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _record_to_response(record: ErrorRecord) -> ErrorResponse:
    """Convert ErrorRecord to ErrorResponse."""
    return ErrorResponse(
        id=record.id,
        error_type=record.error_type,
        error_message=record.error_message,
        stack_trace=record.stack_trace,
        severity=record.severity.value,
        category=record.category.value,
        module=record.module,
        function=record.function,
        job_id=record.job_id,
        user_id=record.user_id,
        first_seen=datetime.fromtimestamp(record.first_seen),
        last_seen=datetime.fromtimestamp(record.last_seen),
        occurrence_count=record.occurrence_count,
        resolved=record.resolved,
        resolved_at=datetime.fromtimestamp(record.resolved_at) if record.resolved_at else None,
        resolution_notes=record.resolution_notes
    )
