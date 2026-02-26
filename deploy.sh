#!/bin/bash
# =============================================================================
# AI Publisher Pro — Deployment Script v1.0
# Usage: bash deploy.sh
# =============================================================================

set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  AI Publisher Pro — Deployment Script v1.0"
echo "═══════════════════════════════════════════════════"

# ─── PRE-CHECKS ──────────────────────────────────────
echo ""
echo "[1/6] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo ""
    echo "Docker installed. Please log out and back in, then re-run this script."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose (v2) not found."
    echo "Install: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "  Docker $(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)"
echo "  Docker Compose $(docker compose version --short)"

# ─── ENVIRONMENT SETUP ───────────────────────────────
echo ""
echo "[2/6] Checking environment..."

if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        cp .env.production .env
        echo "  Created .env from .env.production template"
        echo ""
        echo "  IMPORTANT: Edit .env and configure:"
        echo "    - At least one AI API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)"
        echo "    - SESSION_SECRET (generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
        echo ""
        echo "  Then re-run: bash deploy.sh"
        exit 1
    else
        echo "ERROR: No .env file found."
        echo "Copy .env.production to .env and configure your settings."
        exit 1
    fi
fi

# Validate critical env vars
set +u  # Allow unset vars for checking
source .env 2>/dev/null || true
MISSING=""

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
    MISSING="At least one AI API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)"
fi

if [ "${SESSION_SECRET:-}" = "INSECURE-DEV-SECRET-CHANGE-IN-PRODUCTION" ] || [ -z "${SESSION_SECRET:-}" ]; then
    MISSING="${MISSING:+$MISSING\n  - }SESSION_SECRET must be set to a secure random string"
fi

set -u

if [ -n "$MISSING" ]; then
    echo "  Missing required configuration:"
    echo -e "  - $MISSING"
    echo ""
    echo "  Edit .env and set these values, then re-run."
    exit 1
fi

echo "  Environment configured"

# ─── BUILD ────────────────────────────────────────────
echo ""
echo "[3/6] Building containers (first time may take 5-10 minutes)..."
docker compose build --quiet 2>&1 | tail -5

echo "  Build complete"

# ─── DATA DIRS ────────────────────────────────────────
echo ""
echo "[4/6] Ensuring data directories..."
mkdir -p backups
echo "  Ready"

# ─── START ────────────────────────────────────────────
echo ""
echo "[5/6] Starting services..."
docker compose up -d

echo "  Waiting for backend health check..."
RETRIES=0
MAX_RETRIES=30
BACKEND_PORT="${BACKEND_PORT:-3000}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"

until curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo ""
        echo "  ERROR: Backend did not become healthy in 60 seconds."
        echo "  Check logs: docker compose logs backend"
        exit 1
    fi
    sleep 2
    printf "."
done
echo ""
echo "  Backend healthy"

# ─── SMOKE TEST ───────────────────────────────────────
echo ""
echo "[6/6] Running quick checks..."

if [ -f smoke-test.sh ]; then
    bash smoke-test.sh "http://localhost:${BACKEND_PORT}" || true
else
    # Inline quick check
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${BACKEND_PORT}/health" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "  Health: OK"
    else
        echo "  Health: FAILED ($STATUS)"
    fi
fi

# ─── DONE ─────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  AI Publisher Pro is running!"
echo ""
echo "  Backend API:  http://localhost:${BACKEND_PORT}"
echo "  Frontend UI:  http://localhost:${FRONTEND_PORT}"
echo "  API Docs:     http://localhost:${BACKEND_PORT}/docs"
echo "  Health:       http://localhost:${BACKEND_PORT}/health"
echo ""
echo "  Commands:"
echo "    docker compose logs -f      # View logs"
echo "    docker compose restart      # Restart"
echo "    docker compose down         # Stop"
echo "    bash backup.sh              # Backup data"
echo "    bash update.sh              # Update to latest"
echo "    bash smoke-test.sh          # Run health checks"
echo "═══════════════════════════════════════════════════"
