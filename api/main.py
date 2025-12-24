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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
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
from api.batch_router import router as batch_router

# Multi-AI Provider routes
from api.provider_routes import router as provider_router


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
    """Load CSRF configuration"""
    from config.settings import settings

    class CsrfSettings(BaseModel):
        secret_key: str = settings.csrf_secret_key
        cookie_name: str = "fastapi-csrf-token"
        cookie_samesite: str = "lax"
        cookie_secure: bool = False  # Set to True in production with HTTPS
        header_name: str = "X-CSRF-Token"

    return CsrfSettings()

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="AI Translator Pro API",
    description="REST API for professional translation system with batch processing",
    version="2.4.0"
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
# CSRF Token Endpoint - TEMPORARILY DISABLED FOR DEBUGGING
# =============================================================================

# @app.get("/api/csrf-token")
# async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
#     """
#     Generate and return CSRF token for client-side requests
#
#     This endpoint sets a CSRF cookie and returns the token value.
#     Frontend must call this before making any POST/PATCH/DELETE requests.
#     """
#     response = JSONResponse(content={"message": "CSRF cookie set"})
#     csrf_protect.set_csrf_cookie(response)
#     return response

# CORS middleware - Restricted to allowed origins
# Add more origins as needed for production
ALLOWED_ORIGINS = [
    "https://prismy.in",
    "https://www.prismy.in",
    "https://ai-translator-api.onrender.com",
    "https://ai-translator-ui.onrender.com",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8000",
    "http://localhost:5173",  # Vite dev server for APS UI
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # APS UI alternative port
    "http://127.0.0.1:3000",
    "http://localhost:4000",  # APS UI port 4000
    "http://127.0.0.1:4000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Phase 4.1: Include Author Mode routes
app.include_router(author.router)

# APS V2: Include Claude-Native Universal Publishing routes
app.include_router(aps_v2_router)


# Startup event to resume pending jobs
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


# Batch Processing: Include batch job routes
app.include_router(batch_router)

# Multi-AI Provider: Include provider management routes
app.include_router(provider_router)

# UI Page Routes (for clean URLs)
ui_path = Path(__file__).parent.parent / "ui"


@app.get("/app", include_in_schema=False)
async def publisher_studio():
    """Serve Publisher Studio page"""
    app_html = ui_path / "app.html"
    if app_html.exists():
        return FileResponse(app_html)
    return RedirectResponse(url="/ui/landing/")


@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    """Serve Admin Dashboard page"""
    admin_html = ui_path / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html)
    return RedirectResponse(url="/ui/landing/")


# Mount static files for UI
app.mount("/ui", StaticFiles(directory=str(ui_path), html=True), name="ui")

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
            except:
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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard HTML"""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return """
    <html>
        <head><title>AI Translator Pro</title></head>
        <body>
            <h1>AI Translator Pro API</h1>
            <p>API is running. Access documentation at <a href="/docs">/docs</a></p>
        </body>
    </html>
    """


@app.get("/ui", response_class=HTMLResponse)
async def ui_dashboard():
    """Serve premium UI dashboard"""
    # Try new app.html first, fallback to archived dashboard
    ui_dir = Path(__file__).parent.parent / "ui"
    for filename in ["app.html", "_archive/dashboard_premium_vn.html"]:
        ui_path = ui_dir / filename
        if ui_path.exists():
            return FileResponse(ui_path)
    raise HTTPException(status_code=404, detail="UI dashboard not found")


@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all jobs with optional filtering

    - **status**: Filter by job status (pending/queued/running/completed/failed)
    - **limit**: Maximum number of jobs to return (default: 50)
    - **offset**: Number of jobs to skip (default: 0)
    """
    jobs = queue.list_jobs(status=status, limit=limit, offset=offset)

    return [
        JobResponse(
            job_id=job.job_id,
            job_name=job.job_name,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            source_lang=job.source_lang,
            target_lang=job.target_lang,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            quality_score=job.avg_quality_score,
            total_cost_usd=job.total_cost_usd,
            error_message=job.error_message
        )
        for job in jobs
    ]


