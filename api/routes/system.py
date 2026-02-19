"""
System admin, cache management, and processor control endpoints.
"""

import asyncio
import os
import shutil
import time

from fastapi import APIRouter, HTTPException, Request

from api.deps import queue, manager, chunk_cache, start_time, get_processor, set_processor
from api.models import QueueStats, SystemInfo
from core.job_queue import JobStatus
from core.translation import get_engine_manager
from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["System"])


@router.get("/api/queue/stats", response_model=QueueStats)
async def get_queue_stats():
    """Get queue statistics"""
    stats = queue.get_queue_stats()

    return QueueStats(
        total=stats.get('total', 0),
        pending=stats.get(JobStatus.PENDING, 0),
        queued=stats.get(JobStatus.QUEUED, 0),
        running=stats.get(JobStatus.RUNNING, 0),
        completed=stats.get(JobStatus.COMPLETED, 0),
        failed=stats.get(JobStatus.FAILED, 0),
        cancelled=stats.get(JobStatus.CANCELLED, 0)
    )


@router.get("/api/system/info", response_model=SystemInfo)
async def get_system_info():
    """Get system information"""
    stats = queue.get_queue_stats()
    processor = get_processor()

    return SystemInfo(
        version="2.4.0",
        uptime_seconds=time.time() - start_time,
        processor_running=processor is not None and processor.is_running,
        current_jobs=len(processor.current_jobs) if processor else 0,
        queue_stats=QueueStats(
            total=stats.get('total', 0),
            pending=stats.get(JobStatus.PENDING, 0),
            queued=stats.get(JobStatus.QUEUED, 0),
            running=stats.get(JobStatus.RUNNING, 0),
            completed=stats.get(JobStatus.COMPLETED, 0),
            failed=stats.get(JobStatus.FAILED, 0),
            cancelled=stats.get(JobStatus.CANCELLED, 0)
        )
    )


@router.get("/api/engines")
async def get_available_engines():
    """
    Get list of available translation engines.

    Returns list of engines with their status and capabilities.
    Used by UI to populate engine selector dropdown.
    """
    try:
        engine_manager = get_engine_manager()
        return engine_manager.get_available_engines()
    except Exception as e:
        logger.error(f"Failed to get engines: {e}")
        return [
            {
                "id": "cloud_api_auto",
                "name": "Cloud API (Auto)",
                "available": True,
                "status": "available",
                "languages_count": 55,
                "offline": False,
                "cost_per_token": 0.001
            }
        ]


@router.get("/api/system/status")
async def get_system_status():
    """
    Get system capabilities and feature availability (UI v1.1)

    Returns:
        System status including pandoc, libreoffice, feature flags, supported formats
    """
    from config.settings import settings

    # Check if pandoc is available
    pandoc_available = (
        shutil.which("pandoc") is not None or
        os.path.exists("/opt/homebrew/bin/pandoc") or
        os.path.exists("/usr/local/bin/pandoc")
    )
    logger.info(f"Pandoc available: {pandoc_available}")

    # Check if LibreOffice is available
    libreoffice_available = False
    try:
        from core.export.pdf_adapter import is_libreoffice_available
        libreoffice_available = is_libreoffice_available()
    except ImportError:
        pass

    # Check advanced book layout setting
    try:
        advanced_book_layout_enabled = settings.enable_advanced_book_layout
    except AttributeError:
        advanced_book_layout_enabled = False

    # Build supported formats list
    supported_formats = ["docx"]
    if libreoffice_available:
        supported_formats.append("pdf")

    return {
        "pandoc_available": pandoc_available,
        "libreoffice_available": libreoffice_available,
        "advanced_book_layout_enabled": advanced_book_layout_enabled,
        "supported_formats": supported_formats,
        "features": {
            "omml_equations": pandoc_available,
            "pdf_export": libreoffice_available,
            "book_layout": advanced_book_layout_enabled,
            "ast_pipeline": True,
            "professional_typography": True
        }
    }


@router.get("/api/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics

    Returns:
        Cache statistics including total entries, hit rate, and database size
    """
    try:
        stats = chunk_cache.stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/api/cache/clear")
async def clear_cache(request: Request):
    """
    Clear all translation cache entries

    Rate limited to 5 requests per minute to prevent abuse.
    """
    try:
        chunk_cache.clear()
        stats = chunk_cache.stats()

        return {
            "success": True,
            "message": "Cache cleared successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.post("/api/processor/start")
async def start_processor_endpoint(
    request: Request = None
):
    """Start the batch processor"""
    from core.batch_processor import BatchProcessor
    from api.aps_service import get_aps_service

    processor = get_processor()

    if processor and processor.is_running:
        raise HTTPException(status_code=400, detail="Processor is already running")

    processor = BatchProcessor(queue=queue, max_concurrent_jobs=1, websocket_manager=manager)
    set_processor(processor)

    # Initialize APS service with shared components
    aps_service = get_aps_service(
        job_queue=queue,
        batch_processor=processor,
        websocket_manager=manager,
        force_reinit=True,
    )
    logger.info("APS Service initialized with shared BatchProcessor")

    # Start processor in background without blocking the response
    asyncio.create_task(processor.start(continuous=True))

    return {"message": "Batch processor started", "aps_integration": True}


@router.post("/api/processor/stop")
async def stop_processor_endpoint(
    request: Request = None
):
    """Stop the batch processor"""
    processor = get_processor()

    if not processor or not processor.is_running:
        raise HTTPException(status_code=400, detail="Processor is not running")

    processor.stop()
    return {"message": "Batch processor stopped"}
