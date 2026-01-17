#!/bin/bash

# AI Translator Pro - Startup Script
# Port: 8080 (tránh xung đột với các dự án khác)

echo "🚀 Starting AI Translator Pro on port 8080..."
echo "📍 Dashboard: http://localhost:8080/ui"
echo "📖 API Docs: http://localhost:8080/docs"
echo ""

cd "$(dirname "$0")"

# Kill any existing process on port 8080
PID=$(lsof -ti:8080)
if [ ! -z "$PID" ]; then
  echo "⚠️  Killing existing process on port 8080 (PID: $PID)..."
  kill -9 $PID 2>/dev/null
  # Wait for port to be released
  while lsof -ti:8080 >/dev/null; do
    echo "⏳ Waiting for port 8080 to be released..."
    sleep 0.5
  done
  echo "✅ Port 8080 released."
fi

# Start server
echo "🚀 Starting Uvicorn..."
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
