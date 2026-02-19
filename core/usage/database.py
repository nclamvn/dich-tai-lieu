#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage Database

SQLite storage for usage tracking data.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from core.database import get_db_backend
from .models import UsageRecord, UsageStats, UserQuota, QuotaPlan

logger = logging.getLogger(__name__)


class UsageDatabase:
    """SQLite database for usage tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = Path("data/usage/usage.db")

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._backend = get_db_backend("usage", db_dir=db_path.parent)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        with self._backend.connection() as conn:
            yield conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Usage records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    period TEXT NOT NULL,
                    job_id TEXT,
                    operation TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    pages INTEGER DEFAULT 0,
                    characters INTEGER DEFAULT 0,
                    words INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    provider TEXT,
                    model TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)

            # User quotas table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_quotas (
                    user_id TEXT PRIMARY KEY,
                    plan TEXT DEFAULT 'free',
                    monthly_tokens INTEGER DEFAULT 100000,
                    monthly_jobs INTEGER DEFAULT 50,
                    monthly_pages INTEGER DEFAULT 500,
                    max_file_size_mb INTEGER DEFAULT 10,
                    max_pages_per_job INTEGER DEFAULT 100,
                    max_concurrent_jobs INTEGER DEFAULT 2,
                    priority_queue INTEGER DEFAULT 0,
                    advanced_ocr INTEGER DEFAULT 0,
                    custom_glossary INTEGER DEFAULT 0,
                    api_access INTEGER DEFAULT 0,
                    monthly_budget_usd REAL DEFAULT 0.0,
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)

            # Monthly aggregates table (for fast queries)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monthly_usage (
                    user_id TEXT NOT NULL,
                    period TEXT NOT NULL,
                    total_jobs INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_input_tokens INTEGER DEFAULT 0,
                    total_output_tokens INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    total_characters INTEGER DEFAULT 0,
                    total_words INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    first_usage REAL,
                    last_usage REAL,
                    updated_at REAL DEFAULT (strftime('%s', 'now')),
                    PRIMARY KEY (user_id, period)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_user_period ON usage_records(user_id, period)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_job ON usage_records(job_id)")

    def record_usage(self, record: UsageRecord) -> str:
        """Record a usage event."""
        import uuid

        if not record.id:
            record.id = str(uuid.uuid4())

        if not record.period:
            record.period = record.timestamp.strftime("%Y-%m")

        record.total_tokens = record.input_tokens + record.output_tokens

        with self._get_connection() as conn:
            # Insert record
            conn.execute("""
                INSERT INTO usage_records (
                    id, user_id, timestamp, period, job_id, operation,
                    input_tokens, output_tokens, total_tokens,
                    pages, characters, words, cost_usd,
                    provider, model, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.user_id,
                record.timestamp.timestamp(),
                record.period,
                record.job_id,
                record.operation,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.pages,
                record.characters,
                record.words,
                record.cost_usd,
                record.provider,
                record.model,
                json.dumps(record.metadata) if record.metadata else None
            ))

            # Update monthly aggregate
            conn.execute("""
                INSERT INTO monthly_usage (
                    user_id, period, total_jobs, total_tokens,
                    total_input_tokens, total_output_tokens,
                    total_pages, total_characters, total_words,
                    total_cost_usd, first_usage, last_usage
                ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, period) DO UPDATE SET
                    total_jobs = total_jobs + 1,
                    total_tokens = total_tokens + excluded.total_tokens,
                    total_input_tokens = total_input_tokens + excluded.total_input_tokens,
                    total_output_tokens = total_output_tokens + excluded.total_output_tokens,
                    total_pages = total_pages + excluded.total_pages,
                    total_characters = total_characters + excluded.total_characters,
                    total_words = total_words + excluded.total_words,
                    total_cost_usd = total_cost_usd + excluded.total_cost_usd,
                    last_usage = excluded.last_usage,
                    updated_at = strftime('%s', 'now')
            """, (
                record.user_id,
                record.period,
                record.total_tokens,
                record.input_tokens,
                record.output_tokens,
                record.pages,
                record.characters,
                record.words,
                record.cost_usd,
                record.timestamp.timestamp(),
                record.timestamp.timestamp()
            ))

        return record.id

    def get_user_stats(self, user_id: str, period: Optional[str] = None) -> UsageStats:
        """Get usage statistics for a user."""
        if period is None:
            period = datetime.utcnow().strftime("%Y-%m")

        with self._get_connection() as conn:
            # Get monthly aggregate
            row = conn.execute("""
                SELECT * FROM monthly_usage
                WHERE user_id = ? AND period = ?
            """, (user_id, period)).fetchone()

            if not row:
                return UsageStats(user_id=user_id, period=period)

            stats = UsageStats(
                user_id=user_id,
                period=period,
                total_jobs=row["total_jobs"],
                total_tokens=row["total_tokens"],
                total_input_tokens=row["total_input_tokens"],
                total_output_tokens=row["total_output_tokens"],
                total_pages=row["total_pages"],
                total_characters=row["total_characters"],
                total_words=row["total_words"],
                total_cost_usd=row["total_cost_usd"],
                first_usage=datetime.fromtimestamp(row["first_usage"]) if row["first_usage"] else None,
                last_usage=datetime.fromtimestamp(row["last_usage"]) if row["last_usage"] else None,
            )

            # Get breakdown by operation
            for row in conn.execute("""
                SELECT operation, COUNT(*) as count, SUM(total_tokens) as tokens
                FROM usage_records
                WHERE user_id = ? AND period = ?
                GROUP BY operation
            """, (user_id, period)).fetchall():
                stats.jobs_by_operation[row["operation"]] = row["count"]
                stats.tokens_by_operation[row["operation"]] = row["tokens"] or 0

            # Get breakdown by provider
            for row in conn.execute("""
                SELECT provider, COUNT(*) as count,
                       SUM(total_tokens) as tokens,
                       SUM(cost_usd) as cost
                FROM usage_records
                WHERE user_id = ? AND period = ? AND provider IS NOT NULL
                GROUP BY provider
            """, (user_id, period)).fetchall():
                if row["provider"]:
                    stats.jobs_by_provider[row["provider"]] = row["count"]
                    stats.tokens_by_provider[row["provider"]] = row["tokens"] or 0
                    stats.cost_by_provider[row["provider"]] = row["cost"] or 0.0

            return stats

    def get_user_quota(self, user_id: str) -> UserQuota:
        """Get quota configuration for a user."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_quotas WHERE user_id = ?", (user_id,)
            ).fetchone()

            if not row:
                # Return default free quota
                return UserQuota.get_plan_quota(QuotaPlan.FREE)

            return UserQuota(
                plan=QuotaPlan(row["plan"]),
                monthly_tokens=row["monthly_tokens"],
                monthly_jobs=row["monthly_jobs"],
                monthly_pages=row["monthly_pages"],
                max_file_size_mb=row["max_file_size_mb"],
                max_pages_per_job=row["max_pages_per_job"],
                max_concurrent_jobs=row["max_concurrent_jobs"],
                priority_queue=bool(row["priority_queue"]),
                advanced_ocr=bool(row["advanced_ocr"]),
                custom_glossary=bool(row["custom_glossary"]),
                api_access=bool(row["api_access"]),
                monthly_budget_usd=row["monthly_budget_usd"],
            )

    def set_user_quota(self, user_id: str, quota: UserQuota) -> None:
        """Set quota configuration for a user."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_quotas (
                    user_id, plan, monthly_tokens, monthly_jobs, monthly_pages,
                    max_file_size_mb, max_pages_per_job, max_concurrent_jobs,
                    priority_queue, advanced_ocr, custom_glossary, api_access,
                    monthly_budget_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan = excluded.plan,
                    monthly_tokens = excluded.monthly_tokens,
                    monthly_jobs = excluded.monthly_jobs,
                    monthly_pages = excluded.monthly_pages,
                    max_file_size_mb = excluded.max_file_size_mb,
                    max_pages_per_job = excluded.max_pages_per_job,
                    max_concurrent_jobs = excluded.max_concurrent_jobs,
                    priority_queue = excluded.priority_queue,
                    advanced_ocr = excluded.advanced_ocr,
                    custom_glossary = excluded.custom_glossary,
                    api_access = excluded.api_access,
                    monthly_budget_usd = excluded.monthly_budget_usd,
                    updated_at = strftime('%s', 'now')
            """, (
                user_id,
                quota.plan.value,
                quota.monthly_tokens,
                quota.monthly_jobs,
                quota.monthly_pages,
                quota.max_file_size_mb,
                quota.max_pages_per_job,
                quota.max_concurrent_jobs,
                int(quota.priority_queue),
                int(quota.advanced_ocr),
                int(quota.custom_glossary),
                int(quota.api_access),
                quota.monthly_budget_usd,
            ))

    def get_usage_records(
        self,
        user_id: str,
        period: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UsageRecord]:
        """Get usage records for a user."""
        with self._get_connection() as conn:
            if period:
                rows = conn.execute("""
                    SELECT * FROM usage_records
                    WHERE user_id = ? AND period = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, period, limit, offset)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM usage_records
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset)).fetchall()

            records = []
            for row in rows:
                records.append(UsageRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    timestamp=datetime.fromtimestamp(row["timestamp"]),
                    period=row["period"],
                    job_id=row["job_id"],
                    operation=row["operation"],
                    input_tokens=row["input_tokens"],
                    output_tokens=row["output_tokens"],
                    total_tokens=row["total_tokens"],
                    pages=row["pages"],
                    characters=row["characters"],
                    words=row["words"],
                    cost_usd=row["cost_usd"],
                    provider=row["provider"],
                    model=row["model"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                ))

            return records

    def close(self):
        """Close database connection."""
        pass  # Connections are closed after each operation


# Global instance
_usage_db: Optional[UsageDatabase] = None


def get_usage_db() -> UsageDatabase:
    """Get global usage database instance."""
    global _usage_db
    if _usage_db is None:
        _usage_db = UsageDatabase()
    return _usage_db
