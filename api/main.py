#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI Web Server - REST API for AI Translator Pro.

This module provides the REST API and WebSocket endpoints for the
translation system, including:
- Job management (create, read, update, delete, cancel)
- File upload and analysis
- Queue monitoring and statistics
- Real-time progress updates via WebSocket
- OCR endpoints (deprecated, use hybrid OCR)
- Cache management
- Health monitoring

Usage:
    # Start server
    uvicorn api.main:app --host 0.0.0.0 --port 8000

    # Or run directly
    python -m api.main

API Documentation:
    - OpenAPI docs: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc

Key Endpoints:
    POST /api/jobs - Create translation job
    GET /api/jobs - List all jobs
    GET /api/jobs/{job_id} - Get job details
    POST /api/jobs/{job_id}/cancel - Cancel job
    GET /api/jobs/{job_id}/download/{format} - Download output
    POST /api/upload - Upload file for translation
    POST /api/analyze - Analyze file (word count, language)
    WS /ws - WebSocket for real-time updates

Configuration:
    Environment variables:
    - RATE_LIMIT: API rate limit (default: "60/minute")
    - MAX_UPLOAD_SIZE_MB: Max upload size (default: 50)
    - OPENAI_API_KEY: OpenAI API key
    - ANTHROPIC_API_KEY: Anthropic API key (optional)
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pathlib import Path
import asyncio
import json
import time
import sys
import shutil
import os
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.job_queue import JobQueue, TranslationJob, JobStatus, JobPriority
from core.batch_processor import BatchProcessor, read_document
# Deprecated: DeepSeek OCR has been replaced by hybrid OCR system
# from core.ocr_deepseek import DeepseekOCR, OCRResult
from core.post_formatting.heading_detector import HeadingDetector
from core.cache.chunk_cache import ChunkCache
import re
import math
from docx import Document as DocxDocument

from config.logging_config import get_logger
logger = get_logger(__name__)

# Phase 4.1: Author Mode routes
from api.routes import author

# APS Service (for batch processor)
from api.aps_service import get_aps_service

# APS V2 (Claude-Native Universal Publishing) routes
from api.aps_v2_router import router as aps_v2_router

# Batch Processing routes
# Multi-AI Provider routes
# Glossary and Translation Memory routes (Rich UI Support)
from api.batch_router import router as batch_router
from api.provider_routes import router as provider_router
from api.glossary_router import router as glossary_router
from api.tm_router import router as tm_router
from api.editor_router import router as editor_router

# P1: Authentication and Error Dashboard routes
from api.auth_router import router as auth_router
from api.error_dashboard_router import router as error_router

# P4: Usage tracking, API keys, and Preview routes
from api.usage_router import router as usage_router
from api.api_keys_router import router as api_keys_router
from api.preview_router import router as preview_router

# Book-to-Cinema: AI Movie Maker routes
from api.cinema_api import router as cinema_router

# Screenplay Studio routes
from api.routes.screenplay import router as screenplay_router

# Settings & System routes
from api.routes.settings import router as settings_router
from api.routes.system import router as system_router

# Book Writer routes
from api.book_writer_router import router as book_writer_router

# Prometheus metrics
from api.routes.metrics import router as metrics_router, MetricsMiddleware
from api.routes.book_writer_v2 import router as book_writer_v2_router

# Core route modules (jobs, uploads, batch, health, job outputs)
from api.routes.jobs import router as jobs_router
from api.routes.uploads import router as uploads_router
from api.routes.batch_legacy import router as batch_legacy_router
from api.routes.health import router as health_router
from api.routes.job_outputs import router as job_outputs_router

# Dashboard routes
from api.routes.dashboard import router as dashboard_router

# P1: Error tracking integration
from core.error_integration import (
    track_api_error,
    track_job_error,
    ErrorTrackingContext
)

# =============================================================================
# Pydantic Models for API
# =============================================================================

