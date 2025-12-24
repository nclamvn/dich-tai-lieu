"""
Unit tests for core/parallel.py - ParallelProcessor component
"""
import pytest
import asyncio
from core.parallel import ParallelProcessor, Task, TaskStatus, ProcessingStats


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"


class TestTask:
    """Test Task dataclass."""

    def test_task_creation(self):
        """Test basic Task creation."""
        task = Task(id=1, data="test_data")
        assert task.id == 1
        assert task.data == "test_data"
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None
        assert task.retry_count == 0

    def test_task_with_result(self):
        """Test Task with result."""
        task = Task(
            id=2,
            data="input",
            status=TaskStatus.COMPLETED,
            result="output"
        )
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "output"

    def test_task_with_error(self):
        """Test Task with error."""
        task = Task(
            id=3,
            data="input",
            status=TaskStatus.FAILED,
            error="Connection failed"
        )
        assert task.status == TaskStatus.FAILED
        assert task.error == "Connection failed"


class TestProcessingStats:
    """Test ProcessingStats dataclass."""

    def test_stats_initialization(self):
        """Test ProcessingStats initialization."""
        stats = ProcessingStats()
        assert stats.total_tasks == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.retried == 0
        assert stats.total_time == 0.0
        assert stats.avg_time_per_task == 0.0

    def test_stats_update_completed_task(self):
        """Test stats update with completed task."""
        stats = ProcessingStats(total_tasks=1)
        task = Task(id=1, data="test", status=TaskStatus.COMPLETED)
        task.start_time = 1.0
        task.end_time = 2.0

        stats.update(task)

        assert stats.completed == 1
        assert stats.total_time == 1.0
        assert stats.avg_time_per_task == 1.0

    def test_stats_update_failed_task(self):
        """Test stats update with failed task."""
        stats = ProcessingStats(total_tasks=1)
        task = Task(id=1, data="test", status=TaskStatus.FAILED)

        stats.update(task)

        assert stats.failed == 1
        assert stats.completed == 0

    def test_stats_update_retried_task(self):
        """Test stats update with retried task."""
        stats = ProcessingStats(total_tasks=1)
        task = Task(id=1, data="test", status=TaskStatus.COMPLETED, retry_count=2)
        task.start_time = 1.0
        task.end_time = 2.0

        stats.update(task)

        assert stats.retried == 1
        assert stats.completed == 1

    def test_stats_avg_calculation(self):
        """Test average time calculation."""
        stats = ProcessingStats(total_tasks=3)

        # Add 3 tasks with different durations
        for i in range(3):
            task = Task(id=i, data="test", status=TaskStatus.COMPLETED)
            task.start_time = float(i)
            task.end_time = float(i + 1)
            stats.update(task)

        assert stats.completed == 3
        assert stats.total_time == 3.0
        assert stats.avg_time_per_task == 1.0


