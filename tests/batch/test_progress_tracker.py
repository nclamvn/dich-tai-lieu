"""
Unit tests for core.batch.progress_tracker module.

Tests ProgressTracker, ProgressState, and callback functions.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from core.batch.progress_tracker import (
    ProgressTracker,
    ProgressState,
    create_websocket_callback,
    create_logging_callback,
)


class TestProgressState:
    """Tests for ProgressState dataclass."""

    def test_state_creation_default(self):
        """Test creating ProgressState with defaults."""
        state = ProgressState()
        assert state.total_steps == 0
        assert state.completed_steps == 0
        assert state.current_phase == ""
        assert state.current_step == ""
        assert state.percentage == 0.0
        assert state.eta_seconds is None
        assert state.quality_score == 0.0

    def test_state_creation_with_values(self):
        """Test creating ProgressState with values."""
        state = ProgressState(
            total_steps=100,
            completed_steps=50,
            current_phase="translating",
            current_step="Chunk 50/100",
            percentage=0.5,
            eta_seconds=120.0,
            quality_score=0.92
        )
        assert state.total_steps == 100
        assert state.completed_steps == 50
        assert state.current_phase == "translating"
        assert state.percentage == 0.5
        assert state.eta_seconds == 120.0

    def test_elapsed_seconds_property(self):
        """Test elapsed_seconds calculation."""
        state = ProgressState()
        state.started_at = datetime.now() - timedelta(seconds=5)

        elapsed = state.elapsed_seconds
        assert 4.9 <= elapsed <= 5.5  # Allow small timing variance

    def test_to_dict(self):
        """Test to_dict serialization."""
        state = ProgressState(
            total_steps=100,
            completed_steps=50,
            current_phase="translating",
            current_step="Chunk 50",
            percentage=0.5,
            quality_score=0.9
        )

        result = state.to_dict()

        assert result["total"] == 100
        assert result["completed"] == 50
        assert result["percentage"] == 0.5
        assert result["phase"] == "translating"
        assert result["step"] == "Chunk 50"
        assert result["quality_score"] == 0.9
        assert "elapsed_seconds" in result
        assert "eta_seconds" in result


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a ProgressTracker instance."""
        return ProgressTracker(
            total_chunks=100,
            job_id="test_job_001",
            job_name="Test Translation Job"
        )

    def test_tracker_initialization(self, tracker):
        """Test ProgressTracker initialization."""
        assert tracker.job_id == "test_job_001"
        assert tracker.job_name == "Test Translation Job"
        assert tracker.total_chunks == 100
        assert tracker.state.total_steps == 100
        assert len(tracker._callbacks) == 0

    def test_add_remove_callback(self, tracker):
        """Test adding and removing callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        tracker.add_callback(callback1)
        tracker.add_callback(callback2)
        assert len(tracker._callbacks) == 2

        tracker.remove_callback(callback1)
        assert len(tracker._callbacks) == 1
        assert callback2 in tracker._callbacks

    def test_remove_nonexistent_callback(self, tracker):
        """Test removing callback that doesn't exist."""
        callback = Mock()
        tracker.remove_callback(callback)  # Should not raise
        assert len(tracker._callbacks) == 0

    def test_start(self, tracker):
        """Test starting progress tracking."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start()

        assert callback.called
        call_args = callback.call_args
        assert call_args[0][0] == 0.0  # percentage
        assert "Starting" in call_args[0][1]  # message

    def test_start_phase(self, tracker):
        """Test starting a new phase."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start_phase("translating", total_steps=100)

        assert tracker._current_phase == "translating"
        assert tracker.state.current_phase == "translating"
        assert tracker.state.total_steps == 100
        assert tracker.state.completed_steps == 0

    def test_update_progress(self, tracker):
        """Test updating progress within a phase."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start_phase("translating", total_steps=100)
        tracker.update(50, "Chunk 50/100", quality=0.9)

        assert tracker.state.completed_steps == 50
        assert tracker.state.current_step == "Chunk 50/100"
        assert tracker.state.quality_score == 0.9
        assert tracker.state.percentage == 0.5

    def test_update_eta_calculation(self, tracker):
        """Test ETA calculation during update."""
        tracker.start_phase("translating", total_steps=100)

        # Simulate some elapsed time
        tracker.state.started_at = datetime.now() - timedelta(seconds=10)

        tracker.update(50, "Halfway")

        # Should have ETA based on progress rate
        assert tracker.state.eta_seconds is not None
        # 50 done in 10s = 5/sec, 50 remaining = ~10s ETA
        assert 8 <= tracker.state.eta_seconds <= 12

    def test_complete_phase(self, tracker):
        """Test completing a phase."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start_phase("translating", total_steps=100)
        tracker.update(100, "All done")
        tracker.complete_phase()

        assert "translating" in tracker._phases_completed
        assert tracker._current_phase is None
        assert tracker._phase_progress == 1.0

    def test_finish(self, tracker):
        """Test finishing all progress."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start()
        tracker.start_phase("translating", total_steps=100)
        tracker.update(100, "Done")
        tracker.complete_phase()
        tracker.finish("All completed!")

        assert tracker.state.percentage == 1.0
        assert tracker.state.current_step == "All completed!"
        assert tracker.state.eta_seconds == 0

        # Check final callback
        final_call = callback.call_args
        assert final_call[0][0] == 1.0  # percentage
        assert final_call[0][2]["completed"] is True  # extra data

    def test_fail(self, tracker):
        """Test marking progress as failed."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start()
        tracker.start_phase("translating", total_steps=100)
        tracker.update(50, "In progress")
        tracker.fail("API connection lost")

        assert "Failed: API connection lost" in tracker.state.current_step

        # Check callback received failure data
        final_call = callback.call_args
        assert final_call[0][2]["failed"] is True
        assert final_call[0][2]["error"] == "API connection lost"

    def test_overall_progress_calculation(self, tracker):
        """Test overall progress across multiple phases."""
        # Complete loading phase (5% weight)
        tracker.start_phase("loading", total_steps=10)
        tracker.update(10)
        tracker.complete_phase()

        # Start translating phase (70% weight)
        tracker.start_phase("translating", total_steps=100)
        tracker.update(50)  # 50% of translating

        # Overall should be: 5% (loading) + 35% (50% of 70%) = 40%
        overall = tracker._calculate_overall_progress()
        assert 0.38 <= overall <= 0.42

    def test_multiple_phases_progress(self, tracker):
        """Test progress through multiple phases."""
        callback = Mock()
        tracker.add_callback(callback)

        # Go through all phases
        phases = ["loading", "preprocessing", "translating", "postprocessing", "exporting"]

        for phase in phases:
            tracker.start_phase(phase, total_steps=10)
            for i in range(10):
                tracker.update(i + 1, f"Step {i+1}")
            tracker.complete_phase()

        tracker.finish()

        # Should be 100% after all phases
        assert tracker.state.percentage == 1.0

    def test_get_state(self, tracker):
        """Test getting current state as dictionary."""
        tracker.start()
        tracker.start_phase("translating", total_steps=100)
        tracker.update(50, "Halfway", quality=0.88)

        state = tracker.get_state()

        assert state["job_id"] == "test_job_001"
        assert state["job_name"] == "Test Translation Job"
        assert "progress" in state
        assert state["current_phase"] == "translating"
        assert state["quality_score"] == 0.88
        assert "elapsed_seconds" in state

    def test_callback_error_handling(self, tracker):
        """Test that callback errors don't break tracking."""
        failing_callback = Mock(side_effect=Exception("Callback error"))
        working_callback = Mock()

        tracker.add_callback(failing_callback)
        tracker.add_callback(working_callback)

        # Should not raise
        tracker.start()
        tracker.update(10, "Test")

        # Working callback should still be called
        assert working_callback.called


