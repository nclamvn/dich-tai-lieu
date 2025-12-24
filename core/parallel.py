#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ParallelProcessor - Xử lý song song nhiều chunks với rate limiting
"""

import asyncio
import time
import random
from typing import List, Optional, Any
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import httpx
from tqdm import tqdm

from config.logging_config import get_logger
logger = get_logger(__name__)



class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    """Một task dịch thuật"""
    id: int
    data: Any  # TranslationChunk
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None  # TranslationResult
    error: Optional[str] = None
    retry_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class ProcessingStats:
    """Thống kê quá trình xử lý"""
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    retried: int = 0
    total_time: float = 0.0
    avg_time_per_task: float = 0.0
    tokens_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def update(self, task: Task):
        """Update stats from completed task"""
        if task.status == TaskStatus.COMPLETED:
            self.completed += 1
            if task.start_time is not None and task.end_time is not None:
                self.total_time += (task.end_time - task.start_time)
        elif task.status == TaskStatus.FAILED:
            self.failed += 1

        if task.retry_count > 0:
            self.retried += 1

        # Update averages
        if self.completed > 0:
            self.avg_time_per_task = self.total_time / self.completed


class ParallelProcessor:
    """Xử lý song song nhiều tasks với rate limiting và progress tracking"""

    def __init__(
        self,
        max_concurrency: int = 5,
        max_retries: int = 3,
        timeout: float = 300.0,
        show_progress: bool = True,
        progress_callback: Optional[Callable] = None,
        cancellation_token: Optional[Any] = None
    ):
        """
        Args:
            max_concurrency: Số lượng tasks chạy đồng thời tối đa
            max_retries: Số lần retry cho mỗi task
            timeout: Timeout cho mỗi task (seconds)
            show_progress: Hiển thị progress bar
            progress_callback: Optional callback(completed, total, quality_score) for real-time updates
            cancellation_token: Optional cancellation token to stop processing
        """
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.timeout = timeout
        self.show_progress = show_progress
        self.progress_callback = progress_callback
        self.cancellation_token = cancellation_token

        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.stats = ProcessingStats()
        self.tasks: List[Task] = []

    async def process_task(
        self,
        task: Task,
        processor_func: Callable,
        client: httpx.AsyncClient,
        progress_bar: Optional[tqdm] = None,
        total_tasks: int = 0
    ) -> Task:
        """Xử lý một task với retry logic, exponential backoff + jitter"""

        async with self.semaphore:  # Rate limiting
            while task.retry_count <= self.max_retries:
                # Check for cancellation
                if self.cancellation_token and hasattr(self.cancellation_token, 'is_cancelled'):
                    if self.cancellation_token.is_cancelled():
                        task.status = TaskStatus.FAILED
                        task.error = "Cancelled by user"
                        return task

                try:
                    task.status = TaskStatus.RUNNING if task.retry_count == 0 else TaskStatus.RETRYING
                    task.start_time = time.time()

                    # Process with timeout
                    task.result = await asyncio.wait_for(
                        processor_func(client, task.data),
                        timeout=self.timeout
                    )

                    task.end_time = time.time()
                    task.status = TaskStatus.COMPLETED
                    task.error = None

                    # Call progress callback if provided
                    if self.progress_callback:
                        quality_score = getattr(task.result, 'quality_score', 0.0)
                        # Note: We don't track completed count here, caller tracks it
                        # self.progress_callback will be called from batch_processor

                    if progress_bar:
                        progress_bar.update(1)
                        progress_bar.set_postfix({
                            'completed': self.stats.completed + 1,
                            'failed': self.stats.failed,
                            'retried': self.stats.retried
                        })

                    return task

                except asyncio.TimeoutError:
                    task.error = f"Timeout after {self.timeout}s"
                    task.retry_count += 1
                    logger.error(f" Task #{task.id}: {task.error} (retry {task.retry_count}/{self.max_retries})")

                except httpx.HTTPStatusError as e:
                    # Handle rate limiting (429) with longer backoff
                    if e.response.status_code == 429:
                        task.error = f"Rate limited (429)"
                        task.retry_count += 1
                        logger.warning(f" Task #{task.id}: {task.error} (retry {task.retry_count}/{self.max_retries})")
                        # Use longer backoff for rate limiting
                        if task.retry_count <= self.max_retries:
                            base_delay = min(2 ** (task.retry_count + 2), 30)
                            jitter = random.uniform(0, base_delay * 0.3)
                            await asyncio.sleep(base_delay + jitter)
                            continue
                    else:
                        task.error = f"HTTP {e.response.status_code}: {str(e)}"
                        task.retry_count += 1
                        logger.error(f" Task #{task.id}: {task.error} (retry {task.retry_count}/{self.max_retries})")

                except httpx.HTTPError as e:
                    task.error = f"HTTP error: {str(e)}"
                    task.retry_count += 1
                    logger.error(f" Task #{task.id}: {task.error} (retry {task.retry_count}/{self.max_retries})")

                except Exception as e:
                    task.error = f"Error: {str(e)}"
                    task.retry_count += 1
                    logger.error(f" Task #{task.id}: {task.error} (retry {task.retry_count}/{self.max_retries})")
                    import traceback
                    logger.info(f"  Full traceback: {traceback.format_exc()}")

                # Exponential backoff with jitter before retry
                if task.retry_count <= self.max_retries:
                    base_delay = min(2 ** task.retry_count, 10)
                    jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
                    await asyncio.sleep(base_delay + jitter)

            # Max retries exceeded
            task.status = TaskStatus.FAILED
            task.end_time = time.time()

            if progress_bar:
                progress_bar.update(1)

            return task

    async def process_all(
        self,
        data_list: List[Any],
        processor_func: Callable,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> tuple[List[Any], ProcessingStats]:
        """
        Xử lý song song tất cả tasks

        Args:
            data_list: List of data items to process (e.g., TranslationChunks)
            processor_func: Async function to process each item
            http_client: Optional HTTP client (will create if not provided)

        Returns:
            Tuple of (results, stats)
        """
        # Create tasks
        self.tasks = [Task(id=i, data=data) for i, data in enumerate(data_list)]
        self.stats = ProcessingStats(total_tasks=len(self.tasks))

        # Setup HTTP client
        close_client = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
            close_client = True

        # Setup progress bar
        progress_bar = None
        if self.show_progress:
            progress_bar = tqdm(
                total=len(self.tasks),
                desc="Processing",
                unit="task",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )

        try:
            # Process all tasks concurrently
            start_time = time.time()

            task_coroutines = [
                self.process_task(task, processor_func, http_client, progress_bar)
                for task in self.tasks
            ]

            # Use return_exceptions=True to prevent fail-fast behavior
            # This allows individual tasks to fail without stopping the entire job
            completed_tasks = await asyncio.gather(*task_coroutines, return_exceptions=True)

            # Update stats and handle exceptions
            for i, result in enumerate(completed_tasks):
                if isinstance(result, Exception):
                    # Task raised an exception
                    logger.error(f" Task {i} failed with exception: {type(result).__name__}: {str(result)}")
                    # Mark task as failed
                    if i < len(self.tasks):
                        self.tasks[i].status = TaskStatus.FAILED
                        self.tasks[i].error = str(result)
                        self.stats.update(self.tasks[i])
                elif isinstance(result, Task):
                    # Task completed normally
                    self.stats.update(result)
                else:
                    logger.warning(f" Unexpected result type for task {i}: {type(result)}")

            self.stats.total_time = time.time() - start_time

            # Extract results (only from successful tasks)
            results = [
                task.result
                for task in completed_tasks
                if task.status == TaskStatus.COMPLETED and task.result is not None
            ]

            return results, self.stats

        finally:
            if progress_bar:
                progress_bar.close()

            if close_client:
                await http_client.aclose()

    def get_failed_tasks(self) -> List[Task]:
        """Get list of failed tasks"""
        return [task for task in self.tasks if task.status == TaskStatus.FAILED]

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def print_summary(self):
        """Print processing summary"""
        logger.info("=" * 50)
        logger.info("PARALLEL PROCESSING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total tasks: {self.stats.total_tasks}")
        logger.info(f"Completed: {self.stats.completed} ({self.stats.completed/max(self.stats.total_tasks, 1)*100:.1f}%)")
        if self.stats.failed > 0:
            logger.error(f"Failed: {self.stats.failed}")
        logger.info(f"Retried: {self.stats.retried}")
        logger.info(f"Total time: {self.stats.total_time:.2f}s")
        logger.info(f"Avg per task: {self.stats.avg_time_per_task:.2f}s")

        if self.stats.cache_hits > 0 or self.stats.cache_misses > 0:
            cache_total = self.stats.cache_hits + self.stats.cache_misses
            cache_rate = self.stats.cache_hits / cache_total * 100
            logger.info(f"Cache hits: {self.stats.cache_hits}/{cache_total} ({cache_rate:.1f}%)")

        logger.info("=" * 50)

        # Show failed tasks details
        failed_tasks = self.get_failed_tasks()
        if failed_tasks:
            logger.info(f"\n⚠️  {len(failed_tasks)} FAILED TASKS:")
            for task in failed_tasks[:10]:  # Show first 10
                logger.info(f"  Task #{task.id}: {task.error}")
            if len(failed_tasks) > 10:
                logger.info(f"  ... and {len(failed_tasks) - 10} more")


class BatchProcessor:
    """Xử lý theo batch với automatic batching"""

    def __init__(self, batch_size: int = 10, max_concurrency: int = 5):
        """
        Args:
            batch_size: Số lượng items mỗi batch
            max_concurrency: Concurrency trong mỗi batch
        """
        self.batch_size = batch_size
        self.processor = ParallelProcessor(max_concurrency=max_concurrency)

    async def process_in_batches(
        self,
        data_list: List[Any],
        processor_func: Callable,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> tuple[List[Any], ProcessingStats]:
        """
        Chia nhỏ thành batches và xử lý tuần tự các batches

        Args:
            data_list: List of data to process
            processor_func: Processing function
            http_client: Optional HTTP client

        Returns:
            Tuple of (all_results, combined_stats)
        """
        # Create batches
        batches = [
            data_list[i:i + self.batch_size]
            for i in range(0, len(data_list), self.batch_size)
        ]

        logger.info(f"\n📦 Processing {len(data_list)} items in {len(batches)} batches")
        logger.info(f"  Batch size: {self.batch_size}")
        logger.info(f"  Concurrency: {self.processor.max_concurrency}")

        all_results = []
        combined_stats = ProcessingStats(total_tasks=len(data_list))

        # Setup HTTP client
        close_client = False
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
            close_client = True

        try:
            for i, batch in enumerate(batches, 1):
                logger.info(f"\n🔄 Processing batch {i}/{len(batches)} ({len(batch)} items)...")

                results, stats = await self.processor.process_all(
                    batch,
                    processor_func,
                    http_client
                )

                all_results.extend(results)

                # Combine stats
                combined_stats.completed += stats.completed
                combined_stats.failed += stats.failed
                combined_stats.retried += stats.retried
                combined_stats.total_time += stats.total_time
                combined_stats.tokens_used += stats.tokens_used
                combined_stats.cache_hits += stats.cache_hits
                combined_stats.cache_misses += stats.cache_misses

            # Calculate final averages
            if combined_stats.completed > 0:
                combined_stats.avg_time_per_task = combined_stats.total_time / combined_stats.completed

            return all_results, combined_stats

        finally:
            if close_client:
                await http_client.aclose()