@app.post("/api/jobs", response_model=JobResponse, status_code=201)
@limiter.limit("10/minute")
async def create_job(
    request: Request,
    job_data: JobCreate,
    background_tasks: BackgroundTasks
    # csrf_protect: CsrfProtect = Depends()  # Temporarily disabled
):
    """
    Create a new translation job

    The job will be added to the queue and processed automatically
    when the batch processor is running.

    UI v1.1: Supports ui_layout_mode, output_formats, and advanced_options for enhanced UI experience.
    """
    # CSRF validation - Temporarily disabled for debugging
    # await csrf_protect.validate_csrf(request)

    # Validate input file exists
    input_path = Path(job_data.input_file)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {job_data.input_file}")

    # UI v1.1: Map UI parameters to backend parameters
    layout_mode = job_data.layout_mode
    equation_rendering_mode = job_data.equation_rendering_mode
    use_ast_pipeline = False  # Default
    chunk_size = job_data.chunk_size
    concurrency = job_data.concurrency
    cache_enabled = True  # Default
    quality_validation = job_data.enable_quality_check
    enable_book_layout = False  # Default (Phase 4.3 disabled)

    # UI v1.1: Handle ui_layout_mode mapping
    if job_data.ui_layout_mode:
        if job_data.ui_layout_mode == "basic":
            # Basic: Fast, simple formatting, no AST
            layout_mode = "simple"
            use_ast_pipeline = False
            equation_rendering_mode = "latex_text"
        elif job_data.ui_layout_mode == "professional":
            # Professional: AST + Typography (Phase 2.0.7)
            layout_mode = "simple"
            use_ast_pipeline = True
            equation_rendering_mode = "latex_text"
        elif job_data.ui_layout_mode == "academic":
            # Academic: OMML + citations + semantic structure
            layout_mode = "academic"
            use_ast_pipeline = True
            equation_rendering_mode = "omml"
        logger.debug(f"UI v1.1 Layout mode mapping: {job_data.ui_layout_mode} -> layout_mode={layout_mode}, use_ast_pipeline={use_ast_pipeline}, equation_rendering_mode={equation_rendering_mode}")

    # UI v1.1: Handle advanced_options
    if job_data.advanced_options:
        chunk_size = job_data.advanced_options.get('chunk_size', chunk_size)
        concurrency = job_data.advanced_options.get('concurrency', concurrency)
        cache_enabled = job_data.advanced_options.get('cache_enabled', cache_enabled)
        quality_validation = job_data.advanced_options.get('quality_validation', quality_validation)
        enable_book_layout = job_data.advanced_options.get('enable_book_layout', enable_book_layout)
        logger.debug(f"UI v1.1 Advanced options: chunk_size={chunk_size}, concurrency={concurrency}, cache_enabled={cache_enabled}, quality_validation={quality_validation}, enable_book_layout={enable_book_layout}")

    # UI v1.1: Handle output_formats (will process after initial DOCX export)
    output_formats_requested = job_data.output_formats if job_data.output_formats else [job_data.output_format]
    logger.debug(f"UI v1.1 Output formats requested: {output_formats_requested}")

    # Create job (including Phase 3 parameters in metadata)
    # DEBUG: Phase 2.0.4
    metadata_dict = {
        'input_type': job_data.input_type,
        'output_mode': job_data.output_mode,
        'enable_ocr': job_data.enable_ocr,
        'ocr_mode': job_data.ocr_mode,
        'mathpix_app_id': job_data.mathpix_app_id,
        'mathpix_app_key': job_data.mathpix_app_key,
        'enable_quality_check': quality_validation,
        'enable_chemical_formulas': job_data.enable_chemical_formulas,
        # PHASE 1.7.1: Auto-enable academic mode for STEM domain
        'academic_mode': (job_data.domain == 'stem'),
        # Phase 2.0.4: DOCX layout mode (simple vs academic)
        'layout_mode': layout_mode,
        # Phase 2.0.4: Equation rendering mode for academic DOCX
        'equation_rendering_mode': equation_rendering_mode,
        # UI v1.1: Additional metadata
        'use_ast_pipeline': use_ast_pipeline,
        'cache_enabled': cache_enabled,
        'enable_book_layout': enable_book_layout,
        'output_formats_requested': output_formats_requested,
        'ui_layout_mode': job_data.ui_layout_mode  # Track original UI choice
    }
    logger.debug(f"Creating job with metadata: {metadata_dict}")

    job = queue.create_job(
        job_name=job_data.job_name,
        input_file=job_data.input_file,
        output_file=job_data.output_file,
        source_lang=job_data.source_lang,
        target_lang=job_data.target_lang,
        priority=job_data.priority,
        provider=job_data.provider,
        model=job_data.model,
        domain=job_data.domain,
        glossary=job_data.glossary,
        concurrency=concurrency,  # UI v1.1: Use mapped concurrency
        chunk_size=chunk_size,  # UI v1.1: Use mapped chunk_size
        input_format=input_path.suffix[1:] if input_path.suffix else 'txt',
        output_format=output_formats_requested[0] if output_formats_requested else job_data.output_format,  # UI v1.1: Use first format
        # Phase 3: Advanced STEM features stored in metadata
        metadata=metadata_dict
    )
    logger.debug(f"Job created, returned metadata: {job.metadata}")

    # Broadcast new job event
    await manager.broadcast({
        "event": "job_created",
        "job_id": job.job_id,
        "job_name": job.job_name
    })

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata  # Phase 2.0.4
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get detailed information about a specific job

    - **job_id**: Job ID to retrieve
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata  # Phase 2.0.4
    )


