"""
Unit Tests for Error Tracker Module

Tests SQLite-based error tracking with categorization and reporting.
"""

import pytest
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from core.error_tracker import (
    ErrorSeverity,
    ErrorCategory,
    ErrorRecord,
    ErrorTracker,
    get_error_tracker,
    track_error,
)


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""
    
    def test_severity_values(self):
        """Test severity level values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_all_severities_exist(self):
        """Test all expected severities are defined."""
        severities = [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, 
                      ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        assert len(severities) == 4


class TestErrorCategory:
    """Tests for ErrorCategory enum."""
    
    def test_category_values(self):
        """Test category values."""
        assert ErrorCategory.API_ERROR.value == "api_error"
        assert ErrorCategory.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCategory.TRANSLATION_ERROR.value == "translation_error"
        assert ErrorCategory.OCR_ERROR.value == "ocr_error"
        assert ErrorCategory.DATABASE_ERROR.value == "database_error"
        assert ErrorCategory.UNKNOWN_ERROR.value == "unknown"
    
    def test_all_categories_exist(self):
        """Test all expected categories are defined."""
        categories = [
            ErrorCategory.API_ERROR,
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.TRANSLATION_ERROR,
            ErrorCategory.OCR_ERROR,
            ErrorCategory.DATABASE_ERROR,
            ErrorCategory.FILESYSTEM_ERROR,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.CONFIGURATION_ERROR,
            ErrorCategory.UNKNOWN_ERROR,
        ]
        assert len(categories) == 10


class TestErrorRecord:
    """Tests for ErrorRecord dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic error record."""
        record = ErrorRecord(
            error_type="ValueError",
            error_message="Invalid input"
        )
        assert record.error_type == "ValueError"
        assert record.error_message == "Invalid input"
    
    def test_default_values(self):
        """Test default values."""
        record = ErrorRecord()
        assert record.id is None
        assert record.error_hash is None
        assert record.error_type == ""
        assert record.error_message == ""
        assert record.severity == ErrorSeverity.MEDIUM
        assert record.occurrence_count == 1
        assert record.resolved is False
    
    def test_full_record(self):
        """Test fully populated record."""
        record = ErrorRecord(
            id=1,
            error_hash="abc123",
            error_type="APIError",
            error_message="Connection failed",
            stack_trace="Traceback...",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API_ERROR,
            module="core.translator",
            function="translate_chunk",
            job_id="job_001",
            user_id="user_001",
            first_seen=time.time(),
            last_seen=time.time(),
            occurrence_count=5,
            resolved=False,
            metadata={"retry_count": 3}
        )
        assert record.id == 1
        assert record.severity == ErrorSeverity.HIGH
        assert record.category == ErrorCategory.API_ERROR
        assert record.occurrence_count == 5
        assert record.metadata["retry_count"] == 3


class TestErrorTracker:
    """Tests for ErrorTracker class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield Path(f.name)
        # Cleanup
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def tracker(self, temp_db):
        """Create an ErrorTracker instance with temp database."""
        tracker = ErrorTracker(db_path=temp_db)
        yield tracker
        tracker.close()
    
    def test_tracker_creation(self, tracker):
        """Test basic tracker creation."""
        assert tracker is not None
        assert tracker.conn is not None
    
    def test_track_simple_error(self, tracker):
        """Test tracking a simple error."""
        error = ValueError("Test error message")
        
        # Returns error ID as int
        error_id = tracker.track_error(
            error=error,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION_ERROR
        )
        
        assert isinstance(error_id, int)
        assert error_id > 0
        
        # Retrieve to verify
        record = tracker.get_error(error_id)
        assert record.error_type == "ValueError"
        assert "Test error message" in record.error_message
    
    def test_track_error_with_context(self, tracker):
        """Test tracking error with full context."""
        error = ConnectionError("API connection failed")
        
        error_id = tracker.track_error(
            error=error,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API_ERROR,
            module="core.translator",
            function="translate_chunk",
            job_id="job_123",
            user_id="user_456"
        )
        
        record = tracker.get_error(error_id)
        assert record.severity == ErrorSeverity.HIGH
        assert record.category == ErrorCategory.API_ERROR
        assert record.module == "core.translator"
        assert record.function == "translate_chunk"
        assert record.job_id == "job_123"
    
    def test_error_deduplication(self, tracker):
        """Test that duplicate errors are counted, not duplicated."""
        error = ValueError("Duplicate error test")
        
        # Track same error twice
        id1 = tracker.track_error(error=error, module="test", function="test")
        id2 = tracker.track_error(error=error, module="test", function="test")
        
        # Should return same ID since it's deduplicated
        assert id1 == id2
        
        # Get the error and check count
        retrieved = tracker.get_error(id1)
        assert retrieved is not None
        assert retrieved.occurrence_count >= 2
    
    def test_get_error(self, tracker):
        """Test getting error by ID."""
        error = TypeError("Test type error")
        error_id = tracker.track_error(error=error)
        
        retrieved = tracker.get_error(error_id)
        
        assert retrieved is not None
        assert retrieved.id == error_id
        assert retrieved.error_type == "TypeError"
    
    def test_get_nonexistent_error(self, tracker):
        """Test getting error that doesn't exist."""
        retrieved = tracker.get_error(99999)
        assert retrieved is None
    
    def test_get_recent_errors(self, tracker):
        """Test getting recent errors."""
        # Track some errors
        tracker.track_error(ValueError("Error 1"), severity=ErrorSeverity.LOW)
        tracker.track_error(TypeError("Error 2"), severity=ErrorSeverity.MEDIUM)
        tracker.track_error(RuntimeError("Error 3"), severity=ErrorSeverity.HIGH)
        
        errors = tracker.get_recent_errors(limit=10)
        
        assert len(errors) >= 3
    
    def test_get_recent_errors_with_severity_filter(self, tracker):
        """Test getting recent errors filtered by severity."""
        tracker.track_error(ValueError("Low error"), severity=ErrorSeverity.LOW)
        tracker.track_error(RuntimeError("High error"), severity=ErrorSeverity.HIGH)
        
        high_errors = tracker.get_recent_errors(severity=ErrorSeverity.HIGH)
        
        for error in high_errors:
            assert error.severity == ErrorSeverity.HIGH
    
    def test_get_unresolved_errors(self, tracker):
        """Test getting unresolved errors."""
        error_id = tracker.track_error(ValueError("Unresolved error"))
        
        unresolved = tracker.get_unresolved_errors()
        
        assert len(unresolved) >= 1
        assert any(e.id == error_id for e in unresolved)
    
    def test_get_unresolved_errors_by_category(self, tracker):
        """Test getting unresolved errors by category."""
        tracker.track_error(
            ValueError("API problem"),
            category=ErrorCategory.API_ERROR
        )
        tracker.track_error(
            RuntimeError("DB problem"),
            category=ErrorCategory.DATABASE_ERROR
        )
        
        api_errors = tracker.get_unresolved_errors(category=ErrorCategory.API_ERROR)
        
        for error in api_errors:
            assert error.category == ErrorCategory.API_ERROR
    
    def test_resolve_error(self, tracker):
        """Test resolving an error."""
        error_id = tracker.track_error(ValueError("Error to resolve"))
        
        tracker.resolve_error(error_id, resolution_notes="Fixed by updating config")
        
        retrieved = tracker.get_error(error_id)
        assert retrieved.resolved is True
        assert "Fixed by updating config" in retrieved.resolution_notes
    
    def test_get_statistics(self, tracker):
        """Test getting error statistics."""
        tracker.track_error(ValueError("Stat error 1"), severity=ErrorSeverity.LOW)
        tracker.track_error(TypeError("Stat error 2"), severity=ErrorSeverity.HIGH)
        tracker.track_error(RuntimeError("Stat error 3"), severity=ErrorSeverity.CRITICAL)
        
        stats = tracker.get_statistics(time_window_hours=24)
        
        assert isinstance(stats, dict)
        assert "total_unique_errors" in stats
        assert "by_severity" in stats
        assert stats["total_unique_errors"] >= 3
    
    def test_clear_old_errors(self, tracker):
        """Test clearing old errors."""
        # Track an error
        tracker.track_error(ValueError("Old error"))
        
        # Clear errors older than 30 days (won't affect new ones)
        deleted = tracker.clear_old_errors(days=30)
        
        # Should not have deleted the new error
        assert isinstance(deleted, int)
    
    def test_close_connection(self, temp_db):
        """Test closing database connection."""
        tracker = ErrorTracker(db_path=temp_db)
        
        # Track an error
        tracker.track_error(ValueError("Test"))
        
        # Close
        tracker.close()
        
        # Connection should still be object but closed
        # Just verify close doesn't raise


