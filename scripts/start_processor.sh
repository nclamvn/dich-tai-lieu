#!/bin/bash

# ============================================================================
# Batch Processor Startup Script - AI Translator Pro
# Mục đích: Start batch processor với proper configuration và monitoring
# ============================================================================

cd "$(dirname "$0")/.." || exit 1

echo "=========================================================================="
echo "  AI TRANSLATOR PRO - BATCH PROCESSOR"
echo "=========================================================================="
echo ""

# Check if processor is already running
if pgrep -f "start_batch_processor.py" > /dev/null 2>&1; then
    echo "⚠️  Batch processor đã đang chạy"
    echo ""
    echo "Bạn muốn:"
    echo "  1. Giữ nguyên processor hiện tại"
    echo "  2. Restart processor"
    read -p "Chọn (1/2): " -n 1 -r choice
    echo ""

    if [ "$choice" = "2" ]; then
        echo "🔄 Stopping current processor..."
        pkill -f "start_batch_processor.py"
        sleep 2
    else
        echo "Giữ nguyên processor hiện tại."
        exit 0
    fi
fi

# Create logs directory
mkdir -p logs

# Set environment
export PYTHONDONTWRITEBYTECODE=1

echo "🚀 Starting Batch Processor..."
echo "  - Log: logs/processor.log"
echo ""

# Start processor
python3 start_batch_processor.py 2>&1 | tee logs/processor.log &

PROCESSOR_PID=$!

sleep 2

# Verify startup
if ps -p $PROCESSOR_PID > /dev/null 2>&1; then
    echo "✅ Batch Processor started successfully!"
    echo "  - PID: $PROCESSOR_PID"
    echo ""
    echo "Monitor logs: tail -f logs/processor.log"
    echo "Stop processor: pkill -f 'start_batch_processor.py'"
else
    echo "❌ Failed to start batch processor"
    echo "Check logs: tail -50 logs/processor.log"
    exit 1
fi
