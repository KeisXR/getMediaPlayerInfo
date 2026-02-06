#!/bin/bash
# Linux startup script for Media Player API

cd "$(dirname "$0")"

echo "==================================="
echo "  Media Player API - Linux Setup"
echo "==================================="
echo ""

# Check for Python
echo "[1/4] Checking Python..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found!"
    echo "Please install Python 3.10 or later."
    exit 1
fi
echo "      Using: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

# Check for python3-venv package (required on some distros)
echo "[2/4] Checking venv module..."
if ! $PYTHON_CMD -c "import venv" 2>/dev/null; then
    echo "ERROR: Python venv module not found!"
    echo "Please install it with:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  Fedora: sudo dnf install python3-venv"
    echo "  Arch: sudo pacman -S python"
    exit 1
fi

# Create virtual environment if it doesn't exist or is broken
echo "[3/4] Setting up virtual environment..."
if [ ! -f "venv/bin/activate" ]; then
    echo "      Creating venv..."
    rm -rf venv 2>/dev/null
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ] || [ ! -f "venv/bin/activate" ]; then
        echo "ERROR: Failed to create virtual environment"
        echo "Try: $PYTHON_CMD -m venv venv"
        exit 1
    fi
fi

# Activate venv
source venv/bin/activate 2>/dev/null || true

# Install dependencies (use venv pip directly for reliability)
echo "[4/4] Installing dependencies..."
./venv/bin/pip install --quiet --upgrade pip 2>/dev/null
./venv/bin/pip install --quiet -r requirements.txt 2>/dev/null

echo ""
echo "==================================="
echo "  Starting Media Player API Server"
echo "==================================="
echo ""
echo "API:       http://localhost:8765/now-playing"
echo "WebSocket: ws://localhost:8765/ws"
echo ""
echo "Filter options: --filter all|no-browser|apps-only"
echo ""
echo "Press Ctrl+C to stop"
echo ""

./venv/bin/python main.py "$@"
