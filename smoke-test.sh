#!/bin/bash
# =============================================================================
# AI Publisher Pro — Smoke Test Suite
# Verifies deployment is working by checking 15+ endpoints
# Usage: bash smoke-test.sh [BASE_URL]
# =============================================================================

set -euo pipefail

BASE_URL="${1:-http://localhost:3000}"
PASS=0
FAIL=0
TOTAL=0

check() {
    local name="$1"
    local url="$2"
    local expect="${3:-200}"
    TOTAL=$((TOTAL + 1))

    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

    if [ "$STATUS" = "$expect" ]; then
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name (expected $expect, got $STATUS)"
        FAIL=$((FAIL + 1))
    fi
}

echo "═══════════════════════════════════════════════════"
echo "  AI Publisher Pro — Smoke Test"
echo "  Target: $BASE_URL"
echo "═══════════════════════════════════════════════════"
echo ""

echo "[Core]"
check "Health"               "$BASE_URL/health"
check "Health (detailed)"    "$BASE_URL/api/health/detailed"
check "System info"          "$BASE_URL/api/system/info"
check "API docs"             "$BASE_URL/docs"

echo ""
echo "[Jobs & Translation]"
check "Jobs list"            "$BASE_URL/api/jobs"
check "APS v2 jobs"          "$BASE_URL/api/v2/aps/jobs"

echo ""
echo "[Publishing]"
check "Book writer projects" "$BASE_URL/api/v2/books"
check "Screenplay projects"  "$BASE_URL/api/screenplay/projects"

echo ""
echo "[Knowledge]"
check "Translation Memory"   "$BASE_URL/api/tm/segments"
check "Glossary terms"       "$BASE_URL/api/glossary/terms"

echo ""
echo "[Monitoring]"
check "Dashboard costs"      "$BASE_URL/api/monitoring/costs"
check "Error tracker"        "$BASE_URL/api/errors"
check "Audit log"            "$BASE_URL/api/monitoring/audit"

echo ""
echo "[Settings]"
check "Settings"             "$BASE_URL/api/settings"
check "System status"        "$BASE_URL/api/system/status"
check "Cache stats"          "$BASE_URL/api/system/cache/stats"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed ($TOTAL total)"
if [ $FAIL -eq 0 ]; then
    echo "  ✅ ALL CHECKS PASSED"
else
    echo "  ⚠️  $FAIL CHECKS FAILED"
fi
echo "═══════════════════════════════════════════════════"

exit $FAIL
