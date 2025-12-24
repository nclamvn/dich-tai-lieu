#!/bin/bash

# ============================================================================
# Stop All Services Script - AI Translator Pro
# Mục đích: Gracefully stop all services
# ============================================================================

echo "=========================================================================="
echo "  AI TRANSLATOR PRO - STOPPING ALL SERVICES"
echo "=========================================================================="
echo ""

echo "🛑 Stopping API Server..."
pkill -f "uvicorn.*main:app"
sleep 1
echo "✅ API Server stopped"
echo ""

echo "🛑 Stopping Batch Processor..."
pkill -f "start_batch_processor.py"
sleep 1
echo "✅ Batch Processor stopped"
echo ""

echo "=========================================================================="
echo "  ALL SERVICES STOPPED"
echo "=========================================================================="
echo ""
echo "Start services again with:"
echo "  - ./scripts/start_server.sh"
echo "  - ./scripts/start_processor.sh"
