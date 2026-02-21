#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "Setting up the environment..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

echo -e "${GREEN}Python 3 found.${NC}"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed. Installing pip...${NC}"
    curl -s https://bootstrap.pypa.io/get-pip.py | python3
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install pip.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}pip3 found.${NC}"

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip3 install -r requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Dependencies installed successfully.${NC}"
else
    echo -e "${RED}Failed to install dependencies.${NC}"
    exit 1
fi

echo -e "${GREEN}Setup completed successfully!${NC}"