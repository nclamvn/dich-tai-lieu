"""
NXB Integration Bridge - Main Application

Cầu nối giữa Companion Writer và AI Publisher Pro
để tạo thành Nhà Xuất Bản Số hoàn chỉnh.

Usage:
    uvicorn integration_bridge.main:app --host 0.0.0.0 --port 3003 --reload
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
from datetime import datetime

from .routers import bridge_router, webhook_router
from .utils.config import settings
from .models.schemas import HealthResponse, ServiceHealth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"   AI Publisher Pro: {settings.APP_API_URL}")
    print(f"   Companion Writer: {settings.CW_API_URL}")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## NXB Integration Bridge

    Cầu nối giữa **Companion Writer** (Sáng tác) và **AI Publisher Pro** (Dịch thuật/Xuất bản)
    để tạo thành **Nhà Xuất Bản Số** hoàn chỉnh.

    ### Quy trình:
    1. **Sáng tác** (CW) → 2. **Dịch thuật** (APP) → 3. **Xuất bản** (Unified)

    ### Endpoints chính:
    - `POST /api/bridge/translate` - Dịch draft từ CW qua APP
    - `POST /api/bridge/export` - Xuất file (PDF/DOCX/EPUB)
    - `GET /api/bridge/jobs/{id}` - Theo dõi trạng thái job

    ### Services kết nối:
    - **AI Publisher Pro**: Port 3000
    - **Companion Writer**: Port 3002
    - **Integration Bridge**: Port 3003
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(bridge_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Cầu nối NXB Số - Companion Writer ↔ AI Publisher Pro",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of all connected services"""
    services = []

    # Check AI Publisher Pro
    app_health = await _check_service_health(
        "AI Publisher Pro",
        f"{settings.APP_API_URL}/health"
    )
    services.append(app_health)

    # Check Companion Writer
    cw_health = await _check_service_health(
        "Companion Writer",
        f"{settings.CW_API_URL}/api/health"
    )
    services.append(cw_health)

    # Determine overall status
    statuses = [s.status for s in services]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif all(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        services=services,
        timestamp=datetime.utcnow()
    )


async def _check_service_health(name: str, url: str) -> ServiceHealth:
    """Check health of a single service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = datetime.utcnow()
            response = await client.get(url)
            end = datetime.utcnow()
            latency = (end - start).total_seconds() * 1000

            if response.status_code == 200:
                return ServiceHealth(
                    name=name,
                    status="healthy",
                    url=url,
                    latency_ms=latency
                )
            else:
                return ServiceHealth(
                    name=name,
                    status="unhealthy",
                    url=url,
                    latency_ms=latency,
                    error=f"Status code: {response.status_code}"
                )
    except Exception as e:
        return ServiceHealth(
            name=name,
            status="unhealthy",
            url=url,
            error=str(e)
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )


# For running with python -m
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "integration_bridge.main:app",
        host="0.0.0.0",
        port=3003,
        reload=True
    )
