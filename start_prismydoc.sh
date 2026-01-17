#!/bin/bash
# ===============================================================
# Start ai-publisher-pro for PrismyDoc integration
# ===============================================================

echo "Starting AI-Publisher-Pro Engine for PrismyDoc..."

# Load environment
export $(cat config/prismydoc.env | grep -v '^#' | xargs)

# Create directories
mkdir -p uploads outputs logs data

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required"
    exit 1
fi

# Check dependencies
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start FastAPI server
echo "Starting FastAPI on port $PORT..."
uvicorn api.main:app --host $HOST --port $PORT --reload

# Or for production:
# gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b $HOST:$PORT
