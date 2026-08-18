"""Small async helpers for keeping the event loop responsive.

Translation jobs run as asyncio tasks on the main event loop. Any synchronous
CPU/IO work (PDF extraction, python-docx / ReportLab rendering) executed
directly inside an `async def` blocks the loop and freezes every other request
and job for its whole duration. `run_blocking` moves that work to a worker
thread via asyncio.to_thread so the loop stays free.

Use it ONLY for genuinely blocking sync calls that are thread-safe (operate on
their own file/args, no shared mutable global state). Do NOT wrap code that is
already async.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def run_blocking(func: Callable[..., T], /, *args, **kwargs) -> Awaitable[T]:
    """Run a blocking sync callable in a worker thread, awaitable from the loop.

    Thin wrapper over asyncio.to_thread (Python 3.9+). Returns the coroutine so
    callers `await run_blocking(fn, a, b, kw=...)`. Exceptions raised in the
    thread propagate to the awaiting coroutine, exactly like a direct call.
    """
    return asyncio.to_thread(func, *args, **kwargs)
