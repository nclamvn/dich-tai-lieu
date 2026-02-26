"""
RRI-T Sprint 5: Error Tracker + Health Monitor tests.

Persona coverage: DevOps, QA Destroyer, Business Analyst
Dimensions: D5 (Data Integrity), D6 (Infrastructure), D3 (Performance)
"""

import tempfile
import time
from pathlib import Path

import pytest

from core.error_tracker import (
    ErrorTracker, ErrorRecord, ErrorSeverity, ErrorCategory,
)
from core.health_monitor import HealthMonitor, HealthStatus, CostMetrics


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker(tmp_path):
    db_path = tmp_path / "test_errors.db"
    t = ErrorTracker(db_path=db_path)
    yield t
    t.close()


# ===========================================================================
# MON-001: Error tracking & deduplication
# ===========================================================================

class TestErrorTracking:
    """DevOps persona — error tracking accuracy."""

    @pytest.mark.p0
    def test_mon_001_track_error_returns_id(self, tracker):
        """MON-001 | DevOps | track_error returns positive integer ID"""
        err_id = tracker.track_error(
            ValueError("test error"),
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION_ERROR,
            module="test_module",
            function="test_func",
        )
        assert isinstance(err_id, int)
        assert err_id > 0

    @pytest.mark.p0
    def test_mon_001b_get_tracked_error(self, tracker):
        """MON-001b | DevOps | Tracked error retrievable by ID"""
        err_id = tracker.track_error(
            RuntimeError("db connection failed"),
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE_ERROR,
            module="core.db",
            function="connect",
        )
        record = tracker.get_error(err_id)
        assert record is not None
        assert record.error_type == "RuntimeError"
        assert "db connection failed" in record.error_message
        assert record.severity == ErrorSeverity.CRITICAL
        assert record.category == ErrorCategory.DATABASE_ERROR

    @pytest.mark.p0
    def test_mon_001c_deduplication(self, tracker):
        """MON-001c | DevOps | Same error tracked twice -> count incremented"""
        err = ValueError("duplicate error")
        id1 = tracker.track_error(err, module="m", function="f")
        id2 = tracker.track_error(err, module="m", function="f")
        assert id1 == id2  # Same error returns same ID

        record = tracker.get_error(id1)
        assert record.occurrence_count == 2

    @pytest.mark.p1
    def test_mon_001d_different_errors_different_ids(self, tracker):
        """MON-001d | DevOps | Different errors get different IDs"""
        id1 = tracker.track_error(ValueError("error A"), module="m", function="f")
        id2 = tracker.track_error(TypeError("error B"), module="m", function="f")
        assert id1 != id2

    @pytest.mark.p1
    def test_mon_001e_nonexistent_error_returns_none(self, tracker):
        """MON-001e | QA | get_error with invalid ID -> None"""
        assert tracker.get_error(99999) is None


# ===========================================================================
# MON-002: Error filtering & resolution
# ===========================================================================

class TestErrorFiltering:
    """DevOps persona — error triage."""

    @pytest.mark.p0
    def test_mon_002_recent_errors_ordered(self, tracker):
        """MON-002 | DevOps | get_recent_errors returns newest first"""
        tracker.track_error(ValueError("old"), module="m", function="f")
        tracker.track_error(TypeError("new"), module="m", function="f")

        recent = tracker.get_recent_errors(limit=10)
        assert len(recent) == 2
        assert recent[0].last_seen >= recent[1].last_seen

    @pytest.mark.p1
    def test_mon_002b_filter_by_severity(self, tracker):
        """MON-002b | DevOps | Filter recent errors by severity"""
        tracker.track_error(
            ValueError("low err"), severity=ErrorSeverity.LOW,
            module="m", function="f",
        )
        tracker.track_error(
            RuntimeError("critical err"), severity=ErrorSeverity.CRITICAL,
            module="m", function="f",
        )

        critical = tracker.get_recent_errors(severity=ErrorSeverity.CRITICAL)
        assert all(r.severity == ErrorSeverity.CRITICAL for r in critical)
        assert len(critical) == 1

    @pytest.mark.p0
    def test_mon_002c_resolve_error(self, tracker):
        """MON-002c | DevOps | Resolved errors marked correctly"""
        err_id = tracker.track_error(ValueError("fixme"), module="m", function="f")
        tracker.resolve_error(err_id, "Fixed in PR #123")

        record = tracker.get_error(err_id)
        assert record.resolved is True
        assert record.resolution_notes == "Fixed in PR #123"

    @pytest.mark.p1
    def test_mon_002d_unresolved_filter(self, tracker):
        """MON-002d | DevOps | get_unresolved_errors excludes resolved"""
        id1 = tracker.track_error(ValueError("open"), module="m", function="f1")
        id2 = tracker.track_error(TypeError("closed"), module="m", function="f2")
        tracker.resolve_error(id2, "Done")

        unresolved = tracker.get_unresolved_errors()
        ids = [r.id for r in unresolved]
        assert id1 in ids
        assert id2 not in ids

    @pytest.mark.p1
    def test_mon_002e_unresolved_filter_by_category(self, tracker):
        """MON-002e | DevOps | Filter unresolved by category"""
        tracker.track_error(
            ValueError("api err"), category=ErrorCategory.API_ERROR,
            module="m", function="f1",
        )
        tracker.track_error(
            RuntimeError("db err"), category=ErrorCategory.DATABASE_ERROR,
            module="m", function="f2",
        )

        api_errors = tracker.get_unresolved_errors(category=ErrorCategory.API_ERROR)
        assert len(api_errors) == 1
        assert api_errors[0].category == ErrorCategory.API_ERROR


