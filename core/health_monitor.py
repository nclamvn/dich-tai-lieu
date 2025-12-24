#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Health Monitoring & Cost Tracking for AI Translator Pro

Provides health checks and cost analytics for the translation system.
"""

import time
import psutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import sqlite3


# ============================================================================
# Health Status Data Models
# ============================================================================

@dataclass
class HealthStatus:
    """Overall system health status."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    uptime_seconds: float
    components: Dict[str, Dict[str, Any]]


@dataclass
class CostMetrics:
    """Cost tracking metrics."""
    total_tokens_used: int
    total_cost_usd: float
    cost_by_provider: Dict[str, float]
    cost_by_model: Dict[str, float]
    average_cost_per_job: float
    jobs_processed: int
    time_period: str


# ============================================================================
# Health Monitor
# ============================================================================

class HealthMonitor:
    """System health monitoring and cost tracking."""

    def __init__(self):
        """Initialize health monitor."""
        self.start_time = time.time()

    def check_health(self) -> HealthStatus:
        """
        Perform comprehensive health check.

        Returns:
            HealthStatus with all component statuses
        """
        components = {
            "system": self._check_system_resources(),
            "database": self._check_database(),
            "storage": self._check_storage(),
            "api_connectivity": self._check_api_connectivity(),
        }

        # Determine overall status
        statuses = [comp["status"] for comp in components.values()]
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            uptime_seconds=time.time() - self.start_time,
            components=components
        )

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Determine status based on thresholds
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "unhealthy"
            elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 85:
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            # Check job queue database
            job_db = Path("data/job_queue/job_queue.db")
            if not job_db.exists():
                return {
                    "status": "degraded",
                    "message": "Job queue database not found"
                }

            # Try to connect and query
            conn = sqlite3.connect(str(job_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            conn.close()

            return {
                "status": "healthy",
                "job_count": job_count,
                "database_size_kb": round(job_db.stat().st_size / 1024, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def _check_storage(self) -> Dict[str, Any]:
        """Check storage directories and permissions."""
        try:
            directories = {
                "data": Path("data"),
                "logs": Path("logs"),
                "cache": Path("data/cache"),
            }

            all_ok = True
            details = {}

            for name, path in directories.items():
                if not path.exists():
                    all_ok = False
                    details[name] = "not_found"
                elif not path.is_dir():
                    all_ok = False
                    details[name] = "not_directory"
                else:
                    # Check if writable
                    test_file = path / ".write_test"
                    try:
                        test_file.touch()
                        test_file.unlink()
                        details[name] = "ok"
                    except:
                        all_ok = False
                        details[name] = "not_writable"

            return {
                "status": "healthy" if all_ok else "degraded",
                "directories": details
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def _check_api_connectivity(self) -> Dict[str, Any]:
        """Check API provider connectivity (basic check)."""
        # For internal system, we just check if API keys are configured
        try:
            from config.settings import Settings
            settings = Settings()

            providers = {}
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_key":
                providers["openai"] = "configured"
            if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "your_anthropic_key":
                providers["anthropic"] = "configured"

            if not providers:
                return {
                    "status": "degraded",
                    "message": "No API providers configured",
                    "providers": providers
                }

            return {
                "status": "healthy",
                "providers": providers
            }
        except Exception as e:
            return {
                "status": "degraded",
                "error": str(e)
            }

    def get_cost_metrics(self, time_period_hours: int = 24) -> CostMetrics:
        """
        Get cost metrics for specified time period.

        Args:
            time_period_hours: Time window in hours

        Returns:
            CostMetrics with aggregated cost data
        """
        try:
            # Try to read from analytics database
            analytics_db = Path("data/analytics/analytics.db")
            if not analytics_db.exists():
                return CostMetrics(
                    total_tokens_used=0,
                    total_cost_usd=0.0,
                    cost_by_provider={},
                    cost_by_model={},
                    average_cost_per_job=0.0,
                    jobs_processed=0,
                    time_period=f"{time_period_hours}h"
                )

            conn = sqlite3.connect(str(analytics_db))
            cursor = conn.cursor()

            cutoff_time = time.time() - (time_period_hours * 3600)

            # Get total metrics
            cursor.execute("""
                SELECT
                    COUNT(*) as jobs,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost_usd) as total_cost
                FROM translations
                WHERE timestamp >= ?
            """, (cutoff_time,))

            row = cursor.fetchone()
            jobs_processed = row[0] or 0
            total_tokens = row[1] or 0
            total_cost = row[2] or 0.0

            # Cost by provider (if available)
            cursor.execute("""
                SELECT provider, SUM(cost_usd) as cost
                FROM translations
                WHERE timestamp >= ?
                GROUP BY provider
            """, (cutoff_time,))
            cost_by_provider = {row[0]: row[1] for row in cursor.fetchall()}

            # Cost by model (if available)
            cursor.execute("""
                SELECT model, SUM(cost_usd) as cost
                FROM translations
                WHERE timestamp >= ?
                GROUP BY model
            """, (cutoff_time,))
            cost_by_model = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            avg_cost = total_cost / jobs_processed if jobs_processed > 0 else 0.0

            return CostMetrics(
                total_tokens_used=total_tokens,
                total_cost_usd=round(total_cost, 4),
                cost_by_provider=cost_by_provider,
                cost_by_model=cost_by_model,
                average_cost_per_job=round(avg_cost, 4),
                jobs_processed=jobs_processed,
                time_period=f"{time_period_hours}h"
            )

        except Exception as e:
            # Return empty metrics on error
            return CostMetrics(
                total_tokens_used=0,
                total_cost_usd=0.0,
                cost_by_provider={},
                cost_by_model={},
                average_cost_per_job=0.0,
                jobs_processed=0,
                time_period=f"{time_period_hours}h"
            )


# ============================================================================
# Global Instance
# ============================================================================

_global_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = HealthMonitor()
    return _global_monitor


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    monitor = HealthMonitor()

    # Check health
    health = monitor.check_health()
    print("System Health Check:")
    print(f"  Overall Status: {health.status}")
    print(f"  Uptime: {health.uptime_seconds:.2f}s")
    print(f"\nComponents:")
    for name, status in health.components.items():
        print(f"  {name}: {status['status']}")
        for key, value in status.items():
            if key != "status":
                print(f"    {key}: {value}")

    # Get cost metrics
    costs = monitor.get_cost_metrics(time_period_hours=24)
    print(f"\nCost Metrics (24h):")
    print(f"  Jobs processed: {costs.jobs_processed}")
    print(f"  Total tokens: {costs.total_tokens_used:,}")
    print(f"  Total cost: ${costs.total_cost_usd}")
    print(f"  Average per job: ${costs.average_cost_per_job}")

    print("\n✅ Health monitoring system ready!")
