#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# sync_to_public.sh - Sync releases to public Dich-Viet repo
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage: ./scripts/sync_to_public.sh [version]
# Example: ./scripts/sync_to_public.sh v3.3.0
#
# This script:
# 1. Runs a security audit
# 2. Creates a sanitized copy of the codebase
# 3. Syncs to ~/Dich-Viet
# 4. Commits and pushes to github.com/nclamvn/Dich-Viet
# ═══════════════════════════════════════════════════════════════════════════════

set -e

VERSION=${1:-""}
PRIVATE_REPO="$HOME/ai-publisher-pro-public"
PUBLIC_REPO="$HOME/Dich-Viet"

echo "═══════════════════════════════════════════════════════════════════════"
echo "  Sync to Public Repository"
echo "═══════════════════════════════════════════════════════════════════════"

# Verify we're in private repo
if [ "$(pwd)" != "$PRIVATE_REPO" ]; then
    echo "ERROR: Must run from $PRIVATE_REPO"
    echo "  cd $PRIVATE_REPO && ./scripts/sync_to_public.sh $VERSION"
    exit 1
fi

# Verify version provided
if [ -z "$VERSION" ]; then
    echo "ERROR: Version required."
    echo "  Usage: ./scripts/sync_to_public.sh v3.3.0"
    exit 1
fi

# Verify public repo exists
if [ ! -d "$PUBLIC_REPO/.git" ]; then
    echo "ERROR: Public repo not found at $PUBLIC_REPO"
    echo "  Clone it first: git clone https://github.com/nclamvn/Dich-Viet.git $PUBLIC_REPO"
    exit 1
fi

echo ""
echo "[1/6] Running security audit..."
LEAKED=$(grep -rn "sk-ant-api\|sk-proj-" . --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" 2>/dev/null | grep -v node_modules | grep -v ".example" | grep -v "test" | grep -v "__pycache__" || true)
if [ -n "$LEAKED" ]; then
    echo "ABORT: Found potential API keys!"
    echo "$LEAKED"
    exit 1
fi
echo "  Security audit passed"

echo ""
echo "[2/6] Syncing files..."
rsync -a --delete \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='.env.production' \
    --exclude='.env.development' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.next' \
    --exclude='dist' \
    --exclude='.pytest_cache' \
    --exclude='coverage' \
    --exclude='.playwright-mcp' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite3' \
    --exclude='data/sessions/*' \
    --exclude='data/uploads/*' \
    --exclude='data/settings.json' \
    --exclude='data/api_keys.enc' \
    --exclude='data/.key' \
    --exclude='data/cache/translation_cache.json' \
    --exclude='data/cache/aps' \
    --exclude='data/provider_stats.json' \
    --exclude='uploads/*' \
    --exclude='output/*' \
    --exclude='test_outputs/*' \
    --exclude='outputs/*' \
    --exclude='logs/*' \
    --exclude='*.log' \
    --exclude='*.pem' \
    --exclude='*.key' \
    --exclude='*.p12' \
    --exclude='id_rsa*' \
    --exclude='credentials.json' \
    --exclude='service-account*.json' \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    --exclude='*.bak' \
    --exclude='*.tmp' \
    --exclude='CLAUDE.md' \
    --exclude='.claude' \
    --exclude='.claude.json' \
    --exclude='docs/HANDOVER_*.md' \
    --exclude='docs/XRAY*.md' \
    --exclude='docs/REPORT_PROJECT_XRAY*.md' \
    "$PRIVATE_REPO/" "$PUBLIC_REPO/"

echo "  Files synced"

echo ""
echo "[3/6] Cleaning user data from data/..."
find "$PUBLIC_REPO/data" -type f -not -name ".gitkeep" -delete 2>/dev/null || true
find "$PUBLIC_REPO/uploads" -type f -not -name ".gitkeep" -delete 2>/dev/null || true
find "$PUBLIC_REPO/output" -type f -not -name ".gitkeep" -delete 2>/dev/null || true
find "$PUBLIC_REPO/test_outputs" -type f -not -name ".gitkeep" -delete 2>/dev/null || true
echo "  User data cleaned"

echo ""
echo "[4/6] Restoring .gitkeep files..."
for dir in data data/sessions data/uploads data/errors data/cache data/checkpoints \
           data/translation_memory data/usage data/users data/analytics data/author_uploads \
           data/authors data/backups data/books data/books_v2 data/exports data/input \
           data/logs data/output data/temp outputs logs uploads output test_outputs; do
    mkdir -p "$PUBLIC_REPO/$dir"
    touch "$PUBLIC_REPO/$dir/.gitkeep"
done
echo "  .gitkeep files restored"

echo ""
echo "[5/6] Committing changes..."
cd "$PUBLIC_REPO"
git add -A
git commit -m "Release $VERSION" || echo "  No changes to commit"
echo "  Changes committed"

echo ""
echo "[6/6] Pushing to GitHub..."
git push origin main
git tag -a "$VERSION" -m "Release $VERSION" 2>/dev/null || git tag -d "$VERSION" && git tag -a "$VERSION" -m "Release $VERSION"
git push origin "$VERSION" --force
echo "  Pushed to GitHub"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "  Sync Complete!"
echo "  Public repo: https://github.com/nclamvn/Dich-Viet"
echo "  Version: $VERSION"
echo "═══════════════════════════════════════════════════════════════════════"
