#!/bin/bash
# =============================================================================
# AI Publisher Pro — Update Script
# Pulls latest code, rebuilds, and restarts
# Usage: bash update.sh
# =============================================================================

set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  AI Publisher Pro — Update"
echo "═══════════════════════════════════════════════════"
echo ""

# Backup first
echo "[1/4] Creating backup before update..."
bash backup.sh
echo ""

# Pull latest
echo "[2/4] Pulling latest code..."
git pull origin main
echo ""

# Rebuild
echo "[3/4] Rebuilding containers..."
docker compose build --quiet 2>&1 | tail -3
echo ""

# Restart
echo "[4/4] Restarting services..."
docker compose down
docker compose up -d

# Wait for health
echo "  Waiting for health check..."
BACKEND_PORT="${BACKEND_PORT:-3000}"
RETRIES=0
until curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge 30 ]; then
        echo "  WARNING: Backend not healthy after 60s. Check: docker compose logs backend"
        exit 1
    fi
    sleep 2
    printf "."
done
echo ""
echo ""
echo "  Update complete. System healthy."
