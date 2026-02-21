#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Starting the TraqCheck application..."

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

# Start the frontend
echo "Starting the React frontend..."
cd frontend
npm start &
FRONTEND_PID=$!

# Wait a bit for the frontend to start
sleep 5

# Check if frontend is running
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}Frontend started successfully!${NC}"
else
    echo -e "${RED}Failed to start the frontend.${NC}"
    exit 1
fi

cd ..

# Start the backend
echo "Starting the Flask backend..."
python3 app.py &
BACKEND_PID=$!

# Wait a bit for the backend to start
sleep 2

# Check if the backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}Backend started successfully!${NC}"
    echo -e "${GREEN}Frontend running on http://localhost:3000${NC}"
    echo -e "${GREEN}Backend running on http://localhost:5000${NC}"
    echo "Press Ctrl+C to stop both servers."
    wait $BACKEND_PID
else
    echo -e "${RED}Failed to start the backend.${NC}"
    kill $FRONTEND_PID 2>/dev/null
    exit 1
fi