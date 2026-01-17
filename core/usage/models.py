#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage Tracking Models

Data models for tracking API usage per user.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class QuotaPlan(str, Enum):
    """Available quota plans."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class UserQuota:
    """User quota configuration."""
    plan: QuotaPlan = QuotaPlan.FREE

    # Monthly limits
    monthly_tokens: int = 100_000  # Input + output tokens
    monthly_jobs: int = 50
    monthly_pages: int = 500

    # Per-request limits
    max_file_size_mb: int = 10
    max_pages_per_job: int = 100
    max_concurrent_jobs: int = 2

    # Features
    priority_queue: bool = False
    advanced_ocr: bool = False
    custom_glossary: bool = False
    api_access: bool = False

    # Cost tracking
    monthly_budget_usd: float = 0.0

    @classmethod
    def get_plan_quota(cls, plan: QuotaPlan) -> "UserQuota":
        """Get quota configuration for a plan."""
        plans = {
            QuotaPlan.FREE: cls(
                plan=QuotaPlan.FREE,
                monthly_tokens=100_000,
                monthly_jobs=50,
                monthly_pages=500,
                max_file_size_mb=10,
                max_pages_per_job=50,
                max_concurrent_jobs=1,
            ),
            QuotaPlan.BASIC: cls(
                plan=QuotaPlan.BASIC,
                monthly_tokens=500_000,
                monthly_jobs=200,
                monthly_pages=2000,
                max_file_size_mb=25,
                max_pages_per_job=100,
                max_concurrent_jobs=3,
                custom_glossary=True,
            ),
            QuotaPlan.PRO: cls(
                plan=QuotaPlan.PRO,
                monthly_tokens=2_000_000,
                monthly_jobs=1000,
                monthly_pages=10000,
                max_file_size_mb=50,
                max_pages_per_job=500,
                max_concurrent_jobs=5,
                priority_queue=True,
                advanced_ocr=True,
                custom_glossary=True,
                api_access=True,
            ),
            QuotaPlan.ENTERPRISE: cls(
                plan=QuotaPlan.ENTERPRISE,
                monthly_tokens=10_000_000,
                monthly_jobs=10000,
                monthly_pages=100000,
                max_file_size_mb=100,
                max_pages_per_job=1000,
                max_concurrent_jobs=20,
                priority_queue=True,
                advanced_ocr=True,
                custom_glossary=True,
                api_access=True,
            ),
            QuotaPlan.UNLIMITED: cls(
                plan=QuotaPlan.UNLIMITED,
                monthly_tokens=999_999_999,
                monthly_jobs=999_999,
                monthly_pages=999_999,
                max_file_size_mb=500,
                max_pages_per_job=10000,
                max_concurrent_jobs=100,
                priority_queue=True,
                advanced_ocr=True,
                custom_glossary=True,
                api_access=True,
            ),
        }
        return plans.get(plan, plans[QuotaPlan.FREE])


@dataclass
class UsageRecord:
    """Single usage record."""
    id: Optional[str] = None
    user_id: str = ""

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    period: str = ""  # YYYY-MM format

    # Usage metrics
    job_id: Optional[str] = None
    operation: str = ""  # translate, upload, api_call, etc.

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Document metrics
    pages: int = 0
    characters: int = 0
    words: int = 0

    # Cost
    cost_usd: float = 0.0

    # Provider info
    provider: str = ""
    model: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageStats:
    """Aggregated usage statistics for a user."""
    user_id: str
    period: str  # YYYY-MM format

    # Totals
    total_jobs: int = 0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_pages: int = 0
    total_characters: int = 0
    total_words: int = 0
    total_cost_usd: float = 0.0

    # By operation
    jobs_by_operation: Dict[str, int] = field(default_factory=dict)
    tokens_by_operation: Dict[str, int] = field(default_factory=dict)

    # By provider
    jobs_by_provider: Dict[str, int] = field(default_factory=dict)
    tokens_by_provider: Dict[str, int] = field(default_factory=dict)
    cost_by_provider: Dict[str, float] = field(default_factory=dict)

    # Quota status
    quota: Optional[UserQuota] = None
    tokens_remaining: int = 0
    jobs_remaining: int = 0
    pages_remaining: int = 0
    quota_percent_used: float = 0.0

    # Time-based
    first_usage: Optional[datetime] = None
    last_usage: Optional[datetime] = None

    def calculate_remaining(self, quota: UserQuota) -> None:
        """Calculate remaining quota."""
        self.quota = quota
        self.tokens_remaining = max(0, quota.monthly_tokens - self.total_tokens)
        self.jobs_remaining = max(0, quota.monthly_jobs - self.total_jobs)
        self.pages_remaining = max(0, quota.monthly_pages - self.total_pages)

        # Calculate percentage used (based on most restrictive limit)
        token_percent = (self.total_tokens / quota.monthly_tokens * 100) if quota.monthly_tokens > 0 else 0
        jobs_percent = (self.total_jobs / quota.monthly_jobs * 100) if quota.monthly_jobs > 0 else 0
        pages_percent = (self.total_pages / quota.monthly_pages * 100) if quota.monthly_pages > 0 else 0

        self.quota_percent_used = max(token_percent, jobs_percent, pages_percent)

    def is_quota_exceeded(self) -> bool:
        """Check if any quota is exceeded."""
        if not self.quota:
            return False
        return (
            self.total_tokens >= self.quota.monthly_tokens or
            self.total_jobs >= self.quota.monthly_jobs or
            self.total_pages >= self.quota.monthly_pages
        )

    def can_start_job(self, estimated_tokens: int = 0, estimated_pages: int = 0) -> bool:
        """Check if user can start a new job."""
        if not self.quota:
            return True
        return (
            self.total_tokens + estimated_tokens <= self.quota.monthly_tokens and
            self.total_jobs < self.quota.monthly_jobs and
            self.total_pages + estimated_pages <= self.quota.monthly_pages
        )


@dataclass
class DailyUsage:
    """Daily usage breakdown."""
    date: str  # YYYY-MM-DD format
    jobs: int = 0
    tokens: int = 0
    pages: int = 0
    cost_usd: float = 0.0


@dataclass
class UsageReport:
    """Comprehensive usage report."""
    user_id: str
    period: str
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # Current period stats
    current_stats: Optional[UsageStats] = None

    # Daily breakdown
    daily_usage: list = field(default_factory=list)

    # Trends
    previous_period_stats: Optional[UsageStats] = None
    growth_percent: float = 0.0

    # Top operations
    top_operations: list = field(default_factory=list)
    top_providers: list = field(default_factory=list)