# ===========================================================================
# MON-003: Statistics & cleanup
# ===========================================================================

class TestErrorStatistics:
    """Business Analyst persona — error analytics."""

    @pytest.mark.p0
    def test_mon_003_statistics_structure(self, tracker):
        """MON-003 | BA | get_statistics returns all expected keys"""
        tracker.track_error(ValueError("stat test"), module="m", function="f")

        stats = tracker.get_statistics(time_window_hours=24)
        assert "time_window_hours" in stats
        assert "total_unique_errors" in stats
        assert "total_occurrences" in stats
        assert "unresolved_count" in stats
        assert "by_severity" in stats
        assert "by_category" in stats

    @pytest.mark.p1
    def test_mon_003b_statistics_count_accuracy(self, tracker):
        """MON-003b | BA | Statistics counts match tracked errors"""
        err = ValueError("counted")
        tracker.track_error(err, module="m", function="f")
        tracker.track_error(err, module="m", function="f")  # dup -> count=2
        tracker.track_error(TypeError("other"), module="m", function="g")

        stats = tracker.get_statistics(time_window_hours=24)
        assert stats["total_unique_errors"] == 2
        assert stats["total_occurrences"] == 3  # 2 + 1

    @pytest.mark.p1
    def test_mon_003c_clear_old_resolved(self, tracker):
        """MON-003c | DevOps | clear_old_errors removes old resolved only"""
        err_id = tracker.track_error(ValueError("old"), module="m", function="f")
        tracker.resolve_error(err_id, "done")

        # Manually backdate the error
        with tracker._backend.connection() as conn:
            old_time = time.time() - (60 * 86400)  # 60 days ago
            conn.execute(
                "UPDATE errors SET last_seen = ? WHERE id = ?",
                (old_time, err_id),
            )

        deleted = tracker.clear_old_errors(days=30)
        assert deleted == 1
        assert tracker.get_error(err_id) is None

    @pytest.mark.p1
    def test_mon_003d_empty_stats(self, tracker):
        """MON-003d | QA | Statistics on empty DB -> zero counts"""
        stats = tracker.get_statistics()
        assert stats["total_unique_errors"] == 0
        assert stats["total_occurrences"] == 0


# ===========================================================================
# MON-004: Error enums completeness
# ===========================================================================

class TestErrorEnums:
    """Business Analyst persona — data model validation."""

    @pytest.mark.p0
    def test_mon_004_severity_enum(self):
        """MON-004 | BA | ErrorSeverity has all levels"""
        expected = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        for level in expected:
            assert hasattr(ErrorSeverity, level)

    @pytest.mark.p0
    def test_mon_004b_category_enum(self):
        """MON-004b | BA | ErrorCategory has all categories"""
        expected = [
            "API_ERROR", "VALIDATION_ERROR", "TRANSLATION_ERROR",
            "OCR_ERROR", "DATABASE_ERROR", "FILESYSTEM_ERROR",
            "NETWORK_ERROR", "TIMEOUT_ERROR", "CONFIGURATION_ERROR",
            "UNKNOWN_ERROR",
        ]
        for cat in expected:
            assert hasattr(ErrorCategory, cat)

    @pytest.mark.p1
    def test_mon_004c_severity_values_lowercase(self):
        """MON-004c | BA | Severity values are lowercase strings"""
        for sev in ErrorSeverity:
            assert isinstance(sev.value, str)
            assert sev.value == sev.value.lower()


# ===========================================================================
# MON-005: Health Monitor
# ===========================================================================

class TestHealthMonitor:
    """DevOps persona — system health monitoring."""

    @pytest.mark.p0
    def test_mon_005_health_check_structure(self):
        """MON-005 | DevOps | check_health returns HealthStatus"""
        monitor = HealthMonitor()
        health = monitor.check_health()
        assert isinstance(health, HealthStatus)
        assert health.status in ("healthy", "degraded", "unhealthy")
        assert health.uptime_seconds >= 0
        assert "system" in health.components

    @pytest.mark.p1
    def test_mon_005b_system_resources(self):
        """MON-005b | DevOps | System resources reported"""
        monitor = HealthMonitor()
        resources = monitor._check_system_resources()
        assert "status" in resources
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources

    @pytest.mark.p0
    def test_mon_005c_cost_metrics_structure(self):
        """MON-005c | BA | CostMetrics dataclass has expected fields"""
        metrics = CostMetrics(
            total_tokens_used=1000,
            total_cost_usd=0.05,
            cost_by_provider={"openai": 0.05},
            cost_by_model={"gpt-4o-mini": 0.05},
            average_cost_per_job=0.05,
            jobs_processed=1,
            time_period="24h",
        )
        assert metrics.total_tokens_used == 1000
        assert metrics.total_cost_usd == 0.05
        assert metrics.jobs_processed == 1

    @pytest.mark.p1
    def test_mon_005d_cost_metrics_no_analytics_db(self):
        """MON-005d | DevOps | Cost metrics graceful when no analytics DB"""
        monitor = HealthMonitor()
        metrics = monitor.get_cost_metrics(time_period_hours=24)
        assert isinstance(metrics, CostMetrics)
        assert metrics.total_cost_usd >= 0
        assert metrics.jobs_processed >= 0
