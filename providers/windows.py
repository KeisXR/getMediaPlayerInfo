"""
Windows media provider using SMTC (System Media Transport Controls).
Uses winrt-python package for Windows Runtime API access.
Includes fallback to notification listener for Amazon Music.
"""
import asyncio
import logging
from typing import Optional, Any

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


logger = logging.getLogger(__name__)


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

    @staticmethod
    def _status_priority(status: PlaybackStatus) -> int:
        """Priority for selecting the best session."""
        if status == PlaybackStatus.PLAYING:
            return 3
        if status == PlaybackStatus.PAUSED:
            return 2
        if status == PlaybackStatus.STOPPED:
            return 1
        return 0

    @staticmethod
    def _metadata_priority(title: str, artist: str, album: str) -> int:
        """Priority for selecting richer metadata."""
        if title:
            return 3
        if artist:
            return 2
        if album:
            return 1
        return 0

    @staticmethod
    def _normalize_source_app(source_app: str) -> str:
        """Normalize app name from source_app_user_model_id."""
        normalized = source_app or ""
        if "\\" in normalized or "/" in normalized:
            normalized = normalized.split("\\")[-1].split("/")[-1]
        if normalized.endswith(".exe"):
            normalized = normalized[:-4]
        return normalized

    @staticmethod
    def _coalesce_title(title: str, artist: str, album: str, source_app: str) -> str:
        """Ensure title is not empty when at least some station/media info exists."""
        if title:
            return title
        return artist or album or source_app

    async def _select_best_session_data(self, manager: Any) -> Optional[dict]:
        """
        Select the best session from all available sessions.
        Prefers playing sessions and richer metadata over current-session-only selection.
        """
        try:
            current = manager.get_current_session()
        except Exception:
            current = None

        sessions = []
        if current is not None:
            sessions.append(current)

        try:
            all_sessions = manager.get_sessions()
            if all_sessions:
                for s in all_sessions:
                    if s is not None and all(existing is not s for existing in sessions):
                        sessions.append(s)
        except Exception:
            pass

        best: Optional[dict] = None
        best_score = (-1, -1, -1)

        for session in sessions:
            try:
                media_properties = await session.try_get_media_properties_async()
                if media_properties is None:
                    continue

                playback_info = session.get_playback_info()
                status = self._convert_playback_status(playback_info.playback_status)

                source_app = self._normalize_source_app(session.source_app_user_model_id or "")
                title = (media_properties.title or "").strip()
                artist = (media_properties.artist or "").strip()
                album = (media_properties.album_title or "").strip()

                score = (
                    self._status_priority(status),
                    self._metadata_priority(title, artist, album),
                    1 if session is current else 0,
                )

                if score > best_score:
                    best_score = score
                    best = {
                        "session": session,
                        "status": status,
                        "source_app": source_app,
                        "title": title,
                        "artist": artist,
                        "album": album,
                    }
            except Exception as e:
                logger.debug("Error reading session metadata: %s", e)

        return best
    
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
            logger.debug("Error in notification fallback: %s", e)
        
        return None
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media."""
        try:
            manager = await self._get_session_manager()
            selected = await self._select_best_session_data(manager)
            if selected is None:
                return None

            session = selected["session"]
            status = selected["status"]
            source_app = selected["source_app"]
            title = selected["title"]
            artist = selected["artist"]
            album = selected["album"]
            
            # Check if SMTC data is incomplete for known problematic apps
            missing_primary_fields = not title and not artist
            missing_all_fields = missing_primary_fields and not album
            needs_fallback = self._is_fallback_app(source_app) and missing_primary_fields
            
            if needs_fallback:
                # Try notification fallback for Amazon Music
                fallback_info = await self._try_notification_fallback(source_app, status)
                if fallback_info:
                    return fallback_info

            # If we have absolutely no media fields, treat as no media.
            if missing_all_fields:
                return None

            title = self._coalesce_title(title, artist, album, source_app)
            
            # Get timeline properties for position/duration
            position_ms = None
            duration_ms = None
            try:
                timeline = session.get_timeline_properties()
                if timeline:
                    # position and end_time are datetime.timedelta objects
                    pos = timeline.position
                    end = timeline.end_time
                    if pos is not None:
                        position_ms = int(pos.total_seconds() * 1000)
                        if position_ms < 0:
                            position_ms = None
                    if end is not None:
                        duration_ms = int(end.total_seconds() * 1000)
                        if duration_ms <= 0:
                            duration_ms = None
            except Exception:
                pass
            
            return MediaInfo(
                source_app=source_app,
                title=title,
                artist=artist,
                album=album,
                status=status,
                position_ms=position_ms,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            logger.debug("Error getting current media: %s", e)
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
                logger.debug("Error in watch loop: %s", e)
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
