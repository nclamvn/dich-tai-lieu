#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI Web Server - REST API for AI Translator Pro.

Thin orchestration shell: app creation, middleware, router includes,
startup/shutdown events, WebSocket, UI pages, auth sessions, static mount.

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pathlib import Path
import asyncio
import time
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import get_logger
logger = get_logger(__name__)

# --- Shared state (imported from deps) ---
from api.deps import queue, manager, start_time

# --- Models (LoginRequest used here for auth session endpoints) ---
from api.models import LoginRequest

# --- Existing routers ---
from api.routes import author
from api.aps_v2_router import router as aps_v2_router
from api.batch_router import router as batch_router
from api.provider_routes import router as provider_router
from api.glossary_router import router as glossary_router
from api.tm_router import router as tm_router
from api.editor_router import router as editor_router
from api.auth_router import router as auth_router
from api.error_dashboard_router import router as error_router
from api.usage_router import router as usage_router
from api.api_keys_router import router as api_keys_router
from api.preview_router import router as preview_router

# --- New route modules (Sprint 5) ---
from api.routes.health import router as health_router
from api.routes.uploads import router as uploads_router
from api.routes.batch_legacy import router as batch_legacy_router
from api.routes.system import router as system_router
from api.routes.job_outputs import router as job_outputs_router
from api.routes.jobs import router as jobs_router

# --- Sprint 14 routes ---
from api.routes.dashboard import router as dashboard_router

# --- Book Writer ---
from api.book_writer_router import router as book_writer_router

# --- Book Writer v2.0 ---
from api.routes.book_writer_v2 import router as book_writer_v2_router

# --- Settings Management ---
from api.routes.settings import router as settings_router

# =============================================================================
# CSRF Protection Configuration
# =============================================================================

@CsrfProtect.load_config
def get_csrf_config():
    """Load CSRF configuration"""
    from config.settings import settings

    class CsrfSettings(BaseModel):
        secret_key: str = settings.csrf_secret_key
        cookie_name: str = "fastapi-csrf-token"
        cookie_samesite: str = "lax"
        cookie_secure: bool = False
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

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "60/minute")]
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CSRF protection exception handler
@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=403,
        content={"detail": "CSRF token validation failed. Please refresh the page and try again."}
    )

# CORS middleware — origins from settings (env var) or dev defaults
from config.settings import settings as _settings
ALLOWED_ORIGINS = _settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# =============================================================================
# Include Routers
# =============================================================================

# Existing routers
app.include_router(author.router)
app.include_router(editor_router)
app.include_router(aps_v2_router)
app.include_router(batch_router)
app.include_router(provider_router, prefix="/api/v2/providers", tags=["AI Providers"])
app.include_router(glossary_router, prefix="/api/glossary", tags=["Glossary"])
app.include_router(auth_router)
app.include_router(error_router)
app.include_router(tm_router, prefix="/api/tm", tags=["Translation Memory"])
app.include_router(usage_router)
app.include_router(api_keys_router)
app.include_router(preview_router)

# New Sprint 5 routers
app.include_router(health_router)
app.include_router(uploads_router)
app.include_router(batch_legacy_router)
app.include_router(system_router)
app.include_router(job_outputs_router)
app.include_router(jobs_router)

# Sprint 14 routers
app.include_router(dashboard_router)

# Book Writer
app.include_router(book_writer_router)

# Book Writer v2.0 — Enhanced 9-agent pipeline
app.include_router(book_writer_v2_router)

# Settings Management
app.include_router(settings_router)

# =============================================================================
# Startup / Shutdown Events
# =============================================================================

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
async def startup_resume_book_projects():
    """Resume book writer pipelines interrupted by server restart."""
    try:
        from api.book_writer_router import get_service
        service = get_service()
        await service.resume_stalled_projects()
    except Exception as e:
        logger.error(f"Startup: Failed to resume book projects: {e}")


@app.on_event("startup")
async def startup_book_writer_v2():
    """Initialize Book Writer v2.0 service with AI client."""
    try:
        from api.services.book_writer_v2_service import get_book_writer_v2_service
        try:
            from ai_providers.unified_client import get_unified_client
            ai_client = get_unified_client()
            get_book_writer_v2_service(ai_client)
            logger.info("Book Writer v2.0 initialized with AI client")
        except ImportError:
            get_book_writer_v2_service()
            logger.warning("Book Writer v2.0 initialized with mock AI client")
    except Exception as e:
        logger.error(f"Startup: Book Writer v2.0 init failed: {e}")


