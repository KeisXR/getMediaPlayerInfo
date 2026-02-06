#!/system/bin/sh
# Media Player API - Standalone Shell Script Version
PORT="${1:-8765}"

log() { echo "[MediaAPI] $1"; }

get_device_info() {
    os_version=$(getprop ro.build.version.release)
    device_model=$(getprop ro.product.model)
    hostname=$(getprop net.hostname)
    [ -z "$hostname" ] && hostname=$(getprop ro.product.device)
    echo "{\"os\":\"Android ${os_version}\",\"hostname\":\"${hostname}\",\"device\":\"${device_model}\",\"platform\":\"android\"}"
}

get_media_info() {
    output=$(su -c "dumpsys media_session" 2>/dev/null)
    [ -z "$output" ] && { echo "null"; return; }
    
    active_pkg=$(echo "$output" | grep "global priority session is" | awk '{print $5}')
    [ -z "$active_pkg" ] && { echo "null"; return; }
    
    title=$(echo "$output" | grep "android.media.metadata.TITLE:" | head -1 | sed 's/.*TITLE: *//' | tr -d '\r\n')
    artist=$(echo "$output" | grep "android.media.metadata.ARTIST:" | head -1 | sed 's/.*ARTIST: *//' | tr -d '\r\n')
    album=$(echo "$output" | grep "android.media.metadata.ALBUM:" | head -1 | sed 's/.*ALBUM: *//' | tr -d '\r\n')
    
    state_num=$(echo "$output" | grep "state=PlaybackState" | head -1 | grep -o "state=[0-9]*" | head -1 | cut -d= -f2)
    status="unknown"
    [ "$state_num" = "3" ] && status="playing"
    [ "$state_num" = "2" ] && status="paused"
    [ "$state_num" = "1" ] && status="stopped"
    
    app_name=$(echo "$active_pkg" | rev | cut -d. -f1 | rev)
    echo "{\"source_app\":\"${app_name}\",\"title\":\"${title}\",\"artist\":\"${artist}\",\"album\":\"${album}\",\"status\":\"${status}\",\"thumbnail\":null}"
}

log "Checking root..."
su -c "echo ok" >/dev/null 2>&1 || { log "ERROR: Root required!"; exit 1; }
log "Root: OK"
log "Starting on port ${PORT}..."
log "API: http://localhost:${PORT}/now-playing"
log ""

FIFO="/data/local/tmp/media-api-fifo"
rm -f "$FIFO"
mkfifo "$FIFO"

while true; do
    (
        # Read request from stdin (from nc)
        read -r req_line
        path=$(echo "$req_line" | tr -d '\r' | awk '{print $2}')
        log "Path: $path"
        
        # Consume headers
        while read -r line; do
            line=$(echo "$line" | tr -d '\r')
            [ -z "$line" ] && break
        done
        
        # Generate response
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
                body="{\"error\":\"not found\",\"path\":\"$path\"}"
                ;;
        esac
        
        len=${#body}
        printf "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n%s" "$len" "$body"
    ) < "$FIFO" | busybox nc -l -p $PORT > "$FIFO" 2>/dev/null
done
