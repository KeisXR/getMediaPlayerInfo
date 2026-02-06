"""
VRChat media provider.
Monitors VRChat log files to detect video URLs played in-game.
Tracks playback state based on video duration.
"""
import asyncio
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from .base import MediaProvider, MediaInfo, PlaybackStatus
from .video_metadata import get_video_metadata, extract_video_urls, VideoMetadata


@dataclass
class VideoEntry:
    """A video URL entry from VRChat logs."""
    url: str
    timestamp: datetime


@dataclass
class PlaybackState:
    """Current video playback state."""
    url: str
    metadata: Optional[VideoMetadata]
    start_time: datetime
    duration: Optional[int]  # Duration in seconds
    
    def is_playing(self) -> bool:
        """Check if video is still playing based on duration."""
        if self.duration is None:
            # No duration info, assume playing for 10 minutes max
            return datetime.now() - self.start_time < timedelta(minutes=10)
        
        # Add a small buffer (30 seconds) for loading time
        expected_end = self.start_time + timedelta(seconds=self.duration + 30)
        return datetime.now() < expected_end
    
    def get_status(self) -> PlaybackStatus:
        """Get playback status."""
        if self.is_playing():
            return PlaybackStatus.PLAYING
        return PlaybackStatus.STOPPED


def get_vrchat_log_directory() -> Path:
    """Get the VRChat log directory path."""
    # Windows: %LOCALAPPDATA%Low\VRChat\VRChat
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        # LOCALAPPDATA is C:\Users\xxx\AppData\Local
        # We need C:\Users\xxx\AppData\LocalLow
        local_low = Path(local_app_data).parent / "LocalLow"
        vrchat_dir = local_low / "VRChat" / "VRChat"
        if vrchat_dir.exists():
            return vrchat_dir
    
    # Fallback: try common path
    home = Path.home()
    vrchat_dir = home / "AppData" / "LocalLow" / "VRChat" / "VRChat"
    return vrchat_dir


def get_latest_log_file(log_dir: Path) -> Optional[Path]:
    """Get the most recent VRChat log file."""
    if not log_dir.exists():
        return None
    
    log_files = list(log_dir.glob("output_log_*.txt"))
    if not log_files:
        return None
    
    # Sort by modification time, newest first
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return log_files[0]


def is_vrchat_running() -> bool:
    """Check if VRChat process is running."""
    try:
        # Windows: use tasklist
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq VRChat.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "VRChat.exe" in result.stdout
    except Exception:
        return True  # Assume running if check fails


def parse_video_entries_from_log(log_path: Path, after_position: int = 0) -> tuple[List[VideoEntry], int]:
    """
    Parse video URLs from a VRChat log file.
    
    Returns:
        tuple: (list of VideoEntry, new file position)
    """
    entries = []
    
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(after_position)
            content = f.read()
            new_position = f.tell()
        
        # Look for video URL patterns in log
        # VRChat logs video loads like:
        # "Attempting to resolve URL 'https://youtu.be/xxxxx'"
        # "Attempting to load Url 'https://www.youtube.com/watch?v=xxxxx'"
        
        url_pattern = r"(?:Attempting to (?:resolve URL|load Url)|Video URL)[:\s]*['\"]?(https?://[^\s'\"<>]+)"
        
        for match in re.finditer(url_pattern, content, re.IGNORECASE):
            url = match.group(1).rstrip("'\"")
            # Only include video URLs (YouTube, Twitch, etc.)
            video_urls = extract_video_urls(url)
            for video_url in video_urls:
                entries.append(VideoEntry(
                    url=video_url,
                    timestamp=datetime.now()
                ))
        
        return entries, new_position
        
    except Exception as e:
        print(f"Error parsing VRChat log: {e}")
        return [], after_position


class VRChatMediaProvider(MediaProvider):
    """
    Media provider for VRChat.
    
    Monitors VRChat log files to detect videos being played in-game.
    Uses yt-dlp for duration and tracks playback state.
    """
    
    def __init__(self):
        super().__init__()
        self._log_dir = get_vrchat_log_directory()
        self._current_log_file: Optional[Path] = None
        self._log_position: int = 0
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        self._playback_state: Optional[PlaybackState] = None
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing video in VRChat."""
        # Check if VRChat is running
        if not is_vrchat_running():
            self._playback_state = None
            return None
        
        # Find the latest log file
        log_file = get_latest_log_file(self._log_dir)
        if not log_file:
            return None
        
        # Check if log file changed
        if log_file != self._current_log_file:
            self._current_log_file = log_file
            self._log_position = 0
            self._playback_state = None
        
        # Parse new entries from log
        entries, new_position = parse_video_entries_from_log(log_file, self._log_position)
        self._log_position = new_position
        
        # If new video detected, update playback state
        if entries:
            latest_entry = entries[-1]
            # Only fetch metadata if it's a new URL
            if self._playback_state is None or self._playback_state.url != latest_entry.url:
                metadata = await get_video_metadata(latest_entry.url, include_duration=True)
                self._playback_state = PlaybackState(
                    url=latest_entry.url,
                    metadata=metadata,
                    start_time=latest_entry.timestamp,
                    duration=metadata.duration if metadata else None
                )
        
        # Return current playback info
        if self._playback_state:
            status = self._playback_state.get_status()
            
            # If video has ended, return stopped status or None
            if status == PlaybackStatus.STOPPED:
                return MediaInfo(
                    source_app="VRChat",
                    title=self._playback_state.metadata.title if self._playback_state.metadata else self._playback_state.url,
                    artist=self._playback_state.metadata.author if self._playback_state.metadata else "",
                    album="",
                    status=PlaybackStatus.STOPPED
                )
            
            # Video is still playing
            if self._playback_state.metadata:
                return MediaInfo(
                    source_app="VRChat",
                    title=self._playback_state.metadata.title,
                    artist=self._playback_state.metadata.author,
                    album="",
                    status=PlaybackStatus.PLAYING
                )
            else:
                # Fallback: return URL as title
                return MediaInfo(
                    source_app="VRChat",
                    title=self._playback_state.url,
                    artist="",
                    album="",
                    status=PlaybackStatus.PLAYING
                )
        
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
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in VRChat watch loop: {e}")
                await asyncio.sleep(2)
    
    def _has_changed(self, current: Optional[MediaInfo]) -> bool:
        """Check if media info has changed."""
        if self._last_media_info is None and current is None:
            return False
        if self._last_media_info is None or current is None:
            return True
        
        return (
            self._last_media_info.title != current.title or
            self._last_media_info.artist != current.artist or
            self._last_media_info.status != current.status
        )
