#!/data/data/com.termux/files/usr/bin/bash
# Termux startup script for Media Player API

echo "==================================="
echo "  Media Player API - Termux Setup"
echo "==================================="
echo ""

# Check if running in Termux
if [ -z "$TERMUX_VERSION" ]; then
    echo "Warning: This script is designed for Termux."
    echo "Some features may not work correctly."
fi

# Check for root access
echo "[1/4] Checking root access..."
if su -c "echo test" > /dev/null 2>&1; then
    echo "      ✓ Root access available"
else
    echo "      ✗ Root access NOT available"
    echo ""
    echo "ERROR: This app requires root access (KernelSU/Magisk)."
    echo "Please grant root access to Termux and try again."
    exit 1
fi

# Install Python if not present
echo "[2/4] Checking Python..."
if ! command -v python &> /dev/null; then
    echo "      Installing Python..."
    pkg install -y python
fi
echo "      ✓ Python $(python --version 2>&1 | cut -d' ' -f2)"

# Create and activate virtual environment
echo "[3/4] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate

# Install dependencies (Android doesn't need winrt/dbus packages)
echo "[4/4] Installing dependencies..."
pip install --quiet fastapi uvicorn websockets

echo ""
echo "==================================="
echo "  Starting Media Player API Server"
echo "==================================="
echo ""
echo "API:       http://localhost:8765/now-playing"
echo "WebSocket: ws://localhost:8765/ws"
echo ""
echo "To access from other devices, use your device's IP address."
echo "Press Ctrl+C to stop."
echo ""

python main.py
