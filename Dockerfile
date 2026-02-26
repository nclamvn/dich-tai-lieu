# =============================================================================
# AI Publisher Pro — Production Backend Dockerfile
# Multi-stage build for minimal image size
# Python 3.13 | FastAPI + uvicorn
# =============================================================================

# Stage 1: Build dependencies
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (cache layer — only re-runs when lock file changes)
COPY requirements.lock ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.lock

# Stage 2: Production image
FROM python:3.13-slim

LABEL maintainer="AI Publisher Pro Team"
LABEL version="3.3.1"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=3000

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    fonts-noto-cjk \
    fonts-noto-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (selective — not everything)
COPY api/ ./api/
COPY core/ ./core/
COPY core_v2/ ./core_v2/
COPY ai_providers/ ./ai_providers/
COPY config/ ./config/
COPY integration_bridge/ ./integration_bridge/
COPY services/ ./services/
COPY beautification/ ./beautification/
COPY glossary/ ./glossary/
COPY ui/ ./ui/

# Create data directories
RUN mkdir -p data/uploads data/outputs data/cache data/checkpoints \
    data/translation_memory data/usage data/errors data/glossary \
    data/input data/output data/temp data/logs data/analytics \
    outputs backups \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:3000/health || exit 1

EXPOSE 3000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "1"]