@app.get("/api/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(job_id: str):
    """
    Get detailed step-by-step progress for a job (UI v1.1)

    Returns:
        Detailed progress breakdown with:
        - Current step and total steps
        - Individual step statuses
        - Time elapsed and estimated remaining
        - Progress percentage
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Define processing steps based on job configuration
    metadata = job.metadata or {}
    enable_ocr = metadata.get('enable_ocr', False)
    output_formats = metadata.get('output_formats_requested', [job.output_format])
    equation_rendering = metadata.get('equation_rendering_mode', 'latex_text')

    # Build step list dynamically
    all_steps = []

    # Step 1: Upload/Validation (always)
    all_steps.append({
        'name': 'upload',
        'display_name': 'Tải file và xác thực'
    })

    # Step 2: OCR (if enabled)
    if enable_ocr:
        all_steps.append({
            'name': 'ocr',
            'display_name': 'Trích xuất văn bản OCR'
        })

    # Step 3: Translation (always)
    all_steps.append({
        'name': 'translation',
        'display_name': 'Dịch nội dung'
    })

    # Step 4: DOCX rendering (always)
    all_steps.append({
        'name': 'docx_render',
        'display_name': 'Render DOCX với typography'
    })

    # Step 5: OMML equations (if academic mode)
    if equation_rendering == 'omml':
        all_steps.append({
            'name': 'omml_equations',
            'display_name': 'Render phương trình OMML'
        })

    # Step 6: PDF export (if requested)
    if 'pdf' in output_formats:
        all_steps.append({
            'name': 'pdf_export',
            'display_name': 'Xuất PDF'
        })

    total_steps = len(all_steps)

    # Determine current step based on job status and progress
    if job.status == JobStatus.PENDING or job.status == JobStatus.QUEUED:
        current_step_idx = 0
        step_statuses = ['pending'] * total_steps
    elif job.status == JobStatus.COMPLETED:
        current_step_idx = total_steps - 1
        step_statuses = ['completed'] * total_steps
    elif job.status == JobStatus.FAILED or job.status == JobStatus.CANCELLED:
        # Determine how far we got
        current_step_idx = int(job.progress * total_steps)
        step_statuses = ['completed'] * current_step_idx + ['failed'] + ['pending'] * (total_steps - current_step_idx - 1)
    else:  # RUNNING or RETRYING
        # Map progress to steps
        # Assume translation takes 70% of time, other steps split the remaining 30%
        if job.progress < 0.1:
            # Upload/OCR phase
            current_step_idx = 0 if not enable_ocr else min(1, int(job.progress * 10))
        elif job.progress < 0.8:
            # Translation phase (bulk of work)
            current_step_idx = (1 if enable_ocr else 0) + 1
        else:
            # Rendering/export phase
            progress_in_final = (job.progress - 0.8) / 0.2
            steps_before_render = 2 + (1 if enable_ocr else 0)
            current_step_idx = steps_before_render + int(progress_in_final * (total_steps - steps_before_render))

        current_step_idx = min(current_step_idx, total_steps - 1)
        step_statuses = ['completed'] * current_step_idx + ['in_progress'] + ['pending'] * (total_steps - current_step_idx - 1)

    # Build step details
    steps = []
    for i, step_def in enumerate(all_steps):
        step_status = step_statuses[i] if i < len(step_statuses) else 'pending'

        step = ProgressStep(
            name=step_def['name'],
            display_name=step_def['display_name'],
            status=step_status
        )

        # Add progress for in_progress steps
        if step_status == 'in_progress':
            # Estimate sub-progress within current step
            if step_def['name'] == 'translation':
                # Use chunk progress for translation
                if job.total_chunks > 0:
                    step.progress = job.completed_chunks / job.total_chunks
                else:
                    step.progress = job.progress
            else:
                # For other steps, estimate based on job progress
                step.progress = (job.progress * total_steps - i) if job.progress * total_steps > i else 0.0
                step.progress = max(0.0, min(1.0, step.progress))

        steps.append(step)

    # Calculate elapsed time
    elapsed_seconds = 0.0
    if job.started_at:
        if job.completed_at:
            elapsed_seconds = job.completed_at - job.started_at
        else:
            elapsed_seconds = time.time() - job.started_at

    # Estimate remaining time
    estimated_remaining = None
    if job.status == JobStatus.RUNNING and job.progress > 0.01 and elapsed_seconds > 0:
        # Simple linear estimation: time_elapsed / progress_done = time_total
        total_estimated = elapsed_seconds / job.progress
        estimated_remaining = max(0, total_estimated - elapsed_seconds)

    # Calculate overall progress percentage
    progress_percent = int(job.progress * 100)

    # Determine output file
    output_file = None
    if job.status == JobStatus.COMPLETED:
        output_file = job.output_file

    return JobProgressResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        current_step=current_step_idx + 1,  # 1-indexed
        total_steps=total_steps,
        progress_percent=progress_percent,
        steps=steps,
        elapsed_seconds=elapsed_seconds,
        estimated_remaining_seconds=estimated_remaining,
        output_file=output_file
    )


@app.patch("/api/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    update: JobUpdate,
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """
    Update a job's status or priority

    - **job_id**: Job ID to update
    - **status**: New status (optional)
    - **priority**: New priority (optional)
    """
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Update fields
    if update.status:
        job.status = update.status
    if update.priority is not None:
        job.priority = update.priority

    queue.update_job(job)

    # Broadcast update event
    await manager.broadcast({
        "event": "job_updated",
        "job_id": job.job_id,
        "status": job.status,
        "priority": job.priority
    })

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata  # Phase 2.0.4
    )


@app.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: str,
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """
    Delete a job (only if completed, failed, or cancelled)

    - **job_id**: Job ID to delete
    """
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    if queue.delete_job(job_id):
        # Broadcast delete event
        await manager.broadcast({
            "event": "job_deleted",
            "job_id": job_id
        })
        return {"message": f"Job {job_id} deleted successfully"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete job (only completed/failed/cancelled jobs can be deleted)"
        )


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """
    Cancel a pending, queued, or running job

    - **job_id**: Job ID to cancel
    """
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # If job is running, check processor status
    if job.status == "running":
        # If processor is not running, force cancel immediately
        if processor is None or not processor.is_running:
            # Force update status directly (queue.cancel_job doesn't work for running jobs)
            job.status = JobStatus.CANCELLED
            job.updated_at = time.time()
            queue.update_job(job)

            await manager.broadcast({
                "event": "job_cancelled",
                "job_id": job_id,
                "message": "Job force-cancelled (processor stopped)"
            })
            return {"message": f"Job {job_id} force-cancelled (processor was stopped)", "status": "cancelled"}

        # If processor is running, request graceful cancellation
        else:
            job.request_cancellation()
            queue.update_job(job)

            # Broadcast cancellation request
            await manager.broadcast({
                "event": "job_cancelling",
                "job_id": job_id,
                "message": "Cancellation requested, stopping translation..."
            })
            return {"message": f"Job {job_id} cancellation requested (stopping...)", "status": "cancelling"}

    # For pending/queued jobs, cancel immediately
    elif queue.cancel_job(job_id):
        # Broadcast cancel event
        await manager.broadcast({
            "event": "job_cancelled",
            "job_id": job_id
        })
        return {"message": f"Job {job_id} cancelled successfully", "status": "cancelled"}

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status: {job.status}"
        )


@app.get("/api/jobs/{job_id}/download/{format}")
async def download_job_output(job_id: str, format: str):
    """
    Download translated output file with on-the-fly conversion

    Args:
        job_id: Job ID
        format: Output format (docx, pdf, md, txt, html)

    Returns:
        FileResponse with translated document
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Please check the job ID or view available jobs at /api/jobs"
        )

    if job.status != JobStatus.COMPLETED:
        status_messages = {
            "pending": "Job is queued and waiting to start",
            "running": "Job is currently being translated",
            "paused": "Job has been paused",
            "cancelled": "Job was cancelled before completion",
            "failed": "Job failed during translation"
        }
        status_msg = status_messages.get(job.status, job.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot download: {status_msg}. Only completed jobs can be downloaded."
        )

    # Get output file path and resolve to absolute path
    output_path = Path(job.output_file)

    # If relative path, resolve from project root
    if not output_path.is_absolute():
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_path

    # Resolve to canonical absolute path
    output_path = output_path.resolve()
    output_dir = output_path.parent
    base_name = output_path.stem

    # Check if requested format file already exists
    target_path = output_dir / f"{base_name}.{format}"

    if target_path.exists():
        output_path = target_path
    elif format != job.output_format and output_path.exists():
        # Try to convert from original format
        try:
            converted_path = await convert_document_format(output_path, format, output_dir, base_name)
            if converted_path and converted_path.exists():
                output_path = converted_path
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to convert to {format} format"
                )
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Conversion to {format} failed: {str(e)}"
            )
    elif not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Output file not found. The translation may have failed or the file was deleted."
        )

    # Determine media type
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "txt": "text/plain",
        "html": "text/html",
        "md": "text/markdown",
        "srt": "text/plain"
    }
    media_type = media_types.get(format, "application/octet-stream")

    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        filename=f"{base_name}.{format}"
    )


