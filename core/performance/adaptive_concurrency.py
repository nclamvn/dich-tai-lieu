"""
Adaptive Concurrency Tuner Module

Dynamically adjusts concurrency levels based on real-time performance metrics.
Uses latency × throughput optimization to find optimal parallelism.
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from collections import deque
from statistics import mean, stdev


@dataclass
class ConcurrencyMetrics:
    """
    Real-time performance metrics for concurrency tuning

    Attributes:
        timestamp: When the metric was recorded
        concurrency_level: Number of concurrent tasks
        latency_ms: Average latency in milliseconds
        throughput_per_sec: Tasks completed per second
        success_rate: Ratio of successful tasks (0.0 - 1.0)
        error_count: Number of errors in this window
        optimization_score: latency × throughput (higher is better)
    """
    timestamp: float
    concurrency_level: int
    latency_ms: float
    throughput_per_sec: float
    success_rate: float
    error_count: int = 0

    @property
    def optimization_score(self) -> float:
        """
        Calculate optimization score

        Higher score = better performance
        Formula: throughput / latency (normalize to avoid division issues)
        """
        if self.latency_ms <= 0:
            return 0.0
        # Normalize: throughput per second / (latency in seconds)
        latency_sec = self.latency_ms / 1000.0
        return self.throughput_per_sec / latency_sec if latency_sec > 0 else 0.0


@dataclass
class TuningConfig:
    """
    Configuration for adaptive concurrency tuning

    Attributes:
        min_concurrency: Minimum concurrent tasks (safety floor)
        max_concurrency: Maximum concurrent tasks (safety ceiling)
        initial_concurrency: Starting concurrency level
        window_size: Number of recent metrics to consider
        increase_threshold: Optimization score improvement to trigger increase
        decrease_threshold: Optimization score degradation to trigger decrease
        increase_step: How much to increase concurrency (additive)
        decrease_factor: How much to decrease concurrency (multiplicative)
        min_samples_before_tuning: Minimum metrics needed before adjusting
        stability_window: Number of stable metrics before increasing again
    """
    min_concurrency: int = 1
    max_concurrency: int = 50
    initial_concurrency: int = 5
    window_size: int = 10
    increase_threshold: float = 1.1  # 10% improvement
    decrease_threshold: float = 0.9  # 10% degradation
    increase_step: int = 2  # Additive increase
    decrease_factor: float = 0.75  # Multiplicative decrease (reduce by 25%)
    min_samples_before_tuning: int = 5
    stability_window: int = 3


class AdaptiveConcurrencyTuner:
    """
    Dynamically tune concurrency based on performance metrics

    This tuner uses an AIMD (Additive Increase, Multiplicative Decrease) algorithm:
    - When performance improves: slowly increase concurrency
    - When performance degrades: quickly decrease concurrency
    - Maintains a sliding window of recent metrics for trend analysis

    Example:
        tuner = AdaptiveConcurrencyTuner()

        # Record metrics during processing
        tuner.record_task_completion(latency_ms=150, success=True)

        # Get current recommendation
        optimal_concurrency = tuner.get_optimal_concurrency()

        # Get performance stats
        stats = tuner.get_statistics()
    """

    def __init__(self, config: Optional[TuningConfig] = None):
        """
        Initialize the adaptive concurrency tuner

        Args:
            config: Tuning configuration (uses defaults if None)
        """
        self.config = config or TuningConfig()

        # Current state
        self.current_concurrency = self.config.initial_concurrency
        self.metrics_history: deque[ConcurrencyMetrics] = deque(
            maxlen=self.config.window_size
        )

        # Performance tracking
        self._task_count = 0
        self._success_count = 0
        self._error_count = 0
        self._latencies: List[float] = []
        self._window_start_time = time.time()

        # Tuning state
        self._last_adjustment_time = time.time()
        self._stable_metrics_count = 0
        self._best_score = 0.0

    def record_task_completion(
        self,
        latency_ms: float,
        success: bool = True
    ):
        """
        Record completion of a single task

        Args:
            latency_ms: Task latency in milliseconds
            success: Whether the task succeeded
        """
        self._task_count += 1
        self._latencies.append(latency_ms)

        if success:
            self._success_count += 1
        else:
            self._error_count += 1

        # Update metrics periodically (every 10 tasks or 5 seconds)
        if (self._task_count % 10 == 0 or
            time.time() - self._window_start_time >= 5.0):
            self._update_metrics()

    def _update_metrics(self):
        """
        Calculate and store current performance metrics
        """
        if not self._latencies:
            return

        # Calculate metrics
        current_time = time.time()
        window_duration = current_time - self._window_start_time

        if window_duration <= 0:
            return

        avg_latency = mean(self._latencies)
        throughput = self._task_count / window_duration
        success_rate = self._success_count / self._task_count if self._task_count > 0 else 0.0

        # Create metrics snapshot
        metrics = ConcurrencyMetrics(
            timestamp=current_time,
            concurrency_level=self.current_concurrency,
            latency_ms=avg_latency,
            throughput_per_sec=throughput,
            success_rate=success_rate,
            error_count=self._error_count
        )

        self.metrics_history.append(metrics)

        # Update best score
        if metrics.optimization_score > self._best_score:
            self._best_score = metrics.optimization_score

        # Reset window
        self._latencies = []
        self._task_count = 0
        self._success_count = 0
        self._error_count = 0
        self._window_start_time = current_time

    def get_optimal_concurrency(self) -> int:
        """
        Get the current optimal concurrency level

        This method analyzes recent metrics and may adjust concurrency
        based on the AIMD algorithm.

        Returns:
            Recommended concurrency level
        """
        # Need enough samples before tuning
        if len(self.metrics_history) < self.config.min_samples_before_tuning:
            return self.current_concurrency

        # Analyze recent trend
        should_increase, should_decrease = self._analyze_trend()

        # Apply AIMD algorithm
        if should_increase:
            self._increase_concurrency()
        elif should_decrease:
            self._decrease_concurrency()

        return self.current_concurrency

    def _analyze_trend(self) -> Tuple[bool, bool]:
        """
        Analyze performance trend to decide on adjustment

        Returns:
            (should_increase, should_decrease) tuple
        """
        if len(self.metrics_history) < 2:
            return (False, False)

        # Get recent metrics
        recent_metrics = list(self.metrics_history)[-3:]
        current_metric = recent_metrics[-1]

        # Calculate average score of recent window
        recent_scores = [m.optimization_score for m in recent_metrics]
        avg_recent_score = mean(recent_scores)

        # Check success rate - decrease if too many errors
        if current_metric.success_rate < 0.85:  # Less than 85% success
            return (False, True)

        # Check if performance is improving
        if len(self.metrics_history) >= self.config.min_samples_before_tuning:
            older_metrics = list(self.metrics_history)[:-3]
            if older_metrics:
                older_scores = [m.optimization_score for m in older_metrics]
                avg_older_score = mean(older_scores)

                # Performance improved significantly
                if avg_recent_score >= avg_older_score * self.config.increase_threshold:
                    self._stable_metrics_count += 1
                    # Only increase if we've been stable
                    if self._stable_metrics_count >= self.config.stability_window:
                        return (True, False)

                # Performance degraded significantly
                elif avg_recent_score <= avg_older_score * self.config.decrease_threshold:
                    self._stable_metrics_count = 0
                    return (False, True)

        return (False, False)

    def _increase_concurrency(self):
        """
        Increase concurrency using additive increase
        """
        new_concurrency = min(
            self.current_concurrency + self.config.increase_step,
            self.config.max_concurrency
        )

        if new_concurrency != self.current_concurrency:
            self.current_concurrency = new_concurrency
            self._last_adjustment_time = time.time()
            self._stable_metrics_count = 0

    def _decrease_concurrency(self):
        """
        Decrease concurrency using multiplicative decrease
        """
        new_concurrency = max(
            int(self.current_concurrency * self.config.decrease_factor),
            self.config.min_concurrency
        )

        if new_concurrency != self.current_concurrency:
            self.current_concurrency = new_concurrency
            self._last_adjustment_time = time.time()
            self._stable_metrics_count = 0

    def get_statistics(self) -> dict:
        """
        Get comprehensive performance statistics

        Returns:
            Dictionary with performance metrics and tuning state
        """
        if not self.metrics_history:
            return {
                'current_concurrency': self.current_concurrency,
                'metrics_collected': 0,
                'status': 'warming_up'
            }

        recent_metrics = list(self.metrics_history)
        latest = recent_metrics[-1]

        # Calculate aggregates
        avg_latency = mean([m.latency_ms for m in recent_metrics])
        avg_throughput = mean([m.throughput_per_sec for m in recent_metrics])
        avg_success_rate = mean([m.success_rate for m in recent_metrics])

        # Latency variance (stability indicator)
        latency_variance = stdev([m.latency_ms for m in recent_metrics]) if len(recent_metrics) > 1 else 0.0

        return {
            'current_concurrency': self.current_concurrency,
            'metrics_collected': len(self.metrics_history),
            'latest_latency_ms': latest.latency_ms,
            'latest_throughput': latest.throughput_per_sec,
            'latest_optimization_score': latest.optimization_score,
            'avg_latency_ms': avg_latency,
            'avg_throughput': avg_throughput,
            'avg_success_rate': avg_success_rate,
            'latency_variance': latency_variance,
            'best_score': self._best_score,
            'stable_metrics_count': self._stable_metrics_count,
            'time_since_last_adjustment': time.time() - self._last_adjustment_time,
            'status': 'tuning' if len(recent_metrics) >= self.config.min_samples_before_tuning else 'collecting'
        }

    def reset(self):
        """
        Reset the tuner to initial state

        Useful when starting a new job or after significant changes.
        """
        self.current_concurrency = self.config.initial_concurrency
        self.metrics_history.clear()
        self._task_count = 0
        self._success_count = 0
        self._error_count = 0
        self._latencies = []
        self._window_start_time = time.time()
        self._last_adjustment_time = time.time()
        self._stable_metrics_count = 0
        self._best_score = 0.0


# Example usage and testing
if __name__ == "__main__":
    import random

    print("Adaptive Concurrency Tuner - Demo")
    print("=" * 80)

    # Create tuner with custom config
    config = TuningConfig(
        min_concurrency=1,
        max_concurrency=20,
        initial_concurrency=5,
        window_size=10,
        min_samples_before_tuning=3
    )

    tuner = AdaptiveConcurrencyTuner(config)

    print(f"Initial concurrency: {tuner.current_concurrency}")
    print("\nSimulating task completions...\n")

    # Simulate workload with varying performance
    for phase in range(5):
        print(f"--- Phase {phase + 1} ---")

        # Simulate different performance characteristics per phase
        if phase == 0:
            # Warm-up phase: moderate performance
            base_latency = 200
            latency_variance = 50
        elif phase == 1:
            # Improvement: lower latency
            base_latency = 150
            latency_variance = 30
        elif phase == 2:
            # Optimal: best performance
            base_latency = 100
            latency_variance = 20
        elif phase == 3:
            # Degradation: increased latency
            base_latency = 250
            latency_variance = 80
        else:
            # Recovery: moderate performance
            base_latency = 180
            latency_variance = 40

        # Record 50 tasks for this phase
        for i in range(50):
            latency = max(10, base_latency + random.gauss(0, latency_variance))
            success = random.random() > 0.05  # 95% success rate

            tuner.record_task_completion(latency_ms=latency, success=success)

            # Check optimal concurrency periodically
            if i % 10 == 0:
                optimal = tuner.get_optimal_concurrency()

        # Print phase statistics
        stats = tuner.get_statistics()
        print(f"Concurrency: {stats['current_concurrency']}")
        print(f"Avg Latency: {stats['avg_latency_ms']:.1f} ms")
        print(f"Avg Throughput: {stats['avg_throughput']:.2f} tasks/sec")
        print(f"Success Rate: {stats['avg_success_rate']:.1%}")
        print(f"Optimization Score: {stats['latest_optimization_score']:.2f}")
        print(f"Status: {stats['status']}")
        print()

    print("=" * 80)
    print("✓ Demo complete!")
    print("\nFinal statistics:")
    final_stats = tuner.get_statistics()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")