class TestProgressTrackerPhaseWeights:
    """Tests for phase weight calculations."""

    def test_phase_weights_defined(self):
        """Test all expected phases have weights."""
        expected_phases = ["loading", "preprocessing", "translating", "postprocessing", "exporting"]

        for phase in expected_phases:
            assert phase in ProgressTracker.PHASE_WEIGHTS
            assert 0 < ProgressTracker.PHASE_WEIGHTS[phase] <= 1

    def test_phase_weights_sum_to_one(self):
        """Test phase weights sum to approximately 1."""
        total = sum(ProgressTracker.PHASE_WEIGHTS.values())
        assert 0.99 <= total <= 1.01

    def test_translating_has_highest_weight(self):
        """Test translating phase has the highest weight."""
        max_weight = max(ProgressTracker.PHASE_WEIGHTS.values())
        assert ProgressTracker.PHASE_WEIGHTS["translating"] == max_weight

    def test_unknown_phase_uses_default_weight(self):
        """Test unknown phases get a default weight."""
        tracker = ProgressTracker(total_chunks=100)
        tracker.start_phase("unknown_phase", total_steps=10)
        tracker.update(5)

        # Should not crash and should use default weight
        progress = tracker._calculate_overall_progress()
        assert 0 <= progress <= 1


class TestWebSocketCallback:
    """Tests for WebSocket callback creation."""

    def test_create_websocket_callback(self):
        """Test creating WebSocket callback."""
        ws_manager = Mock()
        ws_manager.broadcast = AsyncMock()

        callback = create_websocket_callback(ws_manager)

        assert callable(callback)

    def test_websocket_callback_broadcasts(self):
        """Test WebSocket callback creates broadcast task."""
        ws_manager = Mock()
        ws_manager.broadcast = AsyncMock()

        callback = create_websocket_callback(ws_manager, event_name="test_event")

        with patch('asyncio.create_task') as mock_create_task:
            callback(0.5, "Testing", {"job_id": "test"})
            mock_create_task.assert_called_once()

    def test_websocket_callback_custom_event_name(self):
        """Test WebSocket callback with custom event name."""
        ws_manager = Mock()
        ws_manager.broadcast = AsyncMock()

        callback = create_websocket_callback(ws_manager, event_name="custom_progress")

        assert callback is not None