class JobCreate(BaseModel):
    """Request model for creating a job"""
    job_name: str = Field(..., description="Human-readable job name")
    input_file: str = Field(..., description="Path to input file")
    output_file: str = Field(..., description="Path to output file")
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="vi", description="Target language code")
    priority: int = Field(default=JobPriority.NORMAL, description="Job priority (1-50)")
    provider: str = Field(default="openai", description="AI provider")
    model: str = Field(default="gpt-4o-mini", description="Model name")
    use_smart_tables: bool = Field(default=False, description="Enable Premium Vision Table Reconstruction")
    domain: Optional[str] = Field(default=None, description="Domain (general/stem/finance/literature/medical/technology). Use 'stem' for STEM documents with formulas/code.")
    glossary: Optional[str] = Field(default=None, description="Glossary name")
    concurrency: int = Field(default=5, description="Parallel chunks")
    chunk_size: int = Field(default=3000, description="Chunk size in characters")
    output_format: str = Field(default="txt", description="Output format (txt/docx/pdf/html/md)")
    # Phase 3: Advanced STEM features
    input_type: str = Field(default="native_pdf", description="Input type: native_pdf, scanned_pdf, handwritten_pdf")
    output_mode: str = Field(default="docx_reflow", description="Output mode: pdf_preserve (keep layout), docx_reflow (clean single-column)")
    enable_ocr: bool = Field(default=False, description="Enable OCR for scanned/handwritten documents")
    ocr_mode: str = Field(default="auto", description="OCR mode: auto, paddle, hybrid, mathpix, none")
    enable_quality_check: bool = Field(default=False, description="Enable translation quality validation")
    enable_chemical_formulas: bool = Field(default=True, description="Enable chemical formula detection (STEM mode only)")
    layout_mode: str = Field(default="simple", description="DOCX layout mode: 'simple' (clean reflow) or 'academic' (semantic structure with theorem blocks, proofs, etc.) - Phase 2.0.1")
    equation_rendering_mode: str = Field(default="latex_text", description="Equation rendering mode for academic layout: 'latex_text' (plain text LaTeX) or 'omml' (Word native math format, requires pandoc) - Phase 2.0.3b")

    # UI v1.1: New parameters for enhanced UI
    ui_layout_mode: Optional[str] = Field(default=None, description="UI v1.1 Layout mode: 'basic', 'professional', or 'academic'. Overrides layout_mode and use_ast_pipeline if provided.")
    output_formats: Optional[List[str]] = Field(default=None, description="UI v1.1: List of output formats ['docx', 'pdf']. If not provided, uses output_format field.")
    advanced_options: Optional[Dict[str, Any]] = Field(default=None, description="UI v1.1: Advanced options {chunk_size, concurrency, cache_enabled, quality_validation, enable_book_layout}")

    # MathPix credentials (optional per-job overrides, uses server .env defaults if not provided)
    mathpix_app_id: Optional[str] = Field(default=None, description="MathPix App ID (optional, overrides server default)")
    mathpix_app_key: Optional[str] = Field(default=None, description="MathPix App Key (optional, overrides server default)")


class JobUpdate(BaseModel):
    """Request model for updating a job"""
    status: Optional[str] = None
    priority: Optional[int] = None


class JobResponse(BaseModel):
    """Response model for job data"""
    job_id: str
    job_name: str
    status: str
    priority: int
    progress: float
    source_lang: str
    target_lang: str
    domain: Optional[str] = None  # PHASE 2.1.0 FIX: Add domain field
    input_format: Optional[str] = None  # PHASE 2.1.0 FIX: Add input_format field
    output_format: Optional[str] = None  # PHASE 2.1.0 FIX: Add output_format field
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    quality_score: float
    total_cost_usd: float
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]] = None  # Phase 2.0.4: Include job metadata

    class Config:
        from_attributes = True


class QueueStats(BaseModel):
    """Queue statistics"""
    total: int
    pending: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int


