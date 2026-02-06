"""
Media Player API Server

A cross-platform API for detecting and broadcasting currently playing media.
"""
import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from system_info import get_system_info
from providers import (
    get_provider, 
    MediaProvider, 
    MediaInfo,
    FILTER_ALL,
    FILTER_NO_BROWSER,
    FILTER_APPS_ONLY,
)

# VRChat provider (Windows only, optional)
try:
    from providers import get_vrchat_provider
    VRCHAT_AVAILABLE = True
except ImportError:
    VRCHAT_AVAILABLE = False


# Cache configuration
CACHE_TTL_SECONDS = 30

# Global filter mode (set by command line argument)
_filter_mode = FILTER_ALL



@dataclass
class MediaCache:
    """Cache for media information."""
    media: Optional[MediaInfo]
    timestamp: datetime
    
    def is_valid(self) -> bool:
        """Check if cache is still valid (within TTL)."""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < CACHE_TTL_SECONDS
    
    def get_age_seconds(self) -> float:
        """Get cache age in seconds."""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()


# Global state
provider: Optional[MediaProvider] = None
vrchat_provider: Optional[MediaProvider] = None
connected_clients: set[WebSocket] = set()
media_cache: Optional[MediaCache] = None


def get_current_timestamp() -> str:
    """Get current timestamp in ISO 8601 format with timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat()


def update_cache(media: Optional[MediaInfo]) -> None:
    """Update the media cache."""
    global media_cache
    if media is not None:
        media_cache = MediaCache(
            media=media,
            timestamp=datetime.now(timezone.utc)
        )


def get_cached_response() -> tuple[Optional[dict], bool, str]:
    """
    Get media response, using cache if current fetch fails.
    
    Returns:
        tuple: (media_dict, is_cached, last_updated_timestamp)
    """
    global media_cache
    
    if media_cache is None:
        return None, False, get_current_timestamp()
    
    if media_cache.is_valid() and media_cache.media is not None:
        # Return cached data with "cached" status
        media_dict = media_cache.media.to_dict()
        media_dict["status"] = "cached"
        return media_dict, True, media_cache.timestamp.astimezone().isoformat()
    
    return None, False, get_current_timestamp()


async def broadcast_media_change(media_info: MediaInfo) -> None:
    """Broadcast media change to all connected WebSocket clients."""
    if not connected_clients:
        return
    
    # Update cache
    update_cache(media_info)
    
    system_info = get_system_info()
    message = json.dumps({
        "type": "media_update",
        "system": system_info,
        "media": media_info.to_dict() if media_info else None,
        "last_updated": get_current_timestamp(),
        "cached": False
    }, ensure_ascii=False)
    
    # Send to all clients
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)
    
    # Remove disconnected clients
    connected_clients.difference_update(disconnected)


def on_media_change(media_info: MediaInfo) -> None:
    """Handle media change events."""
    # Schedule the broadcast in the event loop
    asyncio.create_task(broadcast_media_change(media_info))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global provider, vrchat_provider, _filter_mode
    
    # Startup - main provider
    try:
        provider = get_provider(filter_mode=_filter_mode)
        provider.set_on_change_callback(on_media_change)
        await provider.start_watching()
        filter_info = f" (filter: {_filter_mode})" if _filter_mode != FILTER_ALL else ""
        print(f"Media provider started: {provider.__class__.__name__}{filter_info}")
    except Exception as e:
        print(f"Warning: Could not initialize media provider: {e}")
        provider = None
    
    # Startup - VRChat provider (Windows only)
    if VRCHAT_AVAILABLE:
        try:
            vrchat_provider = get_vrchat_provider()
            await vrchat_provider.start_watching()
            print("VRChat provider started")
        except Exception as e:
            print(f"Warning: Could not initialize VRChat provider: {e}")
            vrchat_provider = None
    
    yield
    
    # Shutdown
    if provider:
        await provider.stop_watching()
    if vrchat_provider:
        await vrchat_provider.stop_watching()


# Create FastAPI app
app = FastAPI(
    title="Media Player API",
    description="Cross-platform API for detecting currently playing media",
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API status endpoint."""
    system_info = get_system_info()
    return {
        "status": "running",
        "service": "Media Player API",
        "version": "1.1.0",
        "system": system_info,
        "provider": provider.__class__.__name__ if provider else None,
        "cache_ttl_seconds": CACHE_TTL_SECONDS
    }


