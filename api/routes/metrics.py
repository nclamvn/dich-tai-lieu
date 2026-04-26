"""
Prometheus metrics endpoint for monitoring.

Exposes /metrics in Prometheus exposition format with:
- HTTP request count and latency
- Active jobs gauge
- Error rate tracking
"""

import time
from collections import defaultdict
from typing import Dict

from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


router = APIRouter(tags=["Monitoring"])


# ── In-process metrics storage (no external dependency needed) ──

class MetricsCollector:
    """Simple in-process metrics collector (no prometheus_client dependency)."""

    def __init__(self):
        self.request_count: Dict[str, int] = defaultdict(int)
        self.request_errors: Dict[str, int] = defaultdict(int)
        self.request_latency_sum: Dict[str, float] = defaultdict(float)
        self.request_latency_count: Dict[str, int] = defaultdict(int)
        self.startup_time = time.time()

    def record_request(self, method: str, path: str, status: int, duration: float):
        key = f'{method} {path}'
        self.request_count[key] += 1
        self.request_latency_sum[key] += duration
        self.request_latency_count[key] += 1
        if status >= 400:
            self.request_errors[key] += 1

    def render_prometheus(self) -> str:
        """Render metrics in Prometheus exposition format."""
        lines = []
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, count in sorted(self.request_count.items()):
            method, path = key.split(" ", 1)
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("")
        lines.append("# HELP http_request_errors_total Total HTTP 4xx/5xx errors")
        lines.append("# TYPE http_request_errors_total counter")
        for key, count in sorted(self.request_errors.items()):
            method, path = key.split(" ", 1)
            lines.append(
                f'http_request_errors_total{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("")
        lines.append("# HELP http_request_duration_seconds HTTP request latency")
        lines.append("# TYPE http_request_duration_seconds summary")
        for key in sorted(self.request_latency_sum.keys()):
            method, path = key.split(" ", 1)
            total = self.request_latency_sum[key]
            count = self.request_latency_count[key]
            avg = total / count if count > 0 else 0
            lines.append(
                f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.4f}'
            )
            lines.append(
                f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
            )

        lines.append("")
        lines.append("# HELP app_uptime_seconds Application uptime")
        lines.append("# TYPE app_uptime_seconds gauge")
        lines.append(f"app_uptime_seconds {time.time() - self.startup_time:.1f}")

        lines.append("")
        return "\n".join(lines) + "\n"


# Global collector instance
metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to record request metrics."""

    # Skip metrics for these paths to avoid noise
    SKIP_PREFIXES = ("/metrics", "/_next/", "/__nextjs", "/favicon")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PREFIXES):
            return await call_next(request)

        # Normalize path: replace UUIDs/IDs with {id} for aggregation
        normalized = self._normalize_path(path)

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        metrics.record_request(request.method, normalized, response.status_code, duration)
        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Replace UUIDs and numeric IDs with placeholders for metric aggregation."""
        import re
        # Replace UUID patterns
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}', path
        )
        # Replace numeric-only segments
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        return path


@router.get("/metrics")
async def prometheus_metrics():
    """Expose metrics in Prometheus exposition format."""
    return Response(
        content=metrics.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
