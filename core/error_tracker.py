#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error Tracking System for AI Translator Pro

SQLite-based error tracking with categorization, deduplication, and reporting.
"""

import sqlite3
import hashlib
import traceback
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


# ============================================================================
# Constants & Configuration
# ============================================================================

ERROR_DB_PATH = Path("data/errors/error_tracker.db")
ERROR_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    API_ERROR = "api_error"           # API call failures
    VALIDATION_ERROR = "validation_error"  # Data validation
    TRANSLATION_ERROR = "translation_error"  # Translation process
    OCR_ERROR = "ocr_error"           # OCR failures
    DATABASE_ERROR = "database_error"  # Database operations
    FILESYSTEM_ERROR = "filesystem_error"  # File I/O errors
    NETWORK_ERROR = "network_error"    # Network/connectivity
    TIMEOUT_ERROR = "timeout_error"    # Timeout errors
    CONFIGURATION_ERROR = "config_error"  # Config/setup issues
    UNKNOWN_ERROR = "unknown"         # Unclassified


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ErrorRecord:
    """Error record for tracking."""
    id: Optional[int] = None
    error_hash: Optional[str] = None

    # Error details
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""

    # Classification
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR

    # Context
    module: str = ""
    function: str = ""
    job_id: Optional[str] = None
    user_id: Optional[str] = None

    # Occurrence tracking
    first_seen: float = 0.0
    last_seen: float = 0.0
    occurrence_count: int = 1

    # Status
    resolved: bool = False
    resolved_at: Optional[float] = None
    resolution_notes: str = ""

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Error Tracker
# ============================================================================

class ErrorTracker:
    """SQLite-based error tracking system."""

    def __init__(self, db_path: Path = ERROR_DB_PATH):
        """Initialize error tracker."""
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_hash TEXT UNIQUE NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                module TEXT,
                function TEXT,
                job_id TEXT,
                user_id TEXT,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                resolved BOOLEAN DEFAULT 0,
                resolved_at REAL,
                resolution_notes TEXT,
                metadata TEXT
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_hash ON errors(error_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_severity ON errors(severity)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON errors(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_resolved ON errors(resolved)
        """)

        self.conn.commit()

    def _generate_error_hash(self, error_type: str, error_message: str, module: str, function: str) -> str:
        """Generate unique hash for error deduplication."""
        content = f"{error_type}:{error_message}:{module}:{function}"
        return hashlib.md5(content.encode()).hexdigest()

    def track_error(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        module: str = "",
        function: str = "",
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Track an error occurrence.

        Args:
            error: Exception object
            severity: Error severity level
            category: Error category
            module: Module where error occurred
            function: Function where error occurred
            job_id: Associated job ID
            user_id: Associated user ID
            metadata: Additional metadata

        Returns:
            Error record ID
        """
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        error_hash = self._generate_error_hash(error_type, error_message, module, function)

        cursor = self.conn.cursor()

        # Check if error already exists
        cursor.execute("SELECT id, occurrence_count FROM errors WHERE error_hash = ?", (error_hash,))
        existing = cursor.fetchone()

        if existing:
            # Update existing error
            error_id = existing[0]
            new_count = existing[1] + 1
            cursor.execute("""
                UPDATE errors
                SET last_seen = ?, occurrence_count = ?
                WHERE id = ?
            """, (time.time(), new_count, error_id))
        else:
            # Insert new error
            cursor.execute("""
                INSERT INTO errors (
                    error_hash, error_type, error_message, stack_trace,
                    severity, category, module, function,
                    job_id, user_id, first_seen, last_seen, occurrence_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                error_hash, error_type, error_message, stack_trace,
                severity.value, category.value, module, function,
                job_id, user_id, time.time(), time.time(), 1
            ))
            error_id = cursor.lastrowid

        self.conn.commit()
        return error_id

    def get_error(self, error_id: int) -> Optional[ErrorRecord]:
        """Get error record by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM errors WHERE id = ?", (error_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_record(row)
        return None

    def get_recent_errors(self, limit: int = 50, severity: Optional[ErrorSeverity] = None) -> List[ErrorRecord]:
        """Get recent errors, optionally filtered by severity."""
        cursor = self.conn.cursor()

        if severity:
            cursor.execute("""
                SELECT * FROM errors
                WHERE severity = ?
                ORDER BY last_seen DESC
                LIMIT ?
            """, (severity.value, limit))
        else:
            cursor.execute("""
                SELECT * FROM errors
                ORDER BY last_seen DESC
                LIMIT ?
            """, (limit,))

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_unresolved_errors(self, category: Optional[ErrorCategory] = None) -> List[ErrorRecord]:
        """Get all unresolved errors, optionally filtered by category."""
        cursor = self.conn.cursor()

        if category:
            cursor.execute("""
                SELECT * FROM errors
                WHERE resolved = 0 AND category = ?
                ORDER BY last_seen DESC
            """, (category.value,))
        else:
            cursor.execute("""
                SELECT * FROM errors
                WHERE resolved = 0
                ORDER BY last_seen DESC
            """)

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def resolve_error(self, error_id: int, resolution_notes: str = ""):
        """Mark error as resolved."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE errors
            SET resolved = 1, resolved_at = ?, resolution_notes = ?
            WHERE id = ?
        """, (time.time(), resolution_notes, error_id))
        self.conn.commit()

    def get_statistics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for a time window."""
        cursor = self.conn.cursor()
        cutoff_time = time.time() - (time_window_hours * 3600)

        # Total errors in window
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(occurrence_count) as total_occurrences
            FROM errors
            WHERE last_seen >= ?
        """, (cutoff_time,))
        row = cursor.fetchone()
        total_unique = row[0]
        total_occurrences = row[1] or 0

        # By severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count, SUM(occurrence_count) as occurrences
            FROM errors
            WHERE last_seen >= ?
            GROUP BY severity
        """, (cutoff_time,))
        by_severity = {row[0]: {"unique": row[1], "occurrences": row[2]} for row in cursor.fetchall()}

        # By category
        cursor.execute("""
            SELECT category, COUNT(*) as count, SUM(occurrence_count) as occurrences
            FROM errors
            WHERE last_seen >= ?
            GROUP BY category
        """, (cutoff_time,))
        by_category = {row[0]: {"unique": row[1], "occurrences": row[2]} for row in cursor.fetchall()}

        # Unresolved count
        cursor.execute("""
            SELECT COUNT(*) FROM errors WHERE resolved = 0 AND last_seen >= ?
        """, (cutoff_time,))
        unresolved = cursor.fetchone()[0]

        return {
            "time_window_hours": time_window_hours,
            "total_unique_errors": total_unique,
            "total_occurrences": total_occurrences,
            "unresolved_count": unresolved,
            "by_severity": by_severity,
            "by_category": by_category,
        }

    def clear_old_errors(self, days: int = 30):
        """Clear errors older than specified days."""
        cursor = self.conn.cursor()
        cutoff_time = time.time() - (days * 24 * 3600)
        cursor.execute("DELETE FROM errors WHERE last_seen < ? AND resolved = 1", (cutoff_time,))
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    def _row_to_record(self, row: sqlite3.Row) -> ErrorRecord:
        """Convert database row to ErrorRecord."""
        return ErrorRecord(
            id=row['id'],
            error_hash=row['error_hash'],
            error_type=row['error_type'],
            error_message=row['error_message'],
            stack_trace=row['stack_trace'],
            severity=ErrorSeverity(row['severity']),
            category=ErrorCategory(row['category']),
            module=row['module'],
            function=row['function'],
            job_id=row['job_id'],
            user_id=row['user_id'],
            first_seen=row['first_seen'],
            last_seen=row['last_seen'],
            occurrence_count=row['occurrence_count'],
            resolved=bool(row['resolved']),
            resolved_at=row['resolved_at'],
            resolution_notes=row['resolution_notes'],
        )

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ============================================================================
# Global Instance & Convenience Functions
# ============================================================================

