#!/bin/bash
# Stop Translation Server

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🛑 Stopping Translation Server..."
echo ""

# Method 1: Kill by PID file
if [ -f ".server.pid" ]; then
    PID=$(cat .server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null
        sleep 1
        
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
        fi
        
        echo -e "${GREEN}✓ Stopped server (PID: $PID)${NC}"
        rm .server.pid
    else
        echo -e "${YELLOW}⚠️  Process $PID not found${NC}"
        rm .server.pid
    fi
fi

# Method 2: Kill by port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -ti:8000)
    PROCESS_CMD=$(ps -p $PID -o command= 2>/dev/null)
    
    if echo "$PROCESS_CMD" | grep -q "translator_project"; then
        kill -9 $PID 2>/dev/null
        echo -e "${GREEN}✓ Killed translation server on port 8000 (PID: $PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Port 8000 occupied by: $PROCESS_CMD${NC}"
        read -p "Kill it anyway? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill -9 $PID 2>/dev/null
            echo -e "${GREEN}✓ Killed PID: $PID${NC}"
        fi
    fi
else
    echo -e "${YELLOW}✓ No server running on port 8000${NC}"
fi

echo ""
echo "Server stopped successfully"
