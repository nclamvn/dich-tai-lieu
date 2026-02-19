"""
Health check and monitoring endpoints.
"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.4.0",
        "timestamp": time.time()
    }


@router.get("/api/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with all system components.

    Returns comprehensive health status including:
    - System resources (CPU, memory, disk)
    - Database connectivity
    - Storage availability
    - API provider configuration
    """
    try:
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        health_status = monitor.check_health()

        return {
            "status": health_status.status,
            "timestamp": health_status.timestamp,
            "uptime_seconds": health_status.uptime_seconds,
            "components": health_status.components
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


@router.get("/api/monitoring/costs")
async def get_cost_metrics(time_period_hours: int = 24):
    """
    Get cost tracking metrics.

    Args:
        time_period_hours: Time window in hours (default 24)

    Returns:
        Cost metrics including total tokens, cost in USD, breakdown by provider/model
    """
    try:
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        cost_metrics = monitor.get_cost_metrics(time_period_hours)

        return {
            "total_tokens_used": cost_metrics.total_tokens_used,
            "total_cost_usd": cost_metrics.total_cost_usd,
            "cost_by_provider": cost_metrics.cost_by_provider,
            "cost_by_model": cost_metrics.cost_by_model,
            "average_cost_per_job": cost_metrics.average_cost_per_job,
            "jobs_processed": cost_metrics.jobs_processed,
            "time_period": cost_metrics.time_period
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost metrics: {str(e)}")


@router.get("/api/monitoring/errors")
async def get_error_stats(time_period_hours: int = 24):
    """
    Get error tracking statistics.

    Args:
        time_period_hours: Time window in hours (default 24)

    Returns:
        Error statistics including severity and category breakdowns
    """
    try:
        from core.error_tracker import get_error_tracker
        tracker = get_error_tracker()
        stats = tracker.get_statistics(time_period_hours)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error stats: {str(e)}")


@router.get("/api/monitoring/errors/recent")
async def get_recent_errors(limit: int = 50, severity: Optional[str] = None):
    """
    Get recent error records.

    Args:
        limit: Maximum number of errors to return (default 50)
        severity: Filter by severity (low, medium, high, critical)

    Returns:
        List of recent error records
    """
    try:
        from core.error_tracker import get_error_tracker, ErrorSeverity
        tracker = get_error_tracker()

        severity_enum = None
        if severity:
            severity_enum = ErrorSeverity(severity.lower())

        errors = tracker.get_recent_errors(limit, severity_enum)

        return [
            {
                "id": err.id,
                "error_type": err.error_type,
                "error_message": err.error_message,
                "severity": err.severity.value,
                "category": err.category.value,
                "last_seen": err.last_seen,
                "occurrence_count": err.occurrence_count,
                "resolved": err.resolved
            }
            for err in errors
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent errors: {str(e)}")