class TestParallelProcessor:
    """Test ParallelProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a ParallelProcessor instance."""
        return ParallelProcessor(
            max_concurrency=3,
            max_retries=2,
            timeout=5.0,
            show_progress=False  # Disable progress bar for tests
        )

    # ========================================================================
    # Test: Initialization
    # ========================================================================

    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = ParallelProcessor(max_concurrency=5, max_retries=3, timeout=10.0)
        assert processor.max_concurrency == 5
        assert processor.max_retries == 3
        assert processor.timeout == 10.0

    def test_processor_default_values(self):
        """Test processor default values."""
        processor = ParallelProcessor()
        # Should have default values
        assert processor.max_concurrency > 0
        assert processor.max_retries >= 0
        assert processor.timeout > 0

    # ========================================================================
    # Test: Async Processing
    # ========================================================================

    @pytest.mark.asyncio
    async def test_process_single_task_success(self, processor):
        """Test processing a single successful task."""
        async def mock_handler(data):
            await asyncio.sleep(0.01)
            return f"processed_{data}"

        tasks_data = ["task1"]
        results, stats = await processor.process_all(tasks_data, mock_handler)

        assert len(results) == 1
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result == "processed_task1"

    @pytest.mark.asyncio
    async def test_process_multiple_tasks(self, processor):
        """Test processing multiple tasks."""
        async def mock_handler(data):
            await asyncio.sleep(0.01)
            return f"processed_{data}"

        tasks_data = ["task1", "task2", "task3"]
        results, stats = await processor.process_all(tasks_data, mock_handler)

        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    @pytest.mark.asyncio
    async def test_process_task_failure(self, processor):
        """Test processing a task that fails."""
        async def failing_handler(data):
            if data == "fail":
                raise Exception("Task failed")
            return f"processed_{data}"

        tasks_data = ["task1", "fail", "task2"]
        results, stats = await processor.process_all(tasks_data, failing_handler)

        assert len(results) == 3
        # Check that failed task is marked as failed
        failed_task = next(r for r in results if r.data == "fail")
        assert failed_task.status == TaskStatus.FAILED
        assert failed_task.error is not None

    @pytest.mark.asyncio
    async def test_process_with_retries(self, processor):
        """Test that failed tasks are retried."""
        attempt_count = {"count": 0}

        async def flaky_handler(data):
            attempt_count["count"] += 1
            if attempt_count["count"] <= 2:
                raise Exception("Temporary failure")
            return "success"

        tasks_data = ["task1"]
        results, stats = await processor.process_all(tasks_data, flaky_handler)

        # Should succeed after retries
        assert len(results) == 1
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].retry_count >= 1

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, processor):
        """Test that concurrency is limited."""
        active_tasks = {"count": 0, "max": 0}

        async def tracking_handler(data):
            active_tasks["count"] += 1
            active_tasks["max"] = max(active_tasks["max"], active_tasks["count"])
            await asyncio.sleep(0.05)
            active_tasks["count"] -= 1
            return f"processed_{data}"

        tasks_data = ["task" + str(i) for i in range(10)]
        results, stats = await processor.process_all(tasks_data, tracking_handler)

        # Max concurrent tasks should not exceed max_concurrency
        assert active_tasks["max"] <= processor.max_concurrency

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test task timeout handling."""
        processor = ParallelProcessor(timeout=0.1, max_retries=1, show_progress=False)

        async def slow_handler(data):
            await asyncio.sleep(1.0)  # Exceeds timeout
            return "done"

        tasks_data = ["task1"]
        results, stats = await processor.process_all(tasks_data, slow_handler)

        # Should fail due to timeout
        assert len(results) == 1
        # Depending on implementation, may be FAILED or have error
        # Just check it didn't complete successfully
        assert results[0].status != TaskStatus.COMPLETED or results[0].error is not None

    @pytest.mark.asyncio
    async def test_empty_task_list(self, processor):
        """Test processing empty task list."""
        async def mock_handler(data):
            return data

        results, stats = await processor.process_all([], mock_handler)
        assert len(results) == 0

    # ========================================================================
    # Test: Statistics
    # ========================================================================

    @pytest.mark.asyncio
    async def test_statistics_collection(self, processor):
        """Test that statistics are collected correctly."""
        async def mock_handler(data):
            await asyncio.sleep(0.01)
            return f"processed_{data}"

        tasks_data = ["task1", "task2", "task3"]
        results, stats = await processor.process_all(tasks_data, mock_handler)

        # Processor should have stats
        # Check results have timing info
        for result in results:
            if result.status == TaskStatus.COMPLETED:
                assert result.start_time is not None
                assert result.end_time is not None
                assert result.end_time >= result.start_time

    # ========================================================================
    # Integration Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_realistic_workflow(self, processor):
        """Test realistic translation workflow."""
        async def translation_handler(chunk):
            # Simulate translation
            await asyncio.sleep(0.02)
            return {
                "chunk_id": chunk["id"],
                "translated": f"Translated: {chunk['text']}"
            }

        chunks = [
            {"id": 1, "text": "Hello world"},
            {"id": 2, "text": "Good morning"},
            {"id": 3, "text": "Thank you"}
        ]

        results, stats = await processor.process_all(chunks, translation_handler)

        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results)
        assert all(r.result is not None for r in results)

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, processor):
        """Test handling mix of successful and failed tasks."""
        async def mixed_handler(data):
            await asyncio.sleep(0.01)
            if "fail" in data:
                raise Exception("Intentional failure")
            return f"success_{data}"

        tasks_data = ["good1", "fail1", "good2", "fail2", "good3"]
        results, stats = await processor.process_all(tasks_data, mixed_handler)

        assert len(results) == 5

        successful = [r for r in results if r.status == TaskStatus.COMPLETED]
        failed = [r for r in results if r.status == TaskStatus.FAILED]

        assert len(successful) == 3
        assert len(failed) == 2

    @pytest.mark.parametrize("concurrency", [1, 3, 5])
    @pytest.mark.asyncio
    async def test_various_concurrency_levels(self, concurrency):
        """Test processor with various concurrency levels."""
        processor = ParallelProcessor(max_concurrency=concurrency, show_progress=False)

        async def mock_handler(data):
            await asyncio.sleep(0.01)
            return data

        tasks_data = ["task" + str(i) for i in range(10)]
        results, stats = await processor.process_all(tasks_data, mock_handler)

        assert len(results) == 10
        assert all(r.status == TaskStatus.COMPLETED for r in results)
