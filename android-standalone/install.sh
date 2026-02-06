#!/system/bin/sh
# Installation script for Media Player API (Shell version)
# Can be used to set up auto-start via init.d or as a service

INSTALL_DIR="/data/local/tmp/media-api"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=================================="
echo " Media Player API - Installation"
echo "=================================="
echo ""

# Check root
if ! su -c "echo test" >/dev/null 2>&1; then
    echo "ERROR: Root access required!"
    exit 1
fi

echo "[1/3] Creating installation directory..."
su -c "mkdir -p $INSTALL_DIR"

echo "[2/3] Copying files..."
su -c "cp $SCRIPT_DIR/media-api.sh $INSTALL_DIR/"
su -c "cp $SCRIPT_DIR/media-api-socat.sh $INSTALL_DIR/" 2>/dev/null
su -c "chmod 755 $INSTALL_DIR/*.sh"

echo "[3/3] Creating start script..."
cat << 'EOF' | su -c "cat > $INSTALL_DIR/start.sh"
#!/system/bin/sh
cd /data/local/tmp/media-api
nohup ./media-api.sh 8765 > /data/local/tmp/media-api.log 2>&1 &
echo $! > /data/local/tmp/media-api.pid
echo "Started with PID $(cat /data/local/tmp/media-api.pid)"
EOF
su -c "chmod 755 $INSTALL_DIR/start.sh"

cat << 'EOF' | su -c "cat > $INSTALL_DIR/stop.sh"
#!/system/bin/sh
if [ -f /data/local/tmp/media-api.pid ]; then
    kill $(cat /data/local/tmp/media-api.pid) 2>/dev/null
    rm /data/local/tmp/media-api.pid
    echo "Stopped"
else
    echo "Not running"
fi
EOF
su -c "chmod 755 $INSTALL_DIR/stop.sh"

echo ""
echo "=================================="
echo " Installation Complete!"
echo "=================================="
echo ""
echo "Files installed to: $INSTALL_DIR"
echo ""
echo "To start the server:"
echo "  su -c '$INSTALL_DIR/start.sh'"
echo ""
echo "To stop the server:"
echo "  su -c '$INSTALL_DIR/stop.sh'"
echo ""
echo "API will be available at:"
echo "  http://localhost:8765/now-playing"
echo ""
