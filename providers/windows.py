"""
Windows media provider using SMTC (System Media Transport Controls).
Uses winrt-python package for Windows Runtime API access.
Includes fallback to notification listener for Amazon Music.
"""
import asyncio
from typing import Optional

from .base import MediaProvider, MediaInfo, PlaybackStatus

# Windows-specific imports
try:
    import winrt.windows.media.control as media_control
    WINRT_AVAILABLE = True
except ImportError:
    WINRT_AVAILABLE = False

# Notification listener for Amazon Music fallback
try:
    from .notification_listener import get_notification_listener, NOTIFICATIONS_AVAILABLE
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    def get_notification_listener():
        return None


class WindowsMediaProvider(MediaProvider):
    """Media provider for Windows using SMTC with Amazon Music fallback."""
    
    # Apps that are known to have incomplete SMTC data
    FALLBACK_APPS = ["amazonmusic", "amazon.music", "amazonmobilellc"]
    
    def __init__(self):
        super().__init__()
        if not WINRT_AVAILABLE:
            raise ImportError("winrt packages are not available. Install them with: pip install winrt-Windows.Media.Control")
        self._session_manager = None
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        self._notification_listener = get_notification_listener() if NOTIFICATIONS_AVAILABLE else None
    
    async def _get_session_manager(self):
        """Get or create the session manager."""
        if self._session_manager is None:
            self._session_manager = await media_control.GlobalSystemMediaTransportControlsSessionManager.request_async()
        return self._session_manager
    
    def _convert_playback_status(self, status) -> PlaybackStatus:
        """Convert Windows playback status to our enum."""
        if status == media_control.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
            return PlaybackStatus.PLAYING
        elif status == media_control.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
            return PlaybackStatus.PAUSED
        elif status == media_control.GlobalSystemMediaTransportControlsSessionPlaybackStatus.STOPPED:
            return PlaybackStatus.STOPPED
        else:
            return PlaybackStatus.UNKNOWN
    
    def _is_fallback_app(self, source_app: str) -> bool:
        """Check if this app needs notification fallback."""
        app_lower = source_app.lower().replace(" ", "").replace("_", "")
        return any(fb in app_lower for fb in self.FALLBACK_APPS)
    
    async def _try_notification_fallback(self, source_app: str, status: PlaybackStatus) -> Optional[MediaInfo]:
        """Try to get media info from notification listener."""
        if not self._notification_listener:
            return None
        
        try:
            notif_info = await self._notification_listener.poll_notifications()
            if notif_info:
                return MediaInfo(
                    source_app=source_app,
                    title=notif_info.title,
                    artist=notif_info.artist,
                    album=notif_info.album,
                    status=status
                )
        except Exception as e:
            print(f"Error in notification fallback: {e}")
        
        return None
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media."""
        try:
            manager = await self._get_session_manager()
            session = manager.get_current_session()
            
            if session is None:
                return None
            
            # Get media properties
            media_properties = await session.try_get_media_properties_async()
            if media_properties is None:
                return None
            
            # Get playback info
            playback_info = session.get_playback_info()
            status = self._convert_playback_status(playback_info.playback_status)
            
            # Get source app name
            source_app = session.source_app_user_model_id or ""
            # Clean up the app name (remove path-like parts)
            if "\\" in source_app or "/" in source_app:
                source_app = source_app.split("\\")[-1].split("/")[-1]
            if source_app.endswith(".exe"):
                source_app = source_app[:-4]
            
            title = media_properties.title or ""
            artist = media_properties.artist or ""
            album = media_properties.album_title or ""
            
            # Check if SMTC data is incomplete for known problematic apps
            is_incomplete = not title and not artist
            needs_fallback = self._is_fallback_app(source_app) and is_incomplete
            
            if needs_fallback:
                # Try notification fallback for Amazon Music
                fallback_info = await self._try_notification_fallback(source_app, status)
                if fallback_info:
                    return fallback_info
            
            return MediaInfo(
                source_app=source_app,
                title=title,
                artist=artist,
                album=album,
                status=status
            )
            
        except Exception as e:
            print(f"Error getting current media: {e}")
            return None
    
    async def start_watching(self) -> None:
        """Start watching for media changes."""
        if self._watching:
            return
        
        self._watching = True
        self._watch_task = asyncio.create_task(self._watch_loop())
    
    async def stop_watching(self) -> None:
        """Stop watching for media changes."""
        self._watching = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
    
    async def _watch_loop(self) -> None:
        """Polling loop to detect media changes."""
        while self._watching:
            try:
                current = await self.get_current_media()
                
                # Check if media info changed
                if self._has_changed(current):
                    self._last_media_info = current
                    if current:
                        self._notify_change(current)
                
                await asyncio.sleep(1)  # Poll every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in watch loop: {e}")
                await asyncio.sleep(1)
    
    def _has_changed(self, current: Optional[MediaInfo]) -> bool:
        """Check if media info has changed."""
        if self._last_media_info is None and current is None:
            return False
        if self._last_media_info is None or current is None:
            return True
        
        return (
            self._last_media_info.title != current.title or
            self._last_media_info.artist != current.artist or
            self._last_media_info.status != current.status or
            self._last_media_info.source_app != current.source_app
        )
