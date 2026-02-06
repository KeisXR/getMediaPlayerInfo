"""
WayDroid media provider using waydroid shell + dumpsys media_session.
For Linux systems running WayDroid (Android container).
"""
import asyncio
import re
import shutil
import subprocess
from typing import Optional

from .base import MediaProvider, MediaInfo, PlaybackStatus


def parse_dumpsys_media_session(output: str) -> Optional[MediaInfo]:
    """
    Parse dumpsys media_session output.
    Shared between AndroidMediaProvider and WayDroidMediaProvider.
    """
    if not output:
        return None
    
    # PlaybackState constants from Android
    PLAYBACK_STATE_PLAYING = 3
    PLAYBACK_STATE_PAUSED = 2
    PLAYBACK_STATE_STOPPED = 1
    
    # Find the active session
    # Look for "Media button session" or "global priority session"
    active_package = None
    
    # Try "Media button session is" first (more reliable for actual media playback)
    button_match = re.search(r'Media button session is (\S+)', output)
    if button_match:
        active_package = button_match.group(1)
    
    if not active_package:
        priority_match = re.search(r'global priority session is (\S+)', output)
        if priority_match:
            active_package = priority_match.group(1)
    
    if not active_package:
        # Try to find any active session
        session_match = re.search(r'Media session (\S+)', output)
        if session_match:
            active_package = session_match.group(1)
    
    if not active_package:
        return None
    
    # Find the section for this session
    # active_package is like "com.amazon.mp3/MediaSessionController (userId=0)"
    # We need to find where this appears and get content after it
    idx = output.find(active_package)
    if idx == -1:
        # Try just the package part before the slash
        package_part = active_package.split("/")[0]
        idx = output.find(package_part)
    
    if idx != -1:
        session_content = output[idx:idx + 3000]
    else:
        session_content = output  # Use entire output as fallback
    
    # Parse metadata
    def extract_metadata(content: str, key: str) -> str:
        """Extract metadata value from dumpsys output."""
        pattern = rf'android\.media\.metadata\.{key}:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    
    title = extract_metadata(session_content, "TITLE")
    artist = extract_metadata(session_content, "ARTIST")
    album = extract_metadata(session_content, "ALBUM")
    
    # Parse playback state
    status = PlaybackStatus.UNKNOWN
    state_match = re.search(r'state=PlaybackState\s*\{[^}]*state=(\d+)', session_content)
    if state_match:
        state_code = int(state_match.group(1))
        if state_code == PLAYBACK_STATE_PLAYING:
            status = PlaybackStatus.PLAYING
        elif state_code == PLAYBACK_STATE_PAUSED:
            status = PlaybackStatus.PAUSED
        elif state_code == PLAYBACK_STATE_STOPPED:
            status = PlaybackStatus.STOPPED
    
    # Clean up package name for display
    # Extract package name from "com.amazon.mp3/MediaSessionController"
    package_part = active_package.split("/")[0]
    app_name = package_part.split(".")[-1].replace("_", " ").title()
    
    # Special case for known packages
    package_names = {
        "com.amazon.mp3": "Amazon Music",
        "com.spotify.music": "Spotify",
        "com.google.android.youtube.music": "YouTube Music",
        "com.google.android.youtube": "YouTube",
    }
    if package_part in package_names:
        app_name = package_names[package_part]
    
    # If no metadata found, try description field
    # Format: "description=title, artist, album" (comma separated)
    if not title:
        desc_match = re.search(r'description=([^\n]+)', session_content)
        if desc_match:
            desc = desc_match.group(1).strip()
            # Try comma-separated format first: "title, artist, album"
            parts = [p.strip() for p in desc.split(',')]
            if len(parts) >= 1 and parts[0]:
                title = parts[0]
            if len(parts) >= 2 and parts[1] and not artist:
                artist = parts[1]
            if len(parts) >= 3 and parts[2] and not album:
                album = parts[2]
            # Fallback: try "title - artist" format
            if not artist and " - " in title:
                t_parts = title.split(" - ", 1)
                title = t_parts[0].strip()
                artist = t_parts[1].strip()
    
    if not title and not artist:
        return None
    
    return MediaInfo(
        source_app=f"{app_name} (WayDroid)",
        title=title or "",
        artist=artist or "",
        album=album or "",
        status=status
    )


class WayDroidMediaProvider(MediaProvider):
    """Media provider for WayDroid using waydroid shell + dumpsys."""
    
    def __init__(self):
        super().__init__()
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        self._waydroid_available = self._check_waydroid()
    
    def _check_waydroid(self) -> bool:
        """Check if waydroid is available and running."""
        if not shutil.which("waydroid"):
            return False
        
        try:
            # Check if waydroid session is running
            result = subprocess.run(
                ["waydroid", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "RUNNING" in result.stdout
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if WayDroid is available."""
        return self._waydroid_available
    
    def _run_dumpsys(self) -> str:
        """Run dumpsys media_session via waydroid shell."""
        try:
            result = subprocess.run(
                ["sudo", "waydroid", "shell", "dumpsys", "media_session"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            print("WayDroid command timed out")
            return ""
        except Exception as e:
            print(f"Error running waydroid command: {e}")
            return ""
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media in WayDroid."""
        if not self._waydroid_available:
            # Re-check availability (session might have started)
            self._waydroid_available = self._check_waydroid()
            if not self._waydroid_available:
                return None
        
        try:
            output = await asyncio.get_event_loop().run_in_executor(
                None, self._run_dumpsys
            )
            return parse_dumpsys_media_session(output)
        except Exception as e:
            print(f"Error getting WayDroid media: {e}")
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
                
                if self._has_changed(current):
                    self._last_media_info = current
                    if current:
                        self._notify_change(current)
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in WayDroid watch loop: {e}")
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
            self._last_media_info.status != current.status or
            self._last_media_info.source_app != current.source_app
        )
