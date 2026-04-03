"""
Base classes for media providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class PlaybackStatus(str, Enum):
    """Media playback status."""
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class MediaInfo:
    """Information about currently playing media."""
    source_app: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    status: PlaybackStatus = PlaybackStatus.UNKNOWN
    position_ms: Optional[int] = None  # Current playback position in milliseconds
    duration_ms: Optional[int] = None  # Total duration in milliseconds
    # Raw thumbnail bytes – only used by the local GUI, never exposed via the public API
    thumbnail_data: Optional[bytes] = field(default=None, repr=False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary.  thumbnail_data is intentionally excluded."""
        return {
            "source_app": self.source_app,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "status": self.status.value,
            "position_ms": self.position_ms,
            "duration_ms": self.duration_ms,
            "thumbnail": None  # Always return None – never expose artwork via the API
        }
    
    def is_playing(self) -> bool:
        """Check if media is currently playing."""
        return self.status == PlaybackStatus.PLAYING
    
    @staticmethod
    def format_time(ms: int) -> str:
        """Format milliseconds to mm:ss string."""
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"


class MediaProvider(ABC):
    """Abstract base class for media providers."""
    
    def __init__(self):
        self._on_change_callback: Optional[Callable[[MediaInfo], None]] = None
    
    @abstractmethod
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media."""
        pass
    
    @abstractmethod
    async def start_watching(self) -> None:
        """Start watching for media changes."""
        pass
    
    @abstractmethod
    async def stop_watching(self) -> None:
        """Stop watching for media changes."""
        pass
    
    def set_on_change_callback(self, callback: Callable[[MediaInfo], None]) -> None:
        """Set callback for media change events."""
        self._on_change_callback = callback
    
    def _notify_change(self, media_info: MediaInfo) -> None:
        """Notify about media change."""
        if self._on_change_callback:
            self._on_change_callback(media_info)