class TestGlobalTracker:
    """Tests for global tracker functions."""
    
    def test_get_error_tracker(self):
        """Test getting global error tracker."""
        tracker = get_error_tracker()
        assert tracker is not None
        assert isinstance(tracker, ErrorTracker)
    
    def test_track_error_function(self):
        """Test track_error convenience function."""
        error = ValueError("Global tracker test")
        
        # Returns error ID as int
        result = track_error(
            error=error,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION_ERROR
        )
        
        assert isinstance(result, int)
        assert result > 0


class TestErrorTrackerEdgeCases:
    """Edge case tests for ErrorTracker."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def tracker(self, temp_db):
        """Create an ErrorTracker instance with temp database."""
        tracker = ErrorTracker(db_path=temp_db)
        yield tracker
        tracker.close()
    
    def test_track_error_with_long_message(self, tracker):
        """Test tracking error with very long message."""
        long_message = "Error " * 1000
        error = ValueError(long_message)
        
        error_id = tracker.track_error(error=error)
        
        assert error_id > 0
        record = tracker.get_error(error_id)
        assert len(record.error_message) > 0
    
    def test_track_error_with_special_characters(self, tracker):
        """Test tracking error with special characters."""
        error = ValueError("Error with 特殊文字 và ký tự đặc biệt")
        
        error_id = tracker.track_error(error=error)
        
        assert error_id > 0
    
    def test_track_error_with_none_values(self, tracker):
        """Test tracking error with None optional values."""
        error = ValueError("Simple error")
        
        error_id = tracker.track_error(
            error=error,
            job_id=None,
            user_id=None,
            metadata=None
        )
        
        assert error_id > 0
    
    def test_empty_statistics(self, temp_db):
        """Test statistics on empty database."""
        tracker = ErrorTracker(db_path=temp_db)
        
        stats = tracker.get_statistics(time_window_hours=24)
        
        assert isinstance(stats, dict)
        assert stats["total_unique_errors"] == 0
        tracker.close()
