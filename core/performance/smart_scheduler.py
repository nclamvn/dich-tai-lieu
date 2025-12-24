"""
Smart Batch Scheduler Module

Intelligent scheduling of translation tasks with dynamic batching,
adaptive retry strategies, and load balancing.
"""

import asyncio
import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, Dict
from enum import Enum
from collections import defaultdict


class BatchStrategy(Enum):
    """Batching strategies for different workload patterns"""
    FIXED = "fixed"  # Fixed batch size
    DYNAMIC = "dynamic"  # Adjust based on performance
    ADAPTIVE = "adaptive"  # Adjust based on concurrency tuner
    LATENCY_OPTIMIZED = "latency_optimized"  # Prioritize fast response
    THROUGHPUT_OPTIMIZED = "throughput_optimized"  # Prioritize total throughput


@dataclass
class BatchConfig:
    """
    Configuration for batch scheduling

    Attributes:
        strategy: Batching strategy to use
        min_batch_size: Minimum tasks per batch
        max_batch_size: Maximum tasks per batch
        initial_batch_size: Starting batch size
        batch_timeout_sec: Maximum time to wait for batch to fill
        max_retries: Maximum retry attempts per task
        base_retry_delay_sec: Initial retry delay
        max_retry_delay_sec: Maximum retry delay
        retry_jitter: Random jitter factor (0.0 - 1.0)
        priority_enabled: Enable task prioritization
    """
    strategy: BatchStrategy = BatchStrategy.DYNAMIC
    min_batch_size: int = 1
    max_batch_size: int = 50
    initial_batch_size: int = 10
    batch_timeout_sec: float = 2.0
    max_retries: int = 3
    base_retry_delay_sec: float = 1.0
    max_retry_delay_sec: float = 30.0
    retry_jitter: float = 0.2
    priority_enabled: bool = False


