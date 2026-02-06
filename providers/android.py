"""
Android media provider using dumpsys media_session.
Requires root access (KernelSU, Magisk, etc.)
"""
import asyncio
import re
import subprocess
from typing import Optional

from .base import MediaProvider, MediaInfo, PlaybackStatus


class AndroidMediaProvider(MediaProvider):
    """Media provider for Android using dumpsys media_session."""
    
    # PlaybackState constants from Android
    # https://developer.android.com/reference/android/media/session/PlaybackState
    PLAYBACK_STATE_PLAYING = 3
    PLAYBACK_STATE_PAUSED = 2
    PLAYBACK_STATE_STOPPED = 1
    
    def __init__(self):
        super().__init__()
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        self._su_command = self._detect_su_command()
    
    def _detect_su_command(self) -> list[str]:
        """Detect which su command to use."""
        # Try different su implementations
        for su_cmd in [["su", "-c"], ["su", "0"], ["/system/bin/su", "-c"]]:
            try:
                result = subprocess.run(
                    su_cmd + ["echo", "test"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return su_cmd
            except Exception:
                continue
        
        # Fallback - might work in Termux with root
        return ["su", "-c"]
    
    def _run_as_root(self, command: str) -> str:
        """Run a command as root."""
        try:
            # Combine su command with the actual command
            full_cmd = self._su_command + [command]
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            print("Command timed out")
            return ""
        except Exception as e:
            print(f"Error running command: {e}")
            return ""
    
    def _parse_media_session(self, output: str) -> Optional[MediaInfo]:
        """Parse dumpsys media_session output."""
        if not output:
            return None
        
        # Find the active session
        # Look for "global priority session" or first Media session
        active_package = None
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
        # Split by "Media session" and find the right one
        sections = re.split(r'Media session (\S+)', output)
        session_content = ""
        
        for i, section in enumerate(sections):
            if active_package in section and i + 1 < len(sections):
                session_content = sections[i + 1]
                break
        
        if not session_content:
            # Use the first large section after finding the package
            idx = output.find(f"Media session {active_package}")
            if idx != -1:
                session_content = output[idx:idx + 2000]
        
        # Parse metadata
        title = self._extract_metadata(session_content, "TITLE")
        artist = self._extract_metadata(session_content, "ARTIST")
        album = self._extract_metadata(session_content, "ALBUM")
        
        # Parse playback state
        status = PlaybackStatus.UNKNOWN
        state_match = re.search(r'state=PlaybackState\s*\{[^}]*state=(\d+)', session_content)
        if state_match:
            state_code = int(state_match.group(1))
            if state_code == self.PLAYBACK_STATE_PLAYING:
                status = PlaybackStatus.PLAYING
            elif state_code == self.PLAYBACK_STATE_PAUSED:
                status = PlaybackStatus.PAUSED
            elif state_code == self.PLAYBACK_STATE_STOPPED:
                status = PlaybackStatus.STOPPED
        
        # Clean up package name for display
        app_name = active_package.split(".")[-1].replace("_", " ").title()
        
        # If no metadata found, try description field
        if not title:
            desc_match = re.search(r'description=([^,\n]+)', session_content)
            if desc_match:
                desc = desc_match.group(1).strip()
                if " - " in desc:
                    parts = desc.split(" - ", 1)
                    title = parts[0].strip()
                    if not artist and len(parts) > 1:
                        artist = parts[1].strip()
        
        if not title and not artist:
            return None
        
        return MediaInfo(
            source_app=app_name,
            title=title or "",
            artist=artist or "",
            album=album or "",
            status=status
        )
    
    def _extract_metadata(self, content: str, key: str) -> str:
        """Extract metadata value from dumpsys output."""
        # Pattern: android.media.metadata.KEY: value
        pattern = rf'android\.media\.metadata\.{key}:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media."""
        try:
            # Run dumpsys command
            output = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._run_as_root("dumpsys media_session")
            )
            
            return self._parse_media_session(output)
            
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
                
                await asyncio.sleep(2)  # Poll every 2 seconds (less frequent due to su overhead)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in watch loop: {e}")
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
