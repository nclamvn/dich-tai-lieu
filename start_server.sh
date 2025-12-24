#!/bin/bash

# AI Translator Pro - Startup Script
# Port: 8080 (tránh xung đột với các dự án khác)

echo "🚀 Starting AI Translator Pro on port 8080..."
echo "📍 Dashboard: http://localhost:8080/ui"
echo "📖 API Docs: http://localhost:8080/docs"
echo ""

cd "$(dirname "$0")"

# Kill any existing process on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null

# Start server
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