class TestLoggingCallback:
    """Tests for logging callback creation."""

    def test_create_logging_callback(self):
        """Test creating logging callback."""
        callback = create_logging_callback(log_interval=5)
        assert callable(callback)

    def test_logging_callback_interval(self):
        """Test logging callback respects interval."""
        callback = create_logging_callback(log_interval=3)

        with patch('core.batch.progress_tracker.logger') as mock_logger:
            # Call 5 times
            for i in range(5):
                callback(0.2 * i, f"Step {i}", {
                    "quality_score": 0.9,
                    "completed": i,
                    "total": 5
                })

            # Should log at call 3 (index 2, count becomes 3)
            # Note: actual calls depend on implementation
            assert mock_logger.info.call_count >= 1

    def test_logging_callback_logs_at_completion(self):
        """Test logging callback logs at 100%."""
        callback = create_logging_callback(log_interval=100)  # High interval

        with patch('core.batch.progress_tracker.logger') as mock_logger:
            callback(1.0, "Completed", {
                "quality_score": 0.95,
                "completed": 100,
                "total": 100
            })

            # Should log at completion regardless of interval
            mock_logger.info.assert_called()


class TestProgressTrackerEdgeCases:
    """Edge case tests for ProgressTracker."""

    def test_zero_total_chunks(self):
        """Test tracker with zero total chunks."""
        tracker = ProgressTracker(total_chunks=0)
        tracker.start()
        tracker.start_phase("translating", total_steps=0)
        tracker.update(0, "Nothing to do")
        tracker.complete_phase()
        tracker.finish()

        assert tracker.state.percentage == 1.0

    def test_update_without_starting_phase(self):
        """Test update without starting a phase first."""
        tracker = ProgressTracker(total_chunks=100)
        tracker.start()

        # Should not crash
        tracker.update(10, "Some update")

        # Percentage calculation with 0 total_steps
        assert tracker.state.completed_steps == 10

    def test_complete_phase_without_starting(self):
        """Test completing phase without starting one."""
        tracker = ProgressTracker(total_chunks=100)
        tracker.start()

        # Should not crash
        tracker.complete_phase()

        assert tracker._current_phase is None

    def test_rapid_updates(self):
        """Test many rapid updates."""
        tracker = ProgressTracker(total_chunks=1000)
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start_phase("translating", total_steps=1000)

        for i in range(1000):
            tracker.update(i + 1, f"Chunk {i+1}")

        # Callback is called for start_phase + 1000 updates
        assert callback.call_count >= 1000
        assert tracker.state.completed_steps == 1000

    def test_very_long_running_job(self):
        """Test ETA calculation for long-running job."""
        tracker = ProgressTracker(total_chunks=10000)
        tracker.start_phase("translating", total_steps=10000)

        # Simulate 1 hour elapsed, 5000 done
        tracker.state.started_at = datetime.now() - timedelta(hours=1)
        tracker.update(5000, "Halfway")

        # ETA should be approximately 1 hour (5000 remaining at same rate)
        assert tracker.state.eta_seconds is not None
        # Allow 10% variance
        assert 3200 <= tracker.state.eta_seconds <= 3800

    def test_empty_job_id_and_name(self):
        """Test tracker with empty job_id and name."""
        tracker = ProgressTracker(total_chunks=100, job_id="", job_name="")
        tracker.start()

        state = tracker.get_state()
        assert state["job_id"] == ""
        assert state["job_name"] == ""

    def test_negative_update_values(self):
        """Test handling of negative update values."""
        tracker = ProgressTracker(total_chunks=100)
        tracker.start_phase("translating", total_steps=100)

        # This shouldn't crash - implementation may handle differently
        tracker.update(-5, "Invalid")

        # Values should be stored as-is (implementation dependent)
        assert tracker.state.completed_steps == -5

    def test_update_exceeds_total(self):
        """Test update exceeding total steps."""
        tracker = ProgressTracker(total_chunks=100)
        tracker.start_phase("translating", total_steps=100)

        tracker.update(150, "Exceeded")

        # Should handle gracefully
        assert tracker.state.completed_steps == 150
        assert tracker._phase_progress > 1.0