async def convert_document_format(source_path: Path, target_format: str, output_dir: Path, base_name: str) -> Path:
    """
    Convert document to requested format

    Supports: docx -> pdf, docx -> md, docx -> txt
    """
    target_path = output_dir / f"{base_name}.{target_format}"

    if target_format == "md":
        # Convert DOCX to Markdown
        try:
            from docx import Document
            doc = Document(str(source_path))

            md_lines = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    md_lines.append("")
                    continue

                # Detect headings by style
                style_name = para.style.name.lower() if para.style else ""
                if "heading 1" in style_name or "title" in style_name:
                    md_lines.append(f"# {text}")
                elif "heading 2" in style_name:
                    md_lines.append(f"## {text}")
                elif "heading 3" in style_name:
                    md_lines.append(f"### {text}")
                else:
                    md_lines.append(text)

                md_lines.append("")  # Empty line after each paragraph

            with open(target_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))

            return target_path
        except Exception as e:
            logger.error(f"Markdown conversion failed: {e}")
            raise

    elif target_format == "pdf":
        # Try multiple PDF conversion methods
        # Method 1: docx2pdf (requires LibreOffice)
        try:
            import subprocess
            result = subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(source_path)],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0 and target_path.exists():
                return target_path
        except Exception as e:
            logger.warning(f"LibreOffice PDF conversion failed: {e}")

        # Method 2: Create simple PDF with reportlab
        try:
            from docx import Document
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Try to register a font that supports Vietnamese
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                font_name = 'DejaVu'
            except:
                font_name = 'Helvetica'

            doc = Document(str(source_path))
            pdf = SimpleDocTemplate(str(target_path), pagesize=A4,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=72)

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Vietnamese', fontName=font_name, fontSize=11, leading=14))

            story = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    # Escape special characters for reportlab
                    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(text, styles['Vietnamese']))
                    story.append(Spacer(1, 6))

            pdf.build(story)
            return target_path
        except Exception as e:
            logger.error(f"ReportLab PDF conversion failed: {e}")
            raise

    elif target_format == "txt":
        # Convert DOCX to plain text
        try:
            from docx import Document
            doc = Document(str(source_path))

            text_lines = []
            for para in doc.paragraphs:
                text_lines.append(para.text)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(text_lines))

            return target_path
        except Exception as e:
            logger.error(f"TXT conversion failed: {e}")
            raise

    else:
        raise ValueError(f"Unsupported target format: {target_format}")