class SystemInfo(BaseModel):
    """System information"""
    version: str
    uptime_seconds: float
    processor_running: bool
    current_jobs: int
    queue_stats: QueueStats


class OCRRequest(BaseModel):
    """Request model for OCR recognition"""
    image_base64: str = Field(..., description="Base64 encoded image")
    language: str = Field(default="auto", description="Language code (auto/vi/en/zh/ja/ko)")
    mode: str = Field(default="accurate", description="Recognition mode (fast/accurate/handwriting)")


class OCRTranslateRequest(BaseModel):
    """Request model for OCR + Translation"""
    image_base64: str = Field(..., description="Base64 encoded image")
    target_lang: str = Field(default="vi", description="Target language code")
    source_lang: str = Field(default="auto", description="Source language (auto detect)")


class OCRResponse(BaseModel):
    """Response model for OCR results"""
    text: str
    confidence: float
    language: str
    processing_time: float
    regions: List[Dict[str, Any]] = []


class OCRTranslateResponse(BaseModel):
    """Response model for OCR + Translation"""
    ocr: Dict[str, Any]
    translation: Dict[str, Any]
    regions: List[Dict[str, Any]] = []


class AnalyzeRequest(BaseModel):
    """Request model for file analysis"""
    file_path: str = Field(..., description="Server path to uploaded file")


class AnalyzeResponse(BaseModel):
    """Response model for file analysis"""
    word_count: int = Field(..., description="Actual word count from extracted text")
    character_count: int = Field(..., description="Character count")
    detected_language: str = Field(..., description="Detected language (Tiếng Anh/Tiếng Việt/Trung/Nhật)")
    chunks_estimate: int = Field(..., description="Estimated number of 3000-word chunks")


# UI v1.1: Progress tracking models
class ProgressStep(BaseModel):
    """Individual processing step"""
    name: str = Field(..., description="Step identifier (upload, ocr, translation, etc.)")
    display_name: str = Field(..., description="Vietnamese display name")
    status: str = Field(..., description="Step status: pending, in_progress, completed, failed")
    progress: Optional[float] = Field(None, description="Step progress (0.0-1.0) for in_progress steps")
    duration: Optional[float] = Field(None, description="Duration in seconds for completed steps")


class JobProgressResponse(BaseModel):
    """Detailed job progress with step-by-step breakdown (UI v1.1)"""
    job_id: str
    job_name: str
    status: str
    current_step: int = Field(..., description="Current step number (1-indexed)")
    total_steps: int = Field(..., description="Total number of steps")
    progress_percent: int = Field(..., description="Overall progress percentage (0-100)")
    steps: List[ProgressStep]
    elapsed_seconds: float = Field(..., description="Time elapsed since job started")
    estimated_remaining_seconds: Optional[float] = Field(None, description="Estimated time remaining")
    output_file: Optional[str] = Field(None, description="Output file path when completed")


# =============================================================================
# CSRF Protection Configuration
# =============================================================================

# Note: We'll load settings lazily in get_csrf_config to avoid circular imports

@CsrfProtect.load_config
def get_csrf_config():
    """Load CSRF configuration — adapts to security_mode."""
    from config.settings import settings

    is_production = settings.security_mode == "production"

    class CsrfSettings(BaseModel):
        secret_key: str = settings.csrf_secret_key
        cookie_name: str = "fastapi-csrf-token"
        cookie_samesite: str = "strict" if is_production else "lax"
        cookie_secure: bool = is_production
        header_name: str = "X-CSRF-Token"

    return CsrfSettings()

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="AI Translator Pro API",
    description="REST API for professional translation system with batch processing",
    version="3.3.1"
)

# Rate limiting (configurable via RATE_LIMIT env var)
# Default: 60 requests per minute per IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "60/minute")]
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CSRF protection exception handler
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """Handle CSRF protection errors"""
    return JSONResponse(
        status_code=403,
        content={"detail": "CSRF token validation failed. Please refresh the page and try again."}
    )

# =============================================================================
# CSRF Token Endpoint
# =============================================================================

