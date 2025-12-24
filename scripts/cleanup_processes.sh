#!/bin/bash

# ============================================================================
# Process Cleanup Script - AI Translator Pro
# Mục đích: Dọn dẹp tất cả orphaned processes và reset system về trạng thái sạch
# ============================================================================

echo "=========================================================================="
echo "  AI TRANSLATOR PRO - PROCESS CLEANUP SCRIPT"
echo "=========================================================================="
echo ""
echo "⚠️  Script này sẽ KILL tất cả processes liên quan đến translator project"
echo "Bao gồm: API servers, batch processors, background jobs, monitors"
echo ""
read -p "Bạn có chắc chắn muốn tiếp tục? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Hủy bỏ cleanup."
    exit 1
fi

echo ""
echo "=========================================================================="
echo "  BƯỚC 1: Liệt kê tất cả processes hiện tại"
echo "=========================================================================="

# Count processes
API_COUNT=$(ps aux | grep -E "api/main.py|uvicorn.*main:app" | grep -v grep | wc -l | tr -d ' ')
PROCESSOR_COUNT=$(ps aux | grep "start_batch_processor.py" | grep -v grep | wc -l | tr -d ' ')
TRANSLATE_COUNT=$(ps aux | grep "translate_pdf.py" | grep -v grep | wc -l | tr -d ' ')
PYTHON_COUNT=$(ps aux | grep "python3.*translator_project" | grep -v grep | wc -l | tr -d ' ')

echo "📊 Processes hiện tại:"
echo "  - API servers: $API_COUNT"
echo "  - Batch processors: $PROCESSOR_COUNT"
echo "  - Translation jobs: $TRANSLATE_COUNT"
echo "  - Total Python processes: $PYTHON_COUNT"
echo ""

echo "=========================================================================="
echo "  BƯỚC 2: Kill API servers"
echo "=========================================================================="

# Kill all API servers
echo "🔪 Killing API servers..."
pkill -9 -f "api/main.py" 2>/dev/null
pkill -9 -f "uvicorn.*main:app" 2>/dev/null

# Kill processes on specific ports
for port in 8000 8001 9000; do
    PID=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "  Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null
    fi
done

sleep 1
REMAINING=$(ps aux | grep -E "api/main.py|uvicorn.*main:app" | grep -v grep | wc -l | tr -d ' ')
echo "✅ API servers killed. Remaining: $REMAINING"
echo ""

echo "=========================================================================="
echo "  BƯỚC 3: Kill batch processors"
echo "=========================================================================="

echo "🔪 Killing batch processors..."
pkill -9 -f "start_batch_processor.py" 2>/dev/null

sleep 1
REMAINING=$(ps aux | grep "start_batch_processor.py" | grep -v grep | wc -l | tr -d ' ')
echo "✅ Batch processors killed. Remaining: $REMAINING"
echo ""

echo "=========================================================================="
echo "  BƯỚC 4: Kill translation jobs"
echo "=========================================================================="

echo "🔪 Killing active translation jobs..."
pkill -9 -f "translate_pdf.py" 2>/dev/null

sleep 1
REMAINING=$(ps aux | grep "translate_pdf.py" | grep -v grep | wc -l | tr -d ' ')
echo "✅ Translation jobs killed. Remaining: $REMAINING"
echo ""

echo "=========================================================================="
echo "  BƯỚC 5: Kill background monitors và scripts"
echo "=========================================================================="

echo "🔪 Killing monitoring scripts..."
pkill -9 -f "monitor_phase" 2>/dev/null
pkill -9 -f "phase.*test.sh" 2>/dev/null

sleep 1
echo "✅ Monitors killed"
echo ""

echo "=========================================================================="
echo "  BƯỚC 6: Cleanup temporary files"
echo "=========================================================================="

echo "🧹 Cleaning up temporary test logs..."
# Count files before cleanup
LOG_COUNT=$(ls -1 /tmp/phase*.log 2>/dev/null | wc -l | tr -d ' ')
SCRIPT_COUNT=$(ls -1 /tmp/phase*.sh 2>/dev/null | wc -l | tr -d ' ')

echo "  - Found $LOG_COUNT log files"
echo "  - Found $SCRIPT_COUNT script files"

# Remove old test logs (keep recent ones)
find /tmp -name "phase*.log" -mtime +1 -delete 2>/dev/null
find /tmp -name "phase*.sh" -mtime +1 -delete 2>/dev/null

# Keep a summary log
echo "  - Archived old logs"
echo "✅ Temporary files cleaned"
echo ""

echo "=========================================================================="
echo "  BƯỚC 7: Verify cleanup"
echo "=========================================================================="

API_COUNT=$(ps aux | grep -E "api/main.py|uvicorn.*main:app" | grep -v grep | wc -l | tr -d ' ')
PROCESSOR_COUNT=$(ps aux | grep "start_batch_processor.py" | grep -v grep | wc -l | tr -d ' ')
TRANSLATE_COUNT=$(ps aux | grep "translate_pdf.py" | grep -v grep | wc -l | tr -d ' ')

echo "📊 Processes sau cleanup:"
echo "  - API servers: $API_COUNT"
echo "  - Batch processors: $PROCESSOR_COUNT"
echo "  - Translation jobs: $TRANSLATE_COUNT"
echo ""

if [ "$API_COUNT" -eq 0 ] && [ "$PROCESSOR_COUNT" -eq 0 ] && [ "$TRANSLATE_COUNT" -eq 0 ]; then
    echo "✅✅✅ CLEANUP THÀNH CÔNG! ✅✅✅"
    echo ""
    echo "System đã được reset về trạng thái sạch."
    echo "Bạn có thể start lại services với:"
    echo "  - API Server: ./scripts/start_server.sh"
    echo "  - Batch Processor: ./scripts/start_processor.sh"
else
    echo "⚠️  CẢNH BÁO: Vẫn còn một số processes đang chạy"
    echo "Kiểm tra thủ công với: ps aux | grep python"
fi

echo ""
echo "=========================================================================="
echo "  CLEANUP HOÀN TẤT"
echo "=========================================================================="