@app.get("/api/jobs/{job_id}/preview")
async def get_job_preview(job_id: str, limit: int = 2000):
    """
    Get preview of translated output with structured formatting (headings + paragraphs)

    Args:
        job_id: Job ID
        limit: Maximum number of words to return (default: 2000)

    Returns:
        Structured preview with heading detection and metadata
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot preview: Job status is '{job.status}'. Only completed jobs can be previewed."
        )

    # Get output file path and resolve to absolute path
    output_path = Path(job.output_file)

    # If relative path, resolve from project root
    if not output_path.is_absolute():
        project_root = Path(__file__).parent.parent
        output_path = project_root / output_path

    # Resolve to canonical absolute path
    output_path = output_path.resolve()

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Output file not found: {output_path}"
        )

    try:
        # Check file format
        file_extension = output_path.suffix.lower()

        if file_extension == '.docx':
            # Read DOCX with structure preservation
            doc = DocxDocument(str(output_path))
            detector = HeadingDetector()

            structured_preview = []
            word_count = 0
            is_truncated = False

            for para in doc.paragraphs:
                para_text = para.text.strip()
                if not para_text:
                    continue

                # Count words in this paragraph
                para_words = len(para_text.split())

                # Check if adding this paragraph would exceed limit
                if word_count + para_words > limit:
                    is_truncated = True
                    # Add partial paragraph if there's room
                    if word_count < limit:
                        remaining_words = limit - word_count
                        truncated_text = ' '.join(para_text.split()[:remaining_words]) + '...'
                        structured_preview.append({
                            "text": truncated_text,
                            "type": "paragraph",
                            "level": None
                        })
                    break

                # Detect heading level
                level = detector.detect_heading_level(para_text)

                if level:
                    # This is a heading
                    structured_preview.append({
                        "text": para_text,
                        "type": f"heading{level}",
                        "level": level
                    })
                else:
                    # Regular paragraph
                    structured_preview.append({
                        "text": para_text,
                        "type": "paragraph",
                        "level": None
                    })

                word_count += para_words

            # Count total words in document
            total_words = sum(len(p.text.split()) for p in doc.paragraphs if p.text.strip())

            return {
                "preview": structured_preview,
                "total_words": total_words,
                "preview_words": word_count,
                "is_truncated": is_truncated,
                "format": job.output_format,
                "is_structured": True
            }

        else:
            # Fallback for non-DOCX formats (TXT, MD, etc.)
            text = read_document(output_path)
            words = text.split()
            total_words = len(words)
            preview_words = words[:limit]
            preview_text = ' '.join(preview_words)

            return {
                "preview": preview_text,
                "total_words": total_words,
                "preview_words": len(preview_words),
                "is_truncated": total_words > limit,
                "format": job.output_format,
                "is_structured": False
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )


@app.post("/api/pdf/detect")
async def detect_pdf_type(
    file_path: str,
    request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """
    Detect PDF type (native vs scanned) and recommend OCR mode.

    Args:
        file_path: Path to PDF file (absolute or relative to project root)

    Returns:
        Detection result with PDF type, recommendation, and confidence
    """
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(request)

    from core.ocr import SmartDetector, PDFType, OCRMode

    # Resolve path
    pdf_path = Path(file_path)
    if not pdf_path.is_absolute():
        project_root = Path(__file__).parent.parent
        pdf_path = project_root / pdf_path

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {file_path}")

    if not pdf_path.suffix.lower() == '.pdf':
        raise HTTPException(status_code=400, detail=f"File is not a PDF: {file_path}")

    try:
        detector = SmartDetector()
        result = detector.detect_pdf_type(pdf_path)

        return {
            "pdf_type": result.pdf_type.value,
            "ocr_needed": result.ocr_needed,
            "confidence": result.confidence,
            "recommendation": result.recommendation.value,
            "details": result.details,
            "message": detector.recommend_ocr_mode(pdf_path, has_mathpix_key=bool(os.getenv('MATHPIX_APP_ID')))
        }

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Smart detection unavailable. Install OCR dependencies: pip install paddleocr paddlepaddle"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


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
# API Endpoints - Batch Queue (Multi-file Processing)
# =============================================================================

# In-memory batch queue storage (for demo - use Redis in production)
batch_jobs_db: Dict[str, Dict] = {}
batch_queue_running = False


@app.get("/api/batch/status")
async def get_batch_status():
    """Get batch queue status"""
    pending = sum(1 for j in batch_jobs_db.values() if j["status"] == "pending")
    processing = sum(1 for j in batch_jobs_db.values() if j["status"] == "processing")
    completed = sum(1 for j in batch_jobs_db.values() if j["status"] == "completed")
    failed = sum(1 for j in batch_jobs_db.values() if j["status"] == "failed")

    total_pages = sum(j.get("total_pages", 0) for j in batch_jobs_db.values())
    completed_pages = sum(j.get("completed_pages", 0) for j in batch_jobs_db.values())
    total_cost = sum(j.get("cost", 0) for j in batch_jobs_db.values())

    return {
        "is_running": batch_queue_running,
        "jobs": {
            "total": len(batch_jobs_db),
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed
        },
        "pages": {
            "total": total_pages,
            "completed": completed_pages,
            "progress": (completed_pages / total_pages * 100) if total_pages > 0 else 0
        },
        "cost": {
            "total": round(total_cost, 4)
        }
    }


@app.post("/api/batch/upload")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    mode: str = "balanced"
):
    """Upload multiple PDF files to batch queue"""
    created_jobs = []

    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue

        # Generate job ID
        job_id = str(uuid.uuid4())[:8]

        # Save file
        upload_dir = Path("./uploads/batch")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{job_id}_{file.filename}"

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Estimate pages (10 pages per MB)
        pages = max(1, int(len(content) / (1024 * 1024) * 10))

        # Cost per page based on mode
        costs = {"economy": 0.001, "balanced": 0.004, "quality": 0.05}

        # Create job
        job = {
            "id": job_id,
            "name": file.filename.replace(".pdf", ""),
            "file_path": str(file_path),
            "status": "pending",
            "priority": 2,
            "total_pages": pages,
            "completed_pages": 0,
            "progress": 0,
            "elapsed": 0,
            "cost": 0,
            "pages_per_min": 0,
            "error": None,
            "output_path": None,
            "settings": {
                "mode": mode,
                "source_lang": "Chinese",
                "target_lang": "Vietnamese",
                "output_format": "docx"
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        batch_jobs_db[job_id] = job
        created_jobs.append(job)

    estimated_cost = sum(
        j["total_pages"] * costs.get(j["settings"]["mode"], 0.004)
        for j in created_jobs
    )

    return {
        "success": True,
        "jobs_created": len(created_jobs),
        "jobs": created_jobs,
        "estimated_cost": round(estimated_cost, 4)
    }


@app.get("/api/batch/jobs")
async def list_batch_jobs():
    """List all batch jobs"""
    jobs = list(batch_jobs_db.values())

    # Sort: processing > pending > paused > failed > completed > cancelled
    order = {"processing": 0, "preparing": 1, "pending": 2, "paused": 3, "failed": 4, "completed": 5, "cancelled": 6}
    jobs.sort(key=lambda j: (order.get(j["status"], 99), -j["priority"]))

    return {"jobs": jobs}


@app.get("/api/batch/jobs/{job_id}")
async def get_batch_job(job_id: str):
    """Get batch job details"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return batch_jobs_db[job_id]