@app.get("/api/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    """
    Generate and return CSRF token for client-side requests.

    This endpoint sets a CSRF cookie and returns the token value.
    Frontend must call this before making any POST/PATCH/DELETE requests
    when CSRF protection is enabled.
    """
    response = JSONResponse(content={"message": "CSRF cookie set"})
    try:
        csrf_protect.set_csrf_cookie(response)
    except TypeError:
        # Older versions of fastapi-csrf-protect use generate_csrf()
        token = csrf_protect.generate_csrf()
        response = JSONResponse(content={"csrf_token": token})
    return response


# QA-12: Global exception handler — sanitize error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"Unhandled error [{error_id}]: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={
        "detail": "An internal error occurred. Please try again or contact support.",
        "error_id": error_id,
    })


# QA-16: Body size limit middleware — prevent DoS via large payloads
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        max_size = 50 * 1024 * 1024  # 50MB default for file uploads
        # Stricter limit for JSON text endpoints
        if "/api/v2/publish-text" in request.url.path or "/api/v2/books" in request.url.path:
            max_size = 5 * 1024 * 1024  # 5MB for text
        if int(content_length) > max_size:
            return JSONResponse(status_code=413, content={
                "detail": f"Request too large. Max: {max_size // (1024 * 1024)}MB"
            })
    return await call_next(request)


# Middleware order matters: last added = first executed in Starlette.
# SecurityHeaders must be added BEFORE CORS so CORS runs first (handles preflight).
from config.settings import settings as _app_settings
from api.middleware.security_headers import SecurityHeadersMiddleware

# 1) Security headers (runs second — after CORS has handled preflight)
app.add_middleware(SecurityHeadersMiddleware, security_mode=_app_settings.security_mode)

# 2) CORS (runs first — must handle OPTIONS preflight before anything else)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_app_settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Job-ID", "X-Progress", "Content-Disposition"],
)


# BIZ-04: Audit logging middleware
_AUDIT_SKIP_PREFIXES = ("/_next/", "/ws", "/__nextjs", "/health")


@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and not path.startswith(_AUDIT_SKIP_PREFIXES):
        # Capture values before the async closure (request may be gc'd)
        user_id = getattr(request.state, "user_id", "anonymous")
        ip_address = request.client.host if request.client else None
        action = f"{request.method} {path}"

        async def _write_audit():
            try:
                import asyncio
                from core.services.audit_log import get_audit_logger
                audit = get_audit_logger()
                await asyncio.to_thread(
                    audit.log,
                    action=action,
                    user_id=user_id,
                    resource_type="api",
                    resource_id=path,
                    ip_address=ip_address,
                )
            except Exception:
                pass

        import asyncio
        asyncio.create_task(_write_audit())
    return response


# Phase 4.1: Include Author Mode routes
app.include_router(author.router)
app.include_router(editor_router)

# APS V2: Include Claude-Native Universal Publishing routes
app.include_router(aps_v2_router)


# Startup event to resume pending jobs
@app.on_event("startup")
async def startup_db_integrity_check():
    """Run PRAGMA integrity_check on all SQLite databases at startup."""
    import sqlite3
    from pathlib import Path

    data_dir = Path("data")
    checked = 0
    warnings = []

    if data_dir.exists():
        for db_file in data_dir.rglob("*.db"):
            try:
                conn = sqlite3.connect(str(db_file))
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                checked += 1
                if result[0] != "ok":
                    warnings.append(f"{db_file}: {result[0]}")
            except Exception as e:
                warnings.append(f"{db_file}: {e}")

    if warnings:
        logger.error("=" * 60)
        logger.error("DATABASE INTEGRITY ISSUES DETECTED")
        for w in warnings:
            logger.error(f"  - {w}")
        logger.error("=" * 60)
    else:
        logger.info(f"Database integrity check passed ({checked} databases)")


@app.on_event("startup")
async def startup_security_check():
    """Log security warnings and deployment summary."""
    from config.settings import Settings
    s = Settings()
    border = "=" * 60

    # --- Security warnings ---
    warnings = []
    if s.security_mode == "development":
        warnings.append("SECURITY_MODE=development — authentication is DISABLED")
    if not s.session_auth_enabled:
        warnings.append("SESSION_AUTH_ENABLED=false — all endpoints are publicly accessible")
    if s.session_secret == "INSECURE-DEV-SECRET-CHANGE-IN-PRODUCTION":
        warnings.append("SESSION_SECRET is default insecure value — CHANGE for production")
    if not s.csrf_enabled:
        warnings.append("CSRF_ENABLED=false — CSRF protection is OFF")
    if warnings:
        logger.warning(f"\n{border}")
        logger.warning("SECURITY WARNINGS:")
        for w in warnings:
            logger.warning(f"  ⚠ {w}")
        logger.warning(f"Set SECURITY_MODE=production in .env to enforce security.")
        logger.warning(f"{border}")

    # --- Deployment summary ---
    providers = []
    if s.anthropic_api_key:
        providers.append("Anthropic")
    if s.openai_api_key:
        providers.append("OpenAI")
    if s.google_api_key:
        providers.append("Google")
    logger.info(f"\n{border}")
    logger.info(f"AI Publisher Pro v3.3.1")
    logger.info(f"  Mode:      {s.security_mode}")
    logger.info(f"  Auth:      {'ON' if s.session_auth_enabled else 'OFF'}")
    logger.info(f"  Providers: {', '.join(providers) if providers else 'NONE — configure API keys!'}")
    logger.info(f"  Provider:  {s.provider} / {s.model}")
    logger.info(f"  Features:  cache={'ON' if s.cache_enabled else 'OFF'} tm={'ON' if s.tm_enabled else 'OFF'} glossary={'ON' if s.glossary_enabled else 'OFF'}")
    logger.info(f"{border}")


@app.on_event("startup")
async def startup_resume_jobs():
    """Resume any pending jobs after server restart."""
    try:
        from api.aps_v2_service import get_v2_service
        service = get_v2_service()
        resumed = await service.resume_pending_jobs()
        if resumed > 0:
            logger.info(f"Startup: Resumed {resumed} pending jobs")
    except Exception as e:
        logger.error(f"Startup: Failed to resume jobs: {e}")


@app.on_event("startup")
async def startup_recover_stuck_v1_jobs():
    """QA-24: Mark V1 jobs stuck as 'running' back to 'pending' on restart."""
    # QA-17/QA-27: Start job timeout watchdog
    try:
        from core.services.watchdog import watchdog_loop
        asyncio.create_task(watchdog_loop())
        logger.info("Job timeout watchdog started")
    except Exception as e:
        logger.debug(f"Watchdog start skipped: {e}")

    # QA-24: Recover stuck V1 jobs
    try:
        queue = JobQueue()
        with queue._backend.connection() as conn:
            cursor = conn.execute(
                "UPDATE jobs SET status = 'pending', error = 'Server restarted — job re-queued' "
                "WHERE status = 'running'"
            )
            if cursor.rowcount > 0:
                logger.warning(f"Recovered {cursor.rowcount} stuck V1 jobs → pending")
    except Exception as e:
        logger.debug(f"V1 stuck job recovery skipped: {e}")


# Batch Processing: Include batch job routes
app.include_router(batch_router)

# Multi-AI Provider: Include provider management routes
app.include_router(provider_router, prefix="/api/v2/providers", tags=["AI Providers"])
app.include_router(glossary_router, prefix="/api/glossary", tags=["Glossary"])

# P1: Authentication routes (JWT-based)
app.include_router(auth_router)

# P1: Error Dashboard routes
app.include_router(error_router)
app.include_router(tm_router)

# P4: Usage tracking, API keys, and Preview
app.include_router(usage_router)
app.include_router(api_keys_router)
app.include_router(preview_router)

# Book-to-Cinema: AI Movie Maker
app.include_router(cinema_router)

# Screenplay Studio
app.include_router(screenplay_router)

# Settings & System
app.include_router(settings_router)
app.include_router(system_router)

# Book Writer
app.include_router(book_writer_router)
app.include_router(book_writer_v2_router)

# Dashboard
app.include_router(dashboard_router)

# Core route modules
app.include_router(jobs_router)
app.include_router(uploads_router)
app.include_router(batch_legacy_router)
app.include_router(health_router)
app.include_router(job_outputs_router)
app.include_router(metrics_router)

# Metrics middleware — records request count, latency, error rate
app.add_middleware(MetricsMiddleware)

# Legacy ui/ removed — frontend is Next.js at frontend/

# Global state
queue = JobQueue()
processor = None
start_time = time.time()
websocket_connections: List[WebSocket] = []

# Initialize chunk cache
cache_db_path = Path(__file__).parent.parent / "data" / "cache" / "chunks.db"
chunk_cache = ChunkCache(cache_db_path)


# =============================================================================
# WebSocket Manager
# =============================================================================

class ConnectionManager:
    """
    Manage WebSocket connections for real-time updates.

    Handles client connections and broadcasts job progress, status
    changes, and queue statistics to all connected clients.

    Attributes:
        active_connections: List of currently connected WebSocket clients.

    Example:
        >>> manager = ConnectionManager()
        >>> await manager.connect(websocket)
        >>> await manager.broadcast({"event": "job_completed", "job_id": "123"})
    """

    def __init__(self):
        """Initialize connection manager with empty connection list."""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from the active list.

        Args:
            websocket: The WebSocket connection to remove.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Dictionary message to send as JSON.

        Note:
            Silently ignores send failures to individual clients.
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Silently ignore connection errors (client may have disconnected)
                pass


manager = ConnectionManager()

# Initialize APS service with queue and websocket manager
# (BatchProcessor will be added when start_processor is called)
_aps_service = get_aps_service(
    job_queue=queue,
    batch_processor=None,  # Will be set when processor starts
    websocket_manager=manager,
)
logger.info("APS Service pre-initialized (awaiting BatchProcessor)")


# =============================================================================
# Security & Authentication (Session-based)
# =============================================================================

from api.security import security_manager, SessionInfo, get_optional_session

class LoginRequest(BaseModel):
    """Simple login request - for development/internal use"""
    username: str = Field(default="user", description="Username (optional for internal)")
    organization: str = Field(default="Default Organization", description="Organization name")


@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """
    Create a session (simple login for internal deployment)

    For internal deployment: No password required
    For production: Add password validation here

    Returns session token to use in X-Session-Token header
    """
    # Create session
    session_token = security_manager.create_session(
        user_id=login_data.username,
        username=login_data.username,
        organization=login_data.organization
    )

    return {
        "session_token": session_token,
        "username": login_data.username,
        "organization": login_data.organization,
        "expires_in_hours": 8,
        "message": "Login successful. Include 'X-Session-Token' header in requests."
    }


@app.post("/api/auth/logout")
async def logout(session: SessionInfo = Depends(get_optional_session)):
    """Logout - invalidate session"""
    if session:
        security_manager.invalidate_session(session.session_id)

    return {"message": "Logged out successfully"}


@app.get("/api/auth/session")
async def get_session_info(session: SessionInfo = Depends(get_optional_session)):
    """Get current session information"""
    if not session:
        return {
            "authenticated": False,
            "message": "No active session"
        }

    return {
        "authenticated": True,
        "username": session.username,
        "organization": session.organization,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "active_sessions": security_manager.get_active_sessions_count()
    }


# =============================================================================
# API Endpoints - Jobs
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API docs — frontend runs separately via Next.js"""
    return RedirectResponse(url="/docs")


# =============================================================================
# API Endpoints - Queue & System
# =============================================================================

@app.get("/api/queue/stats", response_model=QueueStats)
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


@app.get("/api/system/info", response_model=SystemInfo)
async def get_system_info():
    """Get system information"""
    stats = queue.get_queue_stats()

    return SystemInfo(
        version="3.3.1",
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


@app.get("/api/system/status")
async def get_system_status():
    """
    Get system capabilities and feature availability (UI v1.1)

    Returns:
        System status including:
        - pandoc_available: Whether pandoc is installed (for OMML equation rendering)
        - libreoffice_available: Whether LibreOffice is installed (for PDF export)
        - advanced_book_layout_enabled: Whether advanced book layout is enabled
        - supported_formats: List of supported output formats
        - features: Dictionary of available features
    """
    import shutil
    import os
    from config.settings import settings

    # Check if pandoc is available
    import os
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
            "ast_pipeline": True,  # Always available
            "professional_typography": True  # Phase 2.0.7
        }
    }


