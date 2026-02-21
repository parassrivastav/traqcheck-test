#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Starting the TraqCheck application..."

VENV_DIR=".venv"
PYTHON_BIN="python3"
FRONTEND_PID=""
BACKEND_PID=""

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    PYTHON_BIN="python"
fi

# Load env if present
if [ -f ".env" ]; then
    # shellcheck disable=SC1091
    source ".env"
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: app.py not found.${NC}"
    exit 1
fi

# Check if frontend exists
if [ ! -d "frontend" ]; then
    echo -e "${RED}Error: frontend directory not found.${NC}"
    exit 1
fi

cleanup() {
    if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null; fi
    if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null; fi
}

trap cleanup EXIT INT TERM

# Start the frontend
echo "Starting the React frontend..."
cd frontend
HOST=127.0.0.1 npm start &
FRONTEND_PID=$!

# Wait a bit for the frontend to start
sleep 5

# Check if frontend is running
if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${GREEN}Frontend started successfully!${NC}"
else
    echo -e "${RED}Failed to start the frontend.${NC}"
    cleanup
    exit 1
fi

cd ..

# Start the backend
echo "Starting the Flask backend..."
$PYTHON_BIN app.py &
BACKEND_PID=$!

# Wait a bit for the backend to start
sleep 2

# Check if the backend is running
if kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${GREEN}Backend started successfully!${NC}"
    echo -e "${GREEN}Frontend running on http://localhost:3000${NC}"
    echo -e "${GREEN}Backend running on http://localhost:5000${NC}"

    TELEGRAM_TOKEN="${TELEGRAM_API_TOKEN:-${TELEGRAM_API_KEY:-}}"
    if [ -n "${TELEGRAM_TOKEN:-}" ] && [[ "${TELEGRAM_TOKEN}" != your-* ]] && \
       [ -n "${PUBLIC_BASE_URL:-}" ] && [[ "${PUBLIC_BASE_URL}" != https://your-* ]]; then
        if command -v curl >/dev/null 2>&1; then
            echo "Configuring Telegram webhook..."
            curl -sS -X POST http://127.0.0.1:5000/telegram/setup-webhook >/tmp/traqcheck_webhook_setup.json || true
            echo -e "${GREEN}Webhook setup response saved to /tmp/traqcheck_webhook_setup.json${NC}"
        else
            echo -e "${RED}curl not found; skipping automatic webhook setup.${NC}"
        fi
    else
        echo -e "${RED}Telegram webhook not auto-configured. Set TELEGRAM_API_TOKEN/TELEGRAM_API_KEY and PUBLIC_BASE_URL in .env.${NC}"
    fi
    echo "Press Ctrl+C to stop all services."
    wait "$BACKEND_PID"
else
    echo -e "${RED}Failed to start the backend.${NC}"
    cleanup
    exit 1
fi
