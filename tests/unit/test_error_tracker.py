"""Tests for ErrorTracker."""

import pytest
from pathlib import Path

from core.error_tracker import (
    ErrorTracker,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecord,
)


@pytest.fixture
def tracker(tmp_path):
    db_path = tmp_path / "errors.db"
    t = ErrorTracker(db_path=db_path)
    yield t
    t.close()


class TestErrorTracker:

    def test_track_error(self, tracker):
        try:
            raise ValueError("test error")
        except Exception as e:
            error_id = tracker.track_error(
                e,
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.VALIDATION_ERROR,
                module="test_module",
                function="test_func",
            )
        assert error_id is not None
        assert error_id > 0

    def test_get_error(self, tracker):
        try:
            raise RuntimeError("something broke")
        except Exception as e:
            error_id = tracker.track_error(e)

        record = tracker.get_error(error_id)
        assert record is not None
        assert record.error_type == "RuntimeError"
        assert "something broke" in record.error_message

    def test_deduplication(self, tracker):
        for _ in range(3):
            try:
                raise ValueError("duplicate error")
            except Exception as e:
                tracker.track_error(
                    e,
                    module="mod",
                    function="fn",
                )

        errors = tracker.get_recent_errors(limit=10)
        # Should be deduplicated to 1 unique error
        assert len(errors) == 1
        assert errors[0].occurrence_count == 3

    def test_resolve_error(self, tracker):
        try:
            raise ValueError("to resolve")
        except Exception as e:
            error_id = tracker.track_error(e)

        tracker.resolve_error(error_id, "fixed it")
        record = tracker.get_error(error_id)
        assert record.resolved is True

    def test_get_unresolved_errors(self, tracker):
        try:
            raise ValueError("unresolved")
        except Exception as e:
            tracker.track_error(e)

        unresolved = tracker.get_unresolved_errors()
        assert len(unresolved) >= 1

    def test_get_statistics(self, tracker):
        try:
            raise ValueError("stat error")
        except Exception as e:
            tracker.track_error(
                e,
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.API_ERROR,
            )

        stats = tracker.get_statistics(time_window_hours=24)
        assert stats["total_unique_errors"] >= 1
        assert stats["total_occurrences"] >= 1

    def test_clear_old_errors(self, tracker):
        try:
            raise ValueError("old error")
        except Exception as e:
            error_id = tracker.track_error(e)

        # Resolve it and mark as old
        tracker.resolve_error(error_id)
        tracker.conn.execute(
            "UPDATE errors SET last_seen = 0 WHERE id = ?", (error_id,)
        )
        tracker.conn.commit()

        deleted = tracker.clear_old_errors(days=1)
        assert deleted >= 1

    def test_severity_filtering(self, tracker):
        try:
            raise ValueError("critical")
        except Exception as e:
            tracker.track_error(e, severity=ErrorSeverity.CRITICAL)

        try:
            raise ValueError("low")
        except Exception as e:
            tracker.track_error(e, severity=ErrorSeverity.LOW)

        critical = tracker.get_recent_errors(severity=ErrorSeverity.CRITICAL)
        assert all(e.severity == ErrorSeverity.CRITICAL for e in critical)