@app.on_event("startup")
async def startup_redis():
    """Initialize Redis client (falls back to in-memory if unavailable)."""
    try:
        from core.cache.redis_client import get_redis_client
        redis_url = os.environ.get("REDIS_URL")
        client = await get_redis_client(redis_url)
        logger.info(f"Redis initialized (real={client.is_real_redis})")
    except Exception as e:
        logger.warning(f"Redis init skipped: {e}")


@app.on_event("shutdown")
async def shutdown_redis():
    """Close Redis connection on shutdown."""
    try:
        from core.cache.redis_client import close_redis_client
        await close_redis_client()
    except Exception as e:
        logger.debug("Redis shutdown skipped: %s", e)


@app.on_event("startup")
async def startup_cleanup_scheduler():
    """Start periodic file cleanup (every 6 hours) and job memory cleanup (every 1 hour)."""
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(6 * 3600)
            try:
                from core.services.file_cleanup import FileCleanupService
                svc = FileCleanupService()
                result = svc.run_cleanup()
                logger.info(f"Scheduled cleanup: {result}")
            except Exception as e:
                logger.error(f"Scheduled cleanup failed: {e}")

    async def _job_cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # Every hour
            try:
                from api.aps_v2_service import get_v2_service
                service = get_v2_service()
                evicted = service.cleanup_old_jobs()
                if evicted > 0:
                    logger.info(f"Job cleanup: evicted {evicted} old jobs from memory")
            except Exception as e:
                logger.error(f"Job cleanup failed: {e}")

    asyncio.create_task(_cleanup_loop())
    asyncio.create_task(_job_cleanup_loop())

# =============================================================================
# UI Page Routes
# =============================================================================

ui_path = Path(__file__).parent.parent / "ui"


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve landing page directly at root URL"""
    landing_html = ui_path / "landing" / "index.html"
    if landing_html.exists():
        return FileResponse(landing_html)
    return RedirectResponse(url="/ui/landing/")


@app.get("/app", include_in_schema=False)
async def publisher_studio():
    """Serve Publisher Studio page (Claude-style UI)"""
    claude_ui = ui_path / "app-claude-style.html"
    if claude_ui.exists():
        return FileResponse(claude_ui)
    return RedirectResponse(url="/ui/landing/")


@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    """Serve Admin Dashboard page"""
    admin_html = ui_path / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html)
    return RedirectResponse(url="/ui/landing/")


@app.get("/admin/errors", include_in_schema=False)
async def error_dashboard():
    """Serve Error Dashboard page"""
    errors_html = ui_path / "admin" / "errors.html"
    if errors_html.exists():
        return FileResponse(errors_html)
    return RedirectResponse(url="/admin")


@app.get("/ui", response_class=HTMLResponse)
async def ui_dashboard():
    """Serve Claude-style UI dashboard (2026 redesign)"""
    claude_ui = ui_path / "app-claude-style.html"
    if claude_ui.exists():
        return FileResponse(claude_ui)
    raise HTTPException(status_code=404, detail="UI dashboard not found")


# Mount static files for UI (CSS, JS, images, etc.)
app.mount("/ui", StaticFiles(directory=str(ui_path), html=True), name="ui")

# =============================================================================
# Security & Authentication (Session-based) — kept in main.py
# =============================================================================

from api.security import security_manager, SessionInfo, get_optional_session


@app.post("/api/auth/login")
@limiter.limit(_settings.auth_rate_limit)
async def login(request: Request, login_data: LoginRequest):
    """
    Create a session (simple login for internal deployment)

    Returns session token to use in X-Session-Token header.
    Rate-limited to prevent brute force attacks.
    """
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
# WebSocket Endpoint
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates

    Sends updates about job status changes, queue statistics, and system events.

    Clients can send JSON messages:
    - {"action": "subscribe", "job_id": "abc123"} to filter events for a specific job
    - {"action": "unsubscribe"} to receive all events again
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
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                # Handle incoming messages (subscribe/unsubscribe)
                import json
                try:
                    msg = json.loads(data)
                    if msg.get("action") == "subscribe" and msg.get("job_id"):
                        await websocket.send_json({
                            "event": "subscribed",
                            "job_id": msg["job_id"],
                        })
                except (json.JSONDecodeError, KeyError):
                    pass
            except asyncio.TimeoutError:
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
