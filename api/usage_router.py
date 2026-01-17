#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage API Router

Provides REST endpoints for usage tracking and quota management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

from core.auth import get_current_user, get_current_active_user, require_role, User, UserRole
from core.usage import (
    UsageTracker, get_usage_tracker,
    UsageStats, UserQuota, QuotaPlan
)

router = APIRouter(prefix="/api/usage", tags=["Usage & Quota"])


# ============================================================================
# Response Models
# ============================================================================

class QuotaResponse(BaseModel):
    """Quota information response."""
    plan: str
    monthly_tokens: int
    monthly_jobs: int
    monthly_pages: int
    max_file_size_mb: int
    max_pages_per_job: int
    max_concurrent_jobs: int
    priority_queue: bool
    advanced_ocr: bool
    custom_glossary: bool
    api_access: bool


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    user_id: str
    period: str
    total_jobs: int
    total_tokens: int
    total_pages: int
    total_cost_usd: float
    tokens_remaining: int
    jobs_remaining: int
    pages_remaining: int
    quota_percent_used: float
    quota: QuotaResponse


class QuotaCheckResponse(BaseModel):
    """Quota check response."""
    allowed: bool
    reason: Optional[str] = None
    remaining_tokens: int
    remaining_jobs: int
    remaining_pages: int


class SetPlanRequest(BaseModel):
    """Request to set user plan."""
    plan: str = Field(..., description="Plan name: free, basic, pro, enterprise, unlimited")


# ============================================================================
# User Endpoints
# ============================================================================

