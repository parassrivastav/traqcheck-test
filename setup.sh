#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Setting up the environment..."

VENV_DIR=".venv"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

echo -e "${GREEN}Python 3 found.${NC}"

# Create virtual environment if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment.${NC}"
        exit 1
    fi
fi

# Activate virtual environment
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Check if pip is available in the venv
if ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is not available in the virtual environment. Trying ensurepip...${NC}"
    python -m ensurepip --upgrade
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install pip.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Virtual environment ready.${NC}"

# Install dependencies
echo "Installing backend dependencies from requirements.txt..."
python -m pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Backend dependencies installed successfully.${NC}"
else
    echo -e "${RED}Failed to install backend dependencies.${NC}"
    exit 1
fi

# Install frontend dependencies
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed. Please install Node.js and npm first.${NC}"
    exit 1
fi

echo "Installing frontend dependencies..."
cd frontend
npm install
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Frontend dependencies installed successfully.${NC}"
else
    echo -e "${RED}Failed to install frontend dependencies.${NC}"
    exit 1
fi
cd ..

echo -e "${GREEN}Setup completed successfully!${NC}"