@dataclass
class ScheduledTask:
    """
    A task scheduled for execution

    Attributes:
        task_id: Unique task identifier
        payload: Task data/parameters
        priority: Task priority (higher = more urgent)
        retry_count: Number of retries attempted
        created_at: Task creation timestamp
        started_at: Task start timestamp
        metadata: Additional task metadata
    """
    task_id: str
    payload: Any
    priority: int = 0
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Enable priority queue sorting (higher priority first)"""
        return self.priority > other.priority


@dataclass
class BatchResult:
    """
    Result of batch execution

    Attributes:
        batch_id: Batch identifier
        task_count: Number of tasks in batch
        successful_count: Number of successful tasks
        failed_count: Number of failed tasks
        execution_time_sec: Total execution time
        avg_task_time_sec: Average time per task
        error_summary: Summary of errors encountered
    """
    batch_id: str
    task_count: int
    successful_count: int
    failed_count: int
    execution_time_sec: float
    avg_task_time_sec: float
    error_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.task_count == 0:
            return 0.0
        return self.successful_count / self.task_count


class SmartBatchScheduler:
    """
    Intelligent batch scheduler with dynamic sizing and retry logic

    This scheduler optimizes batch processing by:
    - Dynamically adjusting batch sizes based on performance
    - Implementing exponential backoff with jitter for retries
    - Supporting task prioritization
    - Providing detailed execution metrics

    Example:
        async def process_task(task: ScheduledTask) -> Any:
            # Process the task
            return result

        scheduler = SmartBatchScheduler(process_task)

        # Add tasks
        for i in range(100):
            scheduler.add_task(f"task_{i}", payload={"data": i})

        # Process all tasks
        results = await scheduler.process_all()
    """

    def __init__(
        self,
        task_processor: Callable[[ScheduledTask], Any],
        config: Optional[BatchConfig] = None,
        concurrency_tuner: Optional[Any] = None
    ):
        """
        Initialize the smart batch scheduler

        Args:
            task_processor: Async function to process individual tasks
            config: Batch configuration (uses defaults if None)
            concurrency_tuner: Optional AdaptiveConcurrencyTuner for optimization
        """
        self.task_processor = task_processor
        self.config = config or BatchConfig()
        self.concurrency_tuner = concurrency_tuner

        # Task queues
        self._pending_tasks: List[ScheduledTask] = []
        self._failed_tasks: Dict[str, ScheduledTask] = {}
        self._completed_tasks: List[str] = []

        # Scheduling state
        self.current_batch_size = self.config.initial_batch_size
        self._batch_counter = 0

        # Performance tracking
        self._batch_results: List[BatchResult] = []
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Control flags
        self._is_processing = False
        self._should_stop = False

    def add_task(
        self,
        task_id: str,
        payload: Any,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a task to the scheduler

        Args:
            task_id: Unique task identifier
            payload: Task data
            priority: Task priority (higher values = higher priority)
            metadata: Optional task metadata
        """
        task = ScheduledTask(
            task_id=task_id,
            payload=payload,
            priority=priority,
            metadata=metadata or {}
        )
        self._pending_tasks.append(task)

        # Sort by priority if enabled
        if self.config.priority_enabled:
            self._pending_tasks.sort()

    def add_tasks_batch(self, tasks: List[tuple]):
        """
        Add multiple tasks at once

        Args:
            tasks: List of (task_id, payload) or (task_id, payload, priority) tuples
        """
        for task_tuple in tasks:
            if len(task_tuple) == 2:
                task_id, payload = task_tuple
                priority = 0
            else:
                task_id, payload, priority = task_tuple

            self.add_task(task_id, payload, priority)

    async def process_all(self) -> List[Any]:
        """
        Process all pending tasks

        Returns:
            List of results from all successful tasks
        """
        if self._is_processing:
            raise RuntimeError("Scheduler is already processing")

        self._is_processing = True
        self._should_stop = False
        all_results = []

        try:
            while self._pending_tasks and not self._should_stop:
                # Get next batch
                batch = self._get_next_batch()

                if not batch:
                    break

                # Process batch
                results = await self._process_batch(batch)
                all_results.extend(results)

                # Adjust batch size based on strategy
                self._adjust_batch_size()

            # Retry failed tasks
            if self._failed_tasks and not self._should_stop:
                retry_results = await self._retry_failed_tasks()
                all_results.extend(retry_results)

        finally:
            self._is_processing = False

        return all_results

    def _get_next_batch(self) -> List[ScheduledTask]:
        """
        Get the next batch of tasks to process

        Returns:
            List of tasks for the batch
        """
        if not self._pending_tasks:
            return []

        # Determine batch size
        batch_size = min(self.current_batch_size, len(self._pending_tasks))

        # Extract tasks
        batch = self._pending_tasks[:batch_size]
        self._pending_tasks = self._pending_tasks[batch_size:]

        return batch

    async def _process_batch(self, batch: List[ScheduledTask]) -> List[Any]:
        """
        Process a batch of tasks

        Args:
            batch: List of tasks to process

        Returns:
            List of successful results
        """
        self._batch_counter += 1
        batch_id = f"batch_{self._batch_counter}"
        start_time = time.time()

        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        # Process tasks concurrently
        async def process_with_tracking(task: ScheduledTask):
            task.started_at = time.time()
            try:
                result = await self.task_processor(task)

                # Record metrics for concurrency tuner
                if self.concurrency_tuner:
                    latency_ms = (time.time() - task.started_at) * 1000
                    self.concurrency_tuner.record_task_completion(
                        latency_ms=latency_ms,
                        success=True
                    )

                return (True, task, result, None)

            except Exception as e:
                error_type = type(e).__name__
                error_summary[error_type] += 1
                self._error_counts[error_type] += 1

                # Record metrics for concurrency tuner
                if self.concurrency_tuner:
                    latency_ms = (time.time() - task.started_at) * 1000
                    self.concurrency_tuner.record_task_completion(
                        latency_ms=latency_ms,
                        success=False
                    )

                return (False, task, None, e)

        # Execute all tasks in batch
        batch_results = await asyncio.gather(
            *[process_with_tracking(task) for task in batch],
            return_exceptions=False
        )

        # Process results
        for success, task, result, error in batch_results:
            if success:
                successful_count += 1
                results.append(result)
                self._completed_tasks.append(task.task_id)
            else:
                failed_count += 1
                task.retry_count += 1

                # Add to failed queue if retries remain
                if task.retry_count < self.config.max_retries:
                    self._failed_tasks[task.task_id] = task

        # Record batch metrics
        execution_time = time.time() - start_time
        avg_task_time = execution_time / len(batch) if batch else 0.0

        batch_result = BatchResult(
            batch_id=batch_id,
            task_count=len(batch),
            successful_count=successful_count,
            failed_count=failed_count,
            execution_time_sec=execution_time,
            avg_task_time_sec=avg_task_time,
            error_summary=dict(error_summary)
        )

        self._batch_results.append(batch_result)

        return results

    async def _retry_failed_tasks(self) -> List[Any]:
        """
        Retry all failed tasks with exponential backoff

        Returns:
            List of successful results from retries
        """
        results = []

        while self._failed_tasks:
            # Get all tasks ready for retry
            tasks_to_retry = list(self._failed_tasks.values())
            self._failed_tasks.clear()

            # Apply exponential backoff with jitter
            for task in tasks_to_retry:
                delay = self._calculate_retry_delay(task.retry_count)
                await asyncio.sleep(delay)

            # Process retry batch
            batch_results = await self._process_batch(tasks_to_retry)
            results.extend(batch_results)

        return results

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """
        Calculate retry delay with exponential backoff and jitter

        Args:
            retry_count: Number of retries already attempted

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * 2^retry_count
        delay = self.config.base_retry_delay_sec * (2 ** retry_count)

        # Cap at maximum
        delay = min(delay, self.config.max_retry_delay_sec)

        # Add jitter to prevent thundering herd
        jitter_range = delay * self.config.retry_jitter
        jitter = random.uniform(-jitter_range, jitter_range)
        delay += jitter

        return max(0.0, delay)

    def _adjust_batch_size(self):
        """
        Adjust batch size based on strategy and performance
        """
        if self.config.strategy == BatchStrategy.FIXED:
            # No adjustment
            return

        elif self.config.strategy == BatchStrategy.ADAPTIVE:
            # Use concurrency tuner recommendation
            if self.concurrency_tuner:
                optimal_concurrency = self.concurrency_tuner.get_optimal_concurrency()
                self.current_batch_size = max(
                    self.config.min_batch_size,
                    min(optimal_concurrency, self.config.max_batch_size)
                )

        elif self.config.strategy == BatchStrategy.DYNAMIC:
            # Adjust based on recent batch performance
            if len(self._batch_results) >= 2:
                recent = self._batch_results[-1]
                previous = self._batch_results[-2]

                # If success rate improved, increase batch size
                if recent.success_rate > previous.success_rate:
                    self.current_batch_size = min(
                        self.current_batch_size + 2,
                        self.config.max_batch_size
                    )
                # If success rate degraded significantly, decrease batch size
                elif recent.success_rate < previous.success_rate * 0.8:
                    self.current_batch_size = max(
                        int(self.current_batch_size * 0.75),
                        self.config.min_batch_size
                    )

        elif self.config.strategy == BatchStrategy.LATENCY_OPTIMIZED:
            # Use smaller batches for faster response
            self.current_batch_size = self.config.min_batch_size

        elif self.config.strategy == BatchStrategy.THROUGHPUT_OPTIMIZED:
            # Use larger batches for maximum throughput
            self.current_batch_size = self.config.max_batch_size

    def get_statistics(self) -> dict:
        """
        Get comprehensive scheduler statistics

        Returns:
            Dictionary with performance metrics
        """
        total_tasks = (
            len(self._pending_tasks) +
            len(self._failed_tasks) +
            len(self._completed_tasks)
        )

        successful_tasks = len(self._completed_tasks)
        failed_tasks = len(self._failed_tasks)
        pending_tasks = len(self._pending_tasks)

        # Calculate aggregate metrics
        if self._batch_results:
            total_batches = len(self._batch_results)
            avg_batch_time = sum(b.execution_time_sec for b in self._batch_results) / total_batches
            avg_success_rate = sum(b.success_rate for b in self._batch_results) / total_batches
            total_execution_time = sum(b.execution_time_sec for b in self._batch_results)
        else:
            total_batches = 0
            avg_batch_time = 0.0
            avg_success_rate = 0.0
            total_execution_time = 0.0

        return {
            'total_tasks': total_tasks,
            'completed_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'pending_tasks': pending_tasks,
            'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0.0,
            'total_batches': total_batches,
            'current_batch_size': self.current_batch_size,
            'avg_batch_time_sec': avg_batch_time,
            'avg_success_rate': avg_success_rate,
            'total_execution_time_sec': total_execution_time,
            'error_counts': dict(self._error_counts),
            'is_processing': self._is_processing
        }

    def stop(self):
        """
        Signal the scheduler to stop processing after current batch
        """
        self._should_stop = True

    def reset(self):
        """
        Reset the scheduler to initial state
        """
        self._pending_tasks.clear()
        self._failed_tasks.clear()
        self._completed_tasks.clear()
        self._batch_results.clear()
        self._error_counts.clear()
        self._batch_counter = 0
        self.current_batch_size = self.config.initial_batch_size
        self._is_processing = False
        self._should_stop = False


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    print("Smart Batch Scheduler - Demo")
    print("=" * 80)

    # Define a mock task processor
    async def mock_task_processor(task: ScheduledTask) -> str:
        """Simulate task processing with variable latency"""
        # Simulate processing time
        latency = random.uniform(0.05, 0.2)
        await asyncio.sleep(latency)

        # Simulate occasional failures (10% failure rate)
        if random.random() < 0.1:
            raise Exception("Simulated task failure")

        return f"Result for {task.task_id}"

    async def run_demo():
        # Create scheduler with dynamic batching
        config = BatchConfig(
            strategy=BatchStrategy.DYNAMIC,
            min_batch_size=5,
            max_batch_size=20,
            initial_batch_size=10,
            max_retries=3
        )

        scheduler = SmartBatchScheduler(
            task_processor=mock_task_processor,
            config=config
        )

        print(f"Configuration:")
        print(f"  Strategy: {config.strategy.value}")
        print(f"  Batch size: {config.min_batch_size}-{config.max_batch_size}")
        print(f"  Max retries: {config.max_retries}")
        print()

        # Add tasks
        print("Adding 100 tasks...")
        for i in range(100):
            priority = random.randint(0, 5)
            scheduler.add_task(
                task_id=f"task_{i:03d}",
                payload={"index": i, "data": f"Sample data {i}"},
                priority=priority
            )

        # Process all tasks
        print("Processing tasks...\n")
        results = await scheduler.process_all()

        # Print statistics
        stats = scheduler.get_statistics()

        print("\n" + "=" * 80)
        print("Processing Complete!")
        print("=" * 80)
        print(f"\nStatistics:")
        print(f"  Total tasks: {stats['total_tasks']}")
        print(f"  Completed: {stats['completed_tasks']}")
        print(f"  Failed: {stats['failed_tasks']}")
        print(f"  Pending: {stats['pending_tasks']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        print(f"\nBatch metrics:")
        print(f"  Total batches: {stats['total_batches']}")
        print(f"  Final batch size: {stats['current_batch_size']}")
        print(f"  Avg batch time: {stats['avg_batch_time_sec']:.2f}s")
        print(f"  Avg success rate: {stats['avg_success_rate']:.1%}")
        print(f"  Total execution time: {stats['total_execution_time_sec']:.2f}s")

        if stats['error_counts']:
            print(f"\nError summary:")
            for error_type, count in stats['error_counts'].items():
                print(f"  {error_type}: {count}")

        print(f"\n✓ Processed {len(results)} tasks successfully!")

    # Run demo
    asyncio.run(run_demo())