# =============================================================================
# Cache Management Endpoints
# =============================================================================

@app.get("/api/cache/stats")
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


@app.post("/api/cache/clear")
@limiter.limit("5/minute")  # Rate limit to prevent abuse
async def clear_cache(request: Request):
    """
    Clear all translation cache entries

    This will remove all cached translations, forcing fresh translations
    on the next request. Use this when:
    - Translation quality is poor and needs to be redone
    - Translation failed but cache still contains the error
    - You want to force a complete re-translation

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


@app.post("/api/processor/start")
async def start_processor(
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """Start the batch processor"""
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    global processor

    if processor and processor.is_running:
        raise HTTPException(status_code=400, detail="Processor is already running")

    processor = BatchProcessor(queue=queue, max_concurrent_jobs=1, websocket_manager=manager)

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


@app.post("/api/processor/stop")
async def stop_processor(
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """Stop the batch processor"""
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    global processor

    if not processor or not processor.is_running:
        raise HTTPException(status_code=400, detail="Processor is not running")

    processor.stop()
    return {"message": "Batch processor stopped"}


# =============================================================================
# API Endpoints - OCR (Deepseek)
# =============================================================================

@app.post("/api/ocr/recognize", response_model=OCRResponse)
async def ocr_recognize(request: OCRRequest):
    """
    Nhận dạng văn bản từ ảnh (OCR)

    - **image_base64**: Ảnh đã encode base64
    - **language**: Ngôn ngữ (auto/vi/en/zh/ja/ko)
    - **mode**: Chế độ nhận dạng (fast/accurate/handwriting)

    Returns OCR result với văn bản, độ tin cậy, ngôn ngữ phát hiện
    """
    import os
    import tempfile
    import base64

    # Get Deepseek API key from environment
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_key:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY not configured. Set environment variable."
        )

    # Decode base64 image and save to temp file
    try:
        image_data = base64.b64decode(request.image_base64)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    # Perform OCR
    try:
        # Deprecated: DeepSeek OCR replaced by hybrid system
        raise HTTPException(status_code=501, detail="DeepSeek OCR is deprecated. Use hybrid OCR in translation jobs instead.")
        # ocr = DeepseekOCR(api_key=deepseek_key)
        # result = await ocr.recognize_image(
        #     tmp_path,
        #     language=request.language,
        #     mode=request.mode
        # )

        # Clean up temp file
        Path(tmp_path).unlink()

        return OCRResponse(
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            processing_time=result.processing_time,
            regions=result.regions
        )
    except Exception as e:
        # Clean up temp file
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@app.post("/api/ocr/handwriting", response_model=OCRResponse)
async def ocr_handwriting(request: OCRRequest):
    """
    Nhận dạng chữ viết tay (Handwriting Recognition)

    Tối ưu hóa cho:
    - Chữ viết tay tiếng Việt
    - Ghi chú học tập
    - Biên bản họp

    Uses handwriting-optimized mode automatically.
    """
    # Force handwriting mode
    request.mode = "handwriting"
    return await ocr_recognize(request)


@app.post("/api/ocr/translate", response_model=OCRTranslateResponse)
async def ocr_translate(request: OCRTranslateRequest):
    """
    Nhận dạng ảnh và dịch văn bản (OCR + Translation)

    Workflow:
    1. OCR: Nhận dạng văn bản từ ảnh
    2. Detect: Phát hiện ngôn ngữ nguồn
    3. Translate: Dịch sang ngôn ngữ đích

    - **image_base64**: Ảnh đã encode base64
    - **target_lang**: Ngôn ngữ đích (vi/en/zh)
    - **source_lang**: Ngôn ngữ nguồn (auto detect)
    """
    import os
    import tempfile
    import base64

    # Get API keys
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not deepseek_key:
        raise HTTPException(
            status_code=500,
            detail="DEEPSEEK_API_KEY not configured"
        )
    if not openai_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured for translation"
        )

    # Decode base64 image
    try:
        image_data = base64.b64decode(request.image_base64)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    # Perform OCR + Translation
    try:
        # Deprecated: DeepSeek OCR replaced by hybrid system
        raise HTTPException(status_code=501, detail="DeepSeek OCR+translate is deprecated. Use hybrid OCR in translation jobs instead.")
        # ocr = DeepseekOCR(api_key=deepseek_key)
        # result = await ocr.recognize_with_translation(
        #     tmp_path,
        #     target_lang=request.target_lang,
        #     translator_api_key=openai_key
        # )

        # Clean up
        Path(tmp_path).unlink()

        return OCRTranslateResponse(
            ocr=result["ocr"],
            translation=result["translation"],
            regions=result["regions"]
        )
    except Exception as e:
        # Clean up
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        raise HTTPException(status_code=500, detail=f"OCR/Translation failed: {str(e)}")


@app.post("/api/ocr/upload")
@limiter.limit("30/minute")
async def ocr_upload(request: Request, file: UploadFile = File(...)):
    """
    Upload ảnh để OCR (alternative to base64)

    Accepts: JPG, PNG, HEIC
    Max size: 10MB

    Returns base64 encoded image for use with other OCR endpoints.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/heic"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Read file
    contents = await file.read()

    # Check size (configurable via MAX_OCR_IMAGE_SIZE_MB env var, default 10MB)
    max_size_mb = int(os.getenv("MAX_OCR_IMAGE_SIZE_MB", "10"))
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {max_size_mb}MB)")

    # Encode to base64
    import base64
    encoded = base64.b64encode(contents).decode('utf-8')

    return {
        "filename": file.filename,
        "size": len(contents),
        "content_type": file.content_type,
        "base64": encoded
    }


