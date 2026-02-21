#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Starting the Flask server..."

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: app.py not found.${NC}"
    exit 1
fi

# Start the server
python3 app.py &
SERVER_PID=$!

# Wait a bit for the server to start
sleep 2

# Check if the server is running
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}Server started successfully!${NC}"
    echo -e "${GREEN}Running on http://localhost:5000${NC}"
    echo "Press Ctrl+C to stop the server."
    wait $SERVER_PID
else
    echo -e "${RED}Failed to start the server.${NC}"
    exit 1
fi