@app.patch("/api/batch/jobs/{job_id}")
async def update_batch_job(job_id: str, status: str = None, priority: int = None):
    """Update batch job (pause, resume, cancel, set priority)"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if status:
        job["status"] = status
    if priority:
        job["priority"] = priority

    job["updated_at"] = datetime.now().isoformat()
    return job


@app.delete("/api/batch/jobs/{job_id}")
async def delete_batch_job(job_id: str):
    """Delete/cancel batch job"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if job["status"] == "processing":
        job["status"] = "cancelled"
    else:
        del batch_jobs_db[job_id]

    return {"success": True, "message": "Job deleted"}


@app.post("/api/batch/jobs/{job_id}/retry")
async def retry_batch_job(job_id: str):
    """Retry a failed batch job"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if job["status"] not in ["failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Can only retry failed or cancelled jobs")

    job["status"] = "pending"
    job["progress"] = 0
    job["completed_pages"] = 0
    job["error"] = None
    job["updated_at"] = datetime.now().isoformat()

    return job


@app.post("/api/batch/queue/start")
async def start_batch_queue(background_tasks: BackgroundTasks):
    """Start batch queue processing"""
    global batch_queue_running

    if batch_queue_running:
        return {"success": False, "message": "Batch queue already running"}

    batch_queue_running = True
    background_tasks.add_task(process_batch_queue)

    return {"success": True, "message": "Batch queue started"}


@app.post("/api/batch/queue/pause")
async def pause_batch_queue():
    """Pause batch queue processing"""
    global batch_queue_running
    batch_queue_running = False
    return {"success": True, "message": "Batch queue paused"}


@app.post("/api/batch/queue/clear")
async def clear_batch_completed():
    """Clear completed and cancelled batch jobs"""
    to_remove = [
        job_id for job_id, job in batch_jobs_db.items()
        if job["status"] in ["completed", "cancelled"]
    ]

    for job_id in to_remove:
        del batch_jobs_db[job_id]

    return {"success": True, "cleared": len(to_remove)}


async def process_batch_queue():
    """Background task to process batch jobs"""
    global batch_queue_running

    while batch_queue_running:
        # Get processing count
        processing = [j for j in batch_jobs_db.values() if j["status"] == "processing"]

        # Start new jobs if slots available (max 2 concurrent)
        if len(processing) < 2:
            pending = sorted(
                [j for j in batch_jobs_db.values() if j["status"] == "pending"],
                key=lambda j: -j["priority"]
            )

            if pending:
                job = pending[0]
                job["status"] = "processing"
                asyncio.create_task(process_batch_job(job["id"]))

        await asyncio.sleep(1)


async def process_batch_job(job_id: str):
    """Process a single batch job (simulated for demo)"""
    if job_id not in batch_jobs_db:
        return

    job = batch_jobs_db[job_id]
    costs = {"economy": 0.001, "balanced": 0.004, "quality": 0.05}

    try:
        while job["status"] == "processing":
            # Simulate progress (3 pages per second)
            job["completed_pages"] = min(
                job["completed_pages"] + 3,
                job["total_pages"]
            )
            job["progress"] = (job["completed_pages"] / job["total_pages"]) * 100
            job["elapsed"] += 1

            mode = job["settings"]["mode"]
            job["cost"] = job["completed_pages"] * costs.get(mode, 0.004)

            if job["elapsed"] > 0:
                job["pages_per_min"] = (job["completed_pages"] / job["elapsed"]) * 60

            job["updated_at"] = datetime.now().isoformat()

            # Check if done
            if job["completed_pages"] >= job["total_pages"]:
                job["status"] = "completed"
                job["progress"] = 100

                # Output path
                output_dir = Path("./outputs/batch")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{job_id}_output.{job['settings']['output_format']}"
                job["output_path"] = str(output_path)

                # Create placeholder output
                with open(output_path, "w") as f:
                    f.write(f"Translated document: {job['name']}")

                break

            await asyncio.sleep(1)

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)


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


@app.post("/api/upload")
@limiter.limit("20/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
    # csrf_protect: CsrfProtect = Depends()  # Temporarily disabled
):
    """
    Upload file for translation

    Accepts: TXT, PDF, DOCX, SRT
    Max size: 50MB
    Returns: Server file path for job creation
    """
    # CSRF validation - Temporarily disabled for debugging
    # await csrf_protect.validate_csrf(request)

    import os
    import shutil

    # Validate file type
    allowed_types = [
        "text/plain",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/x-subrip"
    ]
    allowed_extensions = [".txt", ".pdf", ".docx", ".srt"]

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Read file
    contents = await file.read()

    # Check size (configurable via MAX_UPLOAD_SIZE_MB env var, default 50MB)
    max_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(contents) > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {max_size_mb}MB)")

    # Create uploads directory if not exists
    upload_dir = Path(__file__).parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # Generate unique filename
    import uuid
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / unique_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    return {
        "filename": file.filename,
        "server_path": str(file_path),
        "size": len(contents),
        "content_type": file.content_type
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    request: AnalyzeRequest,
    http_request: Request = None
    # csrf_protect: CsrfProtect = Depends()  # Disabled for internal deployment
):
    """
    Analyze uploaded file and return accurate word count and language detection

    This endpoint extracts text from PDF/DOCX/TXT files and provides:
    - Accurate word count (not file size estimation)
    - Character count
    - Language detection
    - Chunk count estimate

    Args:
        request: AnalyzeRequest with file_path

    Returns:
        AnalyzeResponse with accurate statistics
    """
    # CSRF validation - Disabled for internal deployment
    # await csrf_protect.validate_csrf(http_request)

    try:
        # Check if file exists
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

        # Extract text from document
        text = read_document(file_path)

        # Detect language using statistical analysis (not just presence)
        cjk_pattern = r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]'
        cjk_char_pattern = r'[\u4e00-\u9fff]'  # Chinese characters only (most common)
        vi_pattern = r'[ăâđêôơưàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]'

        # Count character types for statistical detection
        total_chars = len(re.sub(r'\s', '', text))  # Non-whitespace chars
        cjk_chars = len(re.findall(cjk_char_pattern, text))
        vi_chars = len(re.findall(vi_pattern, text, re.IGNORECASE))

        # Calculate proportions (avoid division by zero)
        cjk_ratio = cjk_chars / total_chars if total_chars > 0 else 0
        vi_ratio = vi_chars / total_chars if total_chars > 0 else 0

        # Detect language based on character proportions
        # CJK: Need at least 10% CJK characters
        # Vietnamese: Need at least 3% Vietnamese accented characters
        if cjk_ratio > 0.10:
            detected_lang = 'Trung/Nhật'
            # For CJK: Count characters, not words (CJK has no spaces between words)
            word_count = cjk_chars
        elif vi_ratio > 0.03:
            detected_lang = 'Tiếng Việt'
            # For Vietnamese: Count words by splitting on whitespace
            words = re.split(r'\s+', text.strip())
            word_count = len([w for w in words if w])
        else:
            detected_lang = 'Tiếng Anh'
            # For English: Count words by splitting on whitespace
            words = re.split(r'\s+', text.strip())
            word_count = len([w for w in words if w])

        # Calculate chunks estimate (3000 words per chunk)
        chunks_estimate = math.ceil(word_count / 3000) if word_count > 0 else 1

        return AnalyzeResponse(
            word_count=word_count,
            character_count=len(text),
            detected_language=detected_lang,
            chunks_estimate=chunks_estimate
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/v2/detect-language")
async def detect_language(file: UploadFile = File(...)):
    """
    Detect language from uploaded file.

    Returns language code (en, zh, ja, ko, fr, de, es, ru, vi) and confidence.
    """
    import tempfile
    import os

    try:
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract text
            text = read_document(Path(tmp_path))
            sample = text[:5000]  # Use first 5000 chars for detection

            # Character pattern detection
            patterns = {
                'zh': (r'[\u4e00-\u9fff]', 0.10),  # Chinese chars, need 10%
                'ja': (r'[\u3040-\u309f\u30a0-\u30ff]', 0.05),  # Hiragana/Katakana
                'ko': (r'[\uac00-\ud7af]', 0.05),  # Korean Hangul
                'ru': (r'[\u0400-\u04ff]', 0.10),  # Cyrillic
                'vi': (r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]', 0.03),
            }

            total_chars = len(re.sub(r'\s', '', sample))
            if total_chars == 0:
                return {"language": "en", "confidence": 0.5}

            # Check each pattern
            for lang, (pattern, threshold) in patterns.items():
                matches = len(re.findall(pattern, sample, re.IGNORECASE))
                ratio = matches / total_chars
                if ratio > threshold:
                    confidence = min(0.95, ratio * 5)
                    return {"language": lang, "confidence": confidence}

            # European language detection by common words
            word_patterns = {
                'fr': r'\b(le|la|les|de|du|des|et|est|un|une|que|qui|dans|pour|sur|avec)\b',
                'de': r'\b(der|die|das|und|ist|ein|eine|zu|den|von|mit|für|auf|nicht|auch)\b',
                'es': r'\b(el|la|los|las|de|en|y|que|es|un|una|por|con|para|del|al|se)\b',
                'en': r'\b(the|be|to|of|and|a|in|that|have|it|for|not|on|with|he|as|you)\b',
            }

            max_lang = 'en'
            max_count = 0

            for lang, pattern in word_patterns.items():
                count = len(re.findall(pattern, sample, re.IGNORECASE))
                if count > max_count:
                    max_count = count
                    max_lang = lang

            confidence = min(0.9, max_count / 50)
            return {"language": max_lang, "confidence": confidence}

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return {"language": "en", "confidence": 0.5}


# =============================================================================
# WebSocket Endpoint - Real-time Updates
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates

    Sends updates about:
    - Job status changes
    - Queue statistics
    - System events
    """
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
# Health Check & Monitoring
# =============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.4.0",
        "timestamp": time.time()
    }