@router.get("/stats", response_model=UsageStatsResponse)
async def get_my_usage_stats(
    period: Optional[str] = Query(None, description="Period in YYYY-MM format"),
    current_user: User = Depends(get_current_active_user),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """
    Get current user's usage statistics.

    Returns usage for the specified period (defaults to current month).
    """
    stats = tracker.get_stats(current_user.id, period)
    quota = tracker.get_quota(current_user.id)

    return UsageStatsResponse(
        user_id=current_user.id,
        period=stats.period,
        total_jobs=stats.total_jobs,
        total_tokens=stats.total_tokens,
        total_pages=stats.total_pages,
        total_cost_usd=stats.total_cost_usd,
        tokens_remaining=stats.tokens_remaining,
        jobs_remaining=stats.jobs_remaining,
        pages_remaining=stats.pages_remaining,
        quota_percent_used=stats.quota_percent_used,
        quota=QuotaResponse(
            plan=quota.plan.value,
            monthly_tokens=quota.monthly_tokens,
            monthly_jobs=quota.monthly_jobs,
            monthly_pages=quota.monthly_pages,
            max_file_size_mb=quota.max_file_size_mb,
            max_pages_per_job=quota.max_pages_per_job,
            max_concurrent_jobs=quota.max_concurrent_jobs,
            priority_queue=quota.priority_queue,
            advanced_ocr=quota.advanced_ocr,
            custom_glossary=quota.custom_glossary,
            api_access=quota.api_access,
        )
    )


@router.get("/quota", response_model=QuotaResponse)
async def get_my_quota(
    current_user: User = Depends(get_current_active_user),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """Get current user's quota configuration."""
    quota = tracker.get_quota(current_user.id)

    return QuotaResponse(
        plan=quota.plan.value,
        monthly_tokens=quota.monthly_tokens,
        monthly_jobs=quota.monthly_jobs,
        monthly_pages=quota.monthly_pages,
        max_file_size_mb=quota.max_file_size_mb,
        max_pages_per_job=quota.max_pages_per_job,
        max_concurrent_jobs=quota.max_concurrent_jobs,
        priority_queue=quota.priority_queue,
        advanced_ocr=quota.advanced_ocr,
        custom_glossary=quota.custom_glossary,
        api_access=quota.api_access,
    )


@router.get("/check", response_model=QuotaCheckResponse)
async def check_quota(
    tokens: int = Query(0, description="Estimated tokens for operation"),
    pages: int = Query(0, description="Estimated pages for operation"),
    current_user: User = Depends(get_current_active_user),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """
    Check if user can perform an operation.

    Use this before starting a translation to verify quota.
    """
    result = tracker.check_quota(current_user.id, tokens, pages)

    return QuotaCheckResponse(
        allowed=result["allowed"],
        reason=result["reason"],
        remaining_tokens=result["remaining"]["tokens"],
        remaining_jobs=result["remaining"]["jobs"],
        remaining_pages=result["remaining"]["pages"],
    )


@router.get("/history")
async def get_usage_history(
    period: Optional[str] = Query(None, description="Period in YYYY-MM format"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """Get detailed usage history."""
    records = tracker.get_history(current_user.id, period, limit, offset)

    return {
        "user_id": current_user.id,
        "period": period,
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "operation": r.operation,
                "job_id": r.job_id,
                "tokens": r.total_tokens,
                "pages": r.pages,
                "cost_usd": r.cost_usd,
                "provider": r.provider,
                "model": r.model,
            }
            for r in records
        ]
    }


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/user/{user_id}/stats", response_model=UsageStatsResponse)
async def get_user_usage_stats(
    user_id: str,
    period: Optional[str] = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """[Admin] Get usage statistics for any user."""
    stats = tracker.get_stats(user_id, period)
    quota = tracker.get_quota(user_id)

    return UsageStatsResponse(
        user_id=user_id,
        period=stats.period,
        total_jobs=stats.total_jobs,
        total_tokens=stats.total_tokens,
        total_pages=stats.total_pages,
        total_cost_usd=stats.total_cost_usd,
        tokens_remaining=stats.tokens_remaining,
        jobs_remaining=stats.jobs_remaining,
        pages_remaining=stats.pages_remaining,
        quota_percent_used=stats.quota_percent_used,
        quota=QuotaResponse(
            plan=quota.plan.value,
            monthly_tokens=quota.monthly_tokens,
            monthly_jobs=quota.monthly_jobs,
            monthly_pages=quota.monthly_pages,
            max_file_size_mb=quota.max_file_size_mb,
            max_pages_per_job=quota.max_pages_per_job,
            max_concurrent_jobs=quota.max_concurrent_jobs,
            priority_queue=quota.priority_queue,
            advanced_ocr=quota.advanced_ocr,
            custom_glossary=quota.custom_glossary,
            api_access=quota.api_access,
        )
    )


@router.put("/admin/user/{user_id}/plan")
async def set_user_plan(
    user_id: str,
    request: SetPlanRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """[Admin] Set plan for a user."""
    try:
        plan = QuotaPlan(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {request.plan}. Valid plans: {[p.value for p in QuotaPlan]}"
        )

    tracker.set_plan(user_id, plan)

    return {
        "message": f"Plan updated to {plan.value}",
        "user_id": user_id,
        "plan": plan.value
    }


@router.get("/admin/summary")
async def get_usage_summary(
    period: Optional[str] = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    tracker: UsageTracker = Depends(get_usage_tracker)
):
    """[Admin] Get overall usage summary."""
    # This would aggregate across all users
    # For now, return placeholder
    return {
        "period": period or datetime.utcnow().strftime("%Y-%m"),
        "total_users_active": 0,
        "total_jobs": 0,
        "total_tokens": 0,
        "total_pages": 0,
        "total_cost_usd": 0.0,
        "message": "Implement aggregation query for full summary"
    }


# ============================================================================
# Plan Information
# ============================================================================

@router.get("/plans")
async def list_plans():
    """List available plans and their features."""
    plans = []
    for plan in QuotaPlan:
        quota = UserQuota.get_plan_quota(plan)
        plans.append({
            "name": plan.value,
            "monthly_tokens": quota.monthly_tokens,
            "monthly_jobs": quota.monthly_jobs,
            "monthly_pages": quota.monthly_pages,
            "max_file_size_mb": quota.max_file_size_mb,
            "max_pages_per_job": quota.max_pages_per_job,
            "max_concurrent_jobs": quota.max_concurrent_jobs,
            "features": {
                "priority_queue": quota.priority_queue,
                "advanced_ocr": quota.advanced_ocr,
                "custom_glossary": quota.custom_glossary,
                "api_access": quota.api_access,
            }
        })

    return {"plans": plans}