_global_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ErrorTracker()
    return _global_tracker


def track_error(
    error: Exception,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    **context
) -> int:
    """Track an error using the global tracker."""
    tracker = get_error_tracker()
    return tracker.track_error(error, severity, category, **context)


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example usage
    tracker = ErrorTracker()

    # Track errors
    try:
        raise ValueError("Test error #1")
    except Exception as e:
        tracker.track_error(
            e,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION_ERROR,
            module="test_module",
            function="test_function",
            job_id="job_123"
        )

    try:
        raise ConnectionError("API connection failed")
    except Exception as e:
        tracker.track_error(
            e,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.API_ERROR,
            module="api_client",
            function="call_api"
        )

    # Get statistics
    stats = tracker.get_statistics(time_window_hours=24)
    print("Error Statistics (24h):")
    print(f"  Total unique errors: {stats['total_unique_errors']}")
    print(f"  Total occurrences: {stats['total_occurrences']}")
    print(f"  Unresolved: {stats['unresolved_count']}")
    print(f"\nBy Severity: {stats['by_severity']}")
    print(f"By Category: {stats['by_category']}")

    # Get recent errors
    recent = tracker.get_recent_errors(limit=10)
    print(f"\nRecent Errors: {len(recent)}")
    for err in recent:
        print(f"  - [{err.severity.value}] {err.error_type}: {err.error_message[:50]}...")

    print("\n✅ Error tracking system initialized successfully!")
    print(f"📁 Database location: {ERROR_DB_PATH.absolute()}")