# =============================================================================
# WebSocket Endpoint - Real-time Updates
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates

    Sends updates about job status changes, queue statistics, and system events.

    Clients can send JSON messages:
    - {"action": "subscribe", "job_id": "abc123"} to filter events for a specific job
    - {"action": "unsubscribe"} to receive all events again

    Authentication: When session_auth_enabled, requires ?token=<session_token> query param.
    """
    # Authenticate WebSocket connection when auth is enabled
    from config.settings import get_settings
    ws_settings = get_settings()
    if ws_settings.session_auth_enabled:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return
        try:
            security_manager.validate_session(token)
        except HTTPException:
            await websocket.close(code=4001, reason="Invalid or expired session")
            return

    await manager.connect(websocket)

    try:
        # Send initial stats
        stats = queue.get_queue_stats()
        await websocket.send_json({
            "event": "connected",
            "stats": stats
        })

        # Keep connection alive and send periodic updates
        while True:
            # Wait for messages (or timeout)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                # Handle client messages if needed
            except asyncio.TimeoutError:
                # Send periodic stats update
                stats = queue.get_queue_stats()
                await websocket.send_json({
                    "event": "stats_update",
                    "stats": stats,
                    "timestamp": time.time()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting AI Translator Pro API Server...")
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Dashboard: http://localhost:8000/")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
