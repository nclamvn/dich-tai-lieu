#!/bin/bash
# =============================================================================
# AI Publisher Pro — Backup Script
# Backs up all SQLite databases and uploaded files
# Usage: bash backup.sh
# =============================================================================

set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_NAME="aipub_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

mkdir -p "$BACKUP_PATH"

echo "═══════════════════════════════════════════════════"
echo "  AI Publisher Pro — Backup"
echo "  Target: ${BACKUP_PATH}.tar.gz"
echo "═══════════════════════════════════════════════════"
echo ""

# Check if running in Docker
if docker compose ps --quiet backend 2>/dev/null | grep -q .; then
    echo "[1/3] Copying data from Docker volume..."
    docker compose cp backend:/app/data "$BACKUP_PATH/data"
else
    echo "[1/3] Copying local data directory..."
    if [ -d data ]; then
        cp -r data/ "$BACKUP_PATH/data/"
    else
        echo "  WARNING: No data/ directory found"
    fi
fi

# Copy .env (without secrets shown)
echo "[2/3] Backing up configuration..."
if [ -f .env ]; then
    cp .env "$BACKUP_PATH/.env.backup"
fi

# Compress
echo "[3/3] Compressing..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"

SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
echo ""
echo "  Backup: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz ($SIZE)"

# Keep last 7 backups
KEPT=7
TOTAL=$(ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | wc -l)
if [ "$TOTAL" -gt "$KEPT" ]; then
    ls -t "$BACKUP_DIR"/*.tar.gz | tail -n +"$((KEPT + 1))" | xargs rm -f
    echo "  Cleaned old backups (keeping last $KEPT)"
fi

echo "  Done"
