#!/bin/bash

# ============================================================================
# API Server Startup Script - AI Translator Pro
# Mục đích: Start API server với proper configuration và monitoring
# ============================================================================

cd "$(dirname "$0")/.." || exit 1

echo "=========================================================================="
echo "  AI TRANSLATOR PRO - API SERVER"
echo "=========================================================================="
echo ""

# Check if server is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  API server đã đang chạy trên port 8000"
    echo ""
    echo "Bạn muốn:"
    echo "  1. Giữ nguyên server hiện tại"
    echo "  2. Restart server"
    read -p "Chọn (1/2): " -n 1 -r choice
    echo ""

    if [ "$choice" = "2" ]; then
        echo "🔄 Stopping current server..."
        pkill -f "uvicorn.*main:app"
        sleep 2
    else
        echo "Giữ nguyên server hiện tại."
        exit 0
    fi
fi

# Create logs directory
mkdir -p logs

# Set environment
export PYTHONDONTWRITEBYTECODE=1

echo "🚀 Starting API Server..."
echo "  - Host: 0.0.0.0"
echo "  - Port: 8000"
echo "  - Log: logs/server.log"
echo ""

# Start server
python3 -m uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    2>&1 | tee logs/server.log &

SERVER_PID=$!

sleep 2

# Verify startup
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ API Server started successfully!"
    echo "  - PID: $SERVER_PID"
    echo "  - URL: http://localhost:8000"
    echo "  - Docs: http://localhost:8000/docs"
    echo "  - UI: http://localhost:8000/ui"
    echo ""
    echo "Monitor logs: tail -f logs/server.log"
    echo "Stop server: pkill -f 'uvicorn.*main:app'"
else
    echo "❌ Failed to start API server"
    echo "Check logs: tail -50 logs/server.log"
    exit 1
fi
