#!/system/bin/sh
# Simple HTTP Server using socat (alternative to nc version)
# This version is more reliable for continuous serving
#
# Requirements:
# - socat (can be installed via Termux or Magisk module)
# - Root access

PORT="${1:-8765}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() {
    echo "[MediaAPI] $1"
}

# Check if socat is available
if ! command -v socat >/dev/null 2>&1; then
    echo "socat not found. Trying nc version instead..."
    exec "$SCRIPT_DIR/media-api.sh" "$PORT"
fi

# Check root
if ! su -c "echo test" >/dev/null 2>&1; then
    echo "Root access required!"
    exit 1
fi

log "Starting server on port ${PORT}..."
log "API: http://localhost:${PORT}/now-playing"
log ""

# Create handler script
HANDLER="/data/local/tmp/media-api-handler.sh"
cat > "$HANDLER" << 'HANDLER_EOF'
#!/system/bin/sh

get_device_info() {
    local os_version=$(getprop ro.build.version.release)
    local device_model=$(getprop ro.product.model)
    local hostname=$(getprop net.hostname)
    [ -z "$hostname" ] && hostname=$(getprop ro.product.device)
    echo "{\"os\":\"Android ${os_version}\",\"hostname\":\"${hostname}\",\"platform\":\"android\"}"
}

get_media_info() {
    local output=$(su -c "dumpsys media_session" 2>/dev/null)
    [ -z "$output" ] && { echo "null"; return; }
    
    local active_pkg=$(echo "$output" | grep -o "global priority session is [^ ]*" | cut -d' ' -f5)
    [ -z "$active_pkg" ] && active_pkg=$(echo "$output" | grep -o "Media session [^ ]*" | head -1 | cut -d' ' -f3)
    [ -z "$active_pkg" ] && { echo "null"; return; }
    
    local title=$(echo "$output" | grep -i "android.media.metadata.TITLE:" | head -1 | sed 's/.*TITLE: *//' | tr -d '\n\r')
    local artist=$(echo "$output" | grep -i "android.media.metadata.ARTIST:" | head -1 | sed 's/.*ARTIST: *//' | tr -d '\n\r')
    local album=$(echo "$output" | grep -i "android.media.metadata.ALBUM:" | head -1 | sed 's/.*ALBUM: *//' | tr -d '\n\r')
    
    local state_num=$(echo "$output" | grep -o "state=[0-9]*" | head -1 | cut -d'=' -f2)
    local status="unknown"
    [ "$state_num" = "3" ] && status="playing"
    [ "$state_num" = "2" ] && status="paused"
    
    local app_name=$(echo "$active_pkg" | rev | cut -d'.' -f1 | rev)
    
    echo "{\"source_app\":\"${app_name}\",\"title\":\"${title}\",\"artist\":\"${artist}\",\"album\":\"${album}\",\"status\":\"${status}\",\"thumbnail\":null}"
}

read request_line
method=$(echo "$request_line" | cut -d' ' -f1)
path=$(echo "$request_line" | cut -d' ' -f2)

while read header; do
    [ "$header" = $'\r' ] || [ -z "$header" ] && break
done

system_info=$(get_device_info)

case "$path" in
    "/"|"/status")
        body="{\"status\":\"running\",\"system\":${system_info}}"
        ;;
    "/now-playing")
        media_info=$(get_media_info)
        body="{\"system\":${system_info},\"media\":${media_info}}"
        ;;
    *)
        body="{\"error\":\"not found\"}"
        ;;
esac

len=${#body}
echo -e "HTTP/1.1 200 OK\r"
echo -e "Content-Type: application/json\r"
echo -e "Content-Length: ${len}\r"
echo -e "Access-Control-Allow-Origin: *\r"
echo -e "\r"
echo -n "$body"
HANDLER_EOF

chmod 755 "$HANDLER"

# Run socat server
socat TCP-LISTEN:${PORT},reuseaddr,fork EXEC:"$HANDLER"
