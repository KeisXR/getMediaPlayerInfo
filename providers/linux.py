"""
Linux media provider using MPRIS (D-Bus).
"""
import asyncio
import base64
import os
from typing import Optional, List, Set
from urllib.parse import urlparse, unquote

from .base import MediaProvider, MediaInfo, PlaybackStatus

# Linux-specific imports
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False


# Known browser MPRIS player names (case-insensitive patterns)
BROWSER_PLAYERS = [
    "chromium",
    "chrome",
    "firefox",
    "brave",
    "edge",
    "opera",
    "vivaldi",
    "librewolf",
    "waterfox",
    "plasma-browser-integration",
]


class LinuxMediaProvider(MediaProvider):
    """Media provider for Linux using MPRIS over D-Bus."""
    
    MPRIS_PREFIX = "org.mpris.MediaPlayer2."
    MPRIS_PATH = "/org/mpris/MediaPlayer2"
    MPRIS_INTERFACE = "org.mpris.MediaPlayer2.Player"
    PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
    
    def __init__(self, excluded_players: Optional[Set[str]] = None):
        """
        Initialize the Linux media provider.
        
        Args:
            excluded_players: Set of player name patterns to exclude (case-insensitive)
        """
        super().__init__()
        if not DBUS_AVAILABLE:
            raise ImportError("dbus-python is not available. Install it with: pip install dbus-python")
        
        # Initialize D-Bus main loop
        DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SessionBus()
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        self._excluded_players = excluded_players or set()
    
    def _is_excluded(self, player_name: str) -> bool:
        """Check if a player should be excluded based on patterns."""
        player_lower = player_name.lower()
        for pattern in self._excluded_players:
            if pattern.lower() in player_lower:
                return True
        return False
    
    def _get_mpris_players(self) -> list[str]:
        """Get list of available MPRIS media players."""
        try:
            bus_object = self._bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            bus_interface = dbus.Interface(bus_object, "org.freedesktop.DBus")
            names = bus_interface.ListNames()
            players = [name for name in names if name.startswith(self.MPRIS_PREFIX)]
            
            # Filter out excluded players
            if self._excluded_players:
                players = [p for p in players if not self._is_excluded(p)]
            
            # Prioritize Plasma Browser Integration (if not excluded)
            # This service usually provides better metadata than the browser itself
            players.sort(key=lambda x: 0 if "plasma-browser-integration" in x else 1)
            
            return players
        except Exception as e:
            print(f"Error listing MPRIS players: {e}")
            return []
    
    def _get_player_properties(self, player_name: str) -> Optional[dict]:
        """Get properties from a specific player."""
        try:
            player_object = self._bus.get_object(player_name, self.MPRIS_PATH)
            properties_interface = dbus.Interface(player_object, self.PROPERTIES_INTERFACE)
            
            # Get all player properties
            properties = properties_interface.GetAll(self.MPRIS_INTERFACE)
            return dict(properties)
        except Exception as e:
            print(f"Error getting properties for {player_name}: {e}")
            return None
    
    def _convert_playback_status(self, status: str) -> PlaybackStatus:
        """Convert MPRIS playback status to our enum."""
        status = status.lower()
        if status == "playing":
            return PlaybackStatus.PLAYING
        elif status == "paused":
            return PlaybackStatus.PAUSED
        elif status == "stopped":
            return PlaybackStatus.STOPPED
        else:
            return PlaybackStatus.UNKNOWN
    
    def _extract_app_name(self, player_name: str) -> str:
        """Extract app name from MPRIS player name."""
        # Remove the MPRIS prefix
        name = player_name.replace(self.MPRIS_PREFIX, "")
        # Remove instance number if present (e.g., "spotify.instance123")
        if ".instance" in name:
            name = name.split(".instance")[0]
        return name.capitalize()
    

    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """Get information about currently playing media."""
        try:
            players = self._get_mpris_players()
            
            if not players:
                return None
            
            # Find a playing player, or use the first one
            active_player = None
            active_properties = None
            
            for player in players:
                properties = self._get_player_properties(player)
                if properties is None:
                    continue
                
                status = str(properties.get("PlaybackStatus", ""))
                if status.lower() == "playing":
                    active_player = player
                    active_properties = properties
                    break
                
                # Keep track of first valid player as fallback
                if active_player is None:
                    active_player = player
                    active_properties = properties
            
            if active_player is None or active_properties is None:
                return None
            
            # Extract metadata
            metadata = active_properties.get("Metadata", {})
            
            # Get title, artist, album
            title = str(metadata.get("xesam:title", "")) if metadata.get("xesam:title") else ""
            
            artists = metadata.get("xesam:artist", [])
            artist = str(artists[0]) if artists else ""
            
            album = str(metadata.get("xesam:album", "")) if metadata.get("xesam:album") else ""
            
            # Get playback status
            status = self._convert_playback_status(str(active_properties.get("PlaybackStatus", "")))
            
            # thumbnail extraction removed
            
            return MediaInfo(
                source_app=self._extract_app_name(active_player),
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


class HybridLinuxMediaProvider(MediaProvider):
    """
    Hybrid media provider that combines MPRIS and WayDroid sources.
    Prioritizes playing media, with WayDroid taking precedence when both are playing.
    """
    
    def __init__(self, excluded_players: Optional[Set[str]] = None):
        """
        Initialize the hybrid media provider.
        
        Args:
            excluded_players: Set of player name patterns to exclude (case-insensitive)
        """
        super().__init__()
        self._mpris = LinuxMediaProvider(excluded_players=excluded_players)
        self._waydroid: Optional[MediaProvider] = None
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_media_info: Optional[MediaInfo] = None
        
        # Try to initialize WayDroid provider
        try:
            from .waydroid import WayDroidMediaProvider
            waydroid = WayDroidMediaProvider()
            if waydroid.is_available():
                self._waydroid = waydroid
                print("HybridLinuxMediaProvider: WayDroid available")
            else:
                print("HybridLinuxMediaProvider: WayDroid not running")
        except Exception as e:
            print(f"HybridLinuxMediaProvider: WayDroid not available ({e})")
    
    async def get_current_media(self) -> Optional[MediaInfo]:
        """
        Get information about currently playing media.
        Priority: Playing > Paused > Stopped
        When same status, WayDroid takes precedence.
        """
        mpris_media = await self._mpris.get_current_media()
        waydroid_media = None
        
        if self._waydroid:
            waydroid_media = await self._waydroid.get_current_media()
        
        # If only one source has media, return that
        if not mpris_media and not waydroid_media:
            return None
        if not mpris_media:
            return waydroid_media
        if not waydroid_media:
            return mpris_media
        
        # Both have media - prioritize by playback status
        # Playing > Paused > Stopped > Unknown
        def status_priority(status: PlaybackStatus) -> int:
            if status == PlaybackStatus.PLAYING:
                return 3
            elif status == PlaybackStatus.PAUSED:
                return 2
            elif status == PlaybackStatus.STOPPED:
                return 1
            return 0
        
        mpris_priority = status_priority(mpris_media.status)
        waydroid_priority = status_priority(waydroid_media.status)
        
        # If same priority, prefer WayDroid
        if waydroid_priority >= mpris_priority:
            return waydroid_media
        return mpris_media
    
    async def start_watching(self) -> None:
        """Start watching for media changes on both sources."""
        if self._watching:
            return
        
        self._watching = True
        await self._mpris.start_watching()
        if self._waydroid:
            await self._waydroid.start_watching()
        
        # Forward change events
        self._mpris.set_on_change_callback(self._on_source_change)
        if self._waydroid:
            self._waydroid.set_on_change_callback(self._on_source_change)
        
        # Also start our own polling for hybrid logic
        self._watch_task = asyncio.create_task(self._watch_loop())
    
    async def stop_watching(self) -> None:
        """Stop watching for media changes."""
        self._watching = False
        await self._mpris.stop_watching()
        if self._waydroid:
            await self._waydroid.stop_watching()
        
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
    
    def _on_source_change(self, media_info: MediaInfo) -> None:
        """Handle change from either source - trigger a re-evaluation."""
        # We'll let the watch loop handle the actual notification
        # to ensure proper priority logic
        pass
    
    async def _watch_loop(self) -> None:
        """Polling loop to detect media changes with priority logic."""
        while self._watching:
            try:
                current = await self.get_current_media()
                
                if self._has_changed(current):
                    self._last_media_info = current
                    if current:
                        self._notify_change(current)
                
                await asyncio.sleep(1.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in hybrid watch loop: {e}")
                await asyncio.sleep(1.5)
    
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