@app.get("/now-playing")
async def now_playing():
    """Get currently playing media information."""
    system_info = get_system_info()
    
    if provider is None:
        return JSONResponse(
            status_code=503,
            content={
                "system": system_info,
                "media": None,
                "last_updated": get_current_timestamp(),
                "cached": False,
                "error": "Media provider not available"
            }
        )
    
    try:
        media = await provider.get_current_media()
        
        if media is not None:
            # Fresh data - update cache and return
            update_cache(media)
            return {
                "system": system_info,
                "media": media.to_dict(),
                "last_updated": get_current_timestamp(),
                "cached": False
            }
        else:
            # No current media - try cache
            cached_media, is_cached, last_updated = get_cached_response()
            return {
                "system": system_info,
                "media": cached_media,
                "last_updated": last_updated,
                "cached": is_cached
            }
            
    except Exception as e:
        # Error occurred - try cache
        cached_media, is_cached, last_updated = get_cached_response()
        if is_cached:
            return {
                "system": system_info,
                "media": cached_media,
                "last_updated": last_updated,
                "cached": True
            }
        return JSONResponse(
            status_code=500,
            content={
                "system": system_info,
                "media": None,
                "last_updated": get_current_timestamp(),
                "cached": False,
                "error": str(e)
            }
        )


@app.get("/vrchat/now-playing")
async def vrchat_now_playing():
    """Get currently playing video in VRChat, with fallback to main media provider."""
    system_info = get_system_info()
    
    # Try VRChat provider first (Windows only)
    if VRCHAT_AVAILABLE and vrchat_provider is not None:
        try:
            media = await vrchat_provider.get_current_media()
            if media is not None:
                return {
                    "system": system_info,
                    "media": media.to_dict(),
                    "last_updated": get_current_timestamp(),
                    "source": "vrchat_log"
                }
        except Exception as e:
            print(f"VRChat provider error: {e}")
    
    # Fallback to main media provider
    if provider is not None:
        try:
            media = await provider.get_current_media()
            if media is not None:
                update_cache(media)
                return {
                    "system": system_info,
                    "media": media.to_dict(),
                    "last_updated": get_current_timestamp(),
                    "source": "fallback"
                }
            else:
                # Try cache
                cached_media, is_cached, last_updated = get_cached_response()
                return {
                    "system": system_info,
                    "media": cached_media,
                    "last_updated": last_updated,
                    "source": "fallback_cached" if is_cached else "fallback"
                }
        except Exception as e:
            print(f"Fallback provider error: {e}")
    
    # No providers available
    return {
        "system": system_info,
        "media": None,
        "last_updated": get_current_timestamp(),
        "source": "none"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time media updates."""
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        # Send current media info immediately
        system_info = get_system_info()
        media = await provider.get_current_media() if provider else None
        
        if media is not None:
            update_cache(media)
            media_dict = media.to_dict()
            is_cached = False
        else:
            media_dict, is_cached, _ = get_cached_response()
        
        await websocket.send_text(json.dumps({
            "type": "connected",
            "system": system_info,
            "media": media_dict,
            "last_updated": get_current_timestamp(),
            "cached": is_cached
        }, ensure_ascii=False))
        
        # Keep connection open
        while True:
            # Wait for messages (ping/pong for keepalive)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    
    parser = argparse.ArgumentParser(
        description="Media Player API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Filter modes:
  all          All media sources (default)
  no-browser   Exclude browsers (Chromium, Firefox, Chrome, etc.)
  apps-only    WayDroid and streaming apps only (same as no-browser)

Examples:
  python main.py                      # All sources
  python main.py --filter no-browser  # Exclude browsers
  python main.py --filter apps-only   # WayDroid and apps only
"""
    )
    parser.add_argument(
        "--filter", "-f",
        dest="filter_mode",
        choices=[FILTER_ALL, FILTER_NO_BROWSER, FILTER_APPS_ONLY],
        default=FILTER_ALL,
        help="Filter mode for media sources (default: all)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)"
    )
    
    args = parser.parse_args()
    _filter_mode = args.filter_mode
    
    if _filter_mode != FILTER_ALL:
        print(f"Filter mode: {_filter_mode}")
    
    uvicorn.run(app, host=args.host, port=args.port)