@app.get("/api/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with all system components.

    Returns comprehensive health status including:
    - System resources (CPU, memory, disk)
    - Database connectivity
    - Storage availability
    - API provider configuration
    """
    try:
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        health_status = monitor.check_health()

        return {
            "status": health_status.status,
            "timestamp": health_status.timestamp,
            "uptime_seconds": health_status.uptime_seconds,
            "components": health_status.components
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/api/monitoring/costs")
async def get_cost_metrics(time_period_hours: int = 24):
    """
    Get cost tracking metrics.

    Args:
        time_period_hours: Time window in hours (default 24)

    Returns:
        Cost metrics including:
        - Total tokens used
        - Total cost in USD
        - Cost breakdown by provider/model
        - Average cost per job
    """
    try:
        from core.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        cost_metrics = monitor.get_cost_metrics(time_period_hours)

        return {
            "total_tokens_used": cost_metrics.total_tokens_used,
            "total_cost_usd": cost_metrics.total_cost_usd,
            "cost_by_provider": cost_metrics.cost_by_provider,
            "cost_by_model": cost_metrics.cost_by_model,
            "average_cost_per_job": cost_metrics.average_cost_per_job,
            "jobs_processed": cost_metrics.jobs_processed,
            "time_period": cost_metrics.time_period
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost metrics: {str(e)}")


@app.get("/api/monitoring/errors")
async def get_error_stats(time_period_hours: int = 24):
    """
    Get error tracking statistics.

    Args:
        time_period_hours: Time window in hours (default 24)

    Returns:
        Error statistics including severity and category breakdowns
    """
    try:
        from core.error_tracker import get_error_tracker
        tracker = get_error_tracker()
        stats = tracker.get_statistics(time_period_hours)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error stats: {str(e)}")


@app.get("/api/monitoring/errors/recent")
async def get_recent_errors(limit: int = 50, severity: Optional[str] = None):
    """
    Get recent error records.

    Args:
        limit: Maximum number of errors to return (default 50)
        severity: Filter by severity (low, medium, high, critical)

    Returns:
        List of recent error records
    """
    try:
        from core.error_tracker import get_error_tracker, ErrorSeverity
        tracker = get_error_tracker()

        severity_enum = None
        if severity:
            severity_enum = ErrorSeverity(severity.lower())

        errors = tracker.get_recent_errors(limit, severity_enum)

        return [
            {
                "id": err.id,
                "error_type": err.error_type,
                "error_message": err.error_message,
                "severity": err.severity.value,
                "category": err.category.value,
                "last_seen": err.last_seen,
                "occurrence_count": err.occurrence_count,
                "resolved": err.resolved
            }
            for err in errors
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent errors: {str(e)}")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting AI Translator Pro API Server...")
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Dashboard: http://localhost:8000/")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
