#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage Tracker

High-level API for tracking and managing usage.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps

from .models import UsageRecord, UsageStats, UserQuota, QuotaPlan
from .database import UsageDatabase, get_usage_db

logger = logging.getLogger(__name__)


class UsageTracker:
    """High-level usage tracking API."""

    def __init__(self, db: Optional[UsageDatabase] = None):
        """Initialize tracker."""
        self.db = db or get_usage_db()

    # ========================================================================
    # Recording Usage
    # ========================================================================

    def record_job(
        self,
        user_id: str,
        job_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        pages: int = 0,
        characters: int = 0,
        words: int = 0,
        cost_usd: float = 0.0,
        provider: str = "",
        model: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a translation job."""
        record = UsageRecord(
            user_id=user_id,
            job_id=job_id,
            operation="translate",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pages=pages,
            characters=characters,
            words=words,
            cost_usd=cost_usd,
            provider=provider,
            model=model,
            metadata=metadata or {}
        )

        record_id = self.db.record_usage(record)
        logger.debug(f"Recorded job usage: {record_id} for user {user_id}")
        return record_id

    def record_api_call(
        self,
        user_id: str,
        operation: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record an API call."""
        record = UsageRecord(
            user_id=user_id,
            operation=operation,
            total_tokens=tokens,
            cost_usd=cost_usd,
            metadata=metadata or {}
        )

        return self.db.record_usage(record)

    def record_upload(
        self,
        user_id: str,
        pages: int = 0,
        characters: int = 0,
        file_size_bytes: int = 0,
        file_type: str = ""
    ) -> str:
        """Record a file upload."""
        record = UsageRecord(
            user_id=user_id,
            operation="upload",
            pages=pages,
            characters=characters,
            metadata={
                "file_size_bytes": file_size_bytes,
                "file_type": file_type
            }
        )

        return self.db.record_usage(record)

    # ========================================================================
    # Querying Usage
    # ========================================================================

    def get_stats(self, user_id: str, period: Optional[str] = None) -> UsageStats:
        """Get usage statistics for a user."""
        stats = self.db.get_user_stats(user_id, period)

        # Add quota information
        quota = self.db.get_user_quota(user_id)
        stats.calculate_remaining(quota)

        return stats

    def get_quota(self, user_id: str) -> UserQuota:
        """Get quota for a user."""
        return self.db.get_user_quota(user_id)

    def set_quota(self, user_id: str, quota: UserQuota) -> None:
        """Set quota for a user."""
        self.db.set_user_quota(user_id, quota)
        logger.info(f"Set quota for user {user_id}: {quota.plan.value}")

    def set_plan(self, user_id: str, plan: QuotaPlan) -> None:
        """Set a predefined plan for a user."""
        quota = UserQuota.get_plan_quota(plan)
        self.set_quota(user_id, quota)

    def get_history(
        self,
        user_id: str,
        period: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get usage history for a user."""
        return self.db.get_usage_records(user_id, period, limit, offset)

    # ========================================================================
    # Quota Checks
    # ========================================================================

    def check_quota(
        self,
        user_id: str,
        estimated_tokens: int = 0,
        estimated_pages: int = 0
    ) -> Dict[str, Any]:
        """
        Check if user can perform an operation.

        Returns:
            Dict with:
            - allowed: bool
            - reason: str (if not allowed)
            - remaining: Dict of remaining quotas
        """
        stats = self.get_stats(user_id)

        if stats.is_quota_exceeded():
            return {
                "allowed": False,
                "reason": "Monthly quota exceeded",
                "remaining": {
                    "tokens": stats.tokens_remaining,
                    "jobs": stats.jobs_remaining,
                    "pages": stats.pages_remaining
                }
            }

        if not stats.can_start_job(estimated_tokens, estimated_pages):
            return {
                "allowed": False,
                "reason": "Insufficient quota for this operation",
                "remaining": {
                    "tokens": stats.tokens_remaining,
                    "jobs": stats.jobs_remaining,
                    "pages": stats.pages_remaining
                }
            }

        return {
            "allowed": True,
            "reason": None,
            "remaining": {
                "tokens": stats.tokens_remaining,
                "jobs": stats.jobs_remaining,
                "pages": stats.pages_remaining
            }
        }

    def check_file_size(self, user_id: str, file_size_mb: float) -> bool:
        """Check if file size is within quota."""
        quota = self.get_quota(user_id)
        return file_size_mb <= quota.max_file_size_mb

    def check_page_count(self, user_id: str, page_count: int) -> bool:
        """Check if page count is within quota."""
        quota = self.get_quota(user_id)
        return page_count <= quota.max_pages_per_job

    def has_feature(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a feature."""
        quota = self.get_quota(user_id)
        feature_map = {
            "priority_queue": quota.priority_queue,
            "advanced_ocr": quota.advanced_ocr,
            "custom_glossary": quota.custom_glossary,
            "api_access": quota.api_access,
        }
        return feature_map.get(feature, False)


# Global instance
_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get global usage tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


# Decorator for tracking API calls
def track_usage(operation: str):
    """Decorator to track API call usage."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get user_id from request
            user_id = None
            request = kwargs.get("request")
            if request and hasattr(request.state, "user"):
                user_id = request.state.user.id

            result = await func(*args, **kwargs)

            # Record usage if we have a user
            if user_id:
                try:
                    tracker = get_usage_tracker()
                    tracker.record_api_call(user_id, operation)
                except Exception as e:
                    logger.warning(f"Failed to track usage: {e}")

            return result
        return wrapper
    return decorator
