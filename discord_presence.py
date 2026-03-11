"""
Discord Rich Presence for Media Player API

Displays currently playing media information in Discord's activity status.
Includes elapsed/remaining time display (seek bar) when position/duration are available.
"""
import asyncio
import argparse
import signal
import sys
import time
from typing import Optional

try:
    from pypresence import AioPresence
    from pypresence.exceptions import DiscordNotFound, PipeClosed
except ImportError:
    print("Error: pypresence is not installed. Install it with: pip install pypresence")
    sys.exit(1)

from providers import get_provider, MediaProvider
from providers.base import MediaInfo, PlaybackStatus


class DiscordMediaPresence:
    """Discord Rich Presence client for media information."""
    
    # Mapping of source apps to Discord asset keys (optional, for custom icons)
    APP_ICONS = {
        "spotify": "spotify",
        "youtube": "youtube",
        "vlc": "vlc",
        "firefox": "firefox",
        "chrome": "chrome",
        "plasma-browser-integration": "browser",
    }
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.rpc: Optional[AioPresence] = None
        self.provider: Optional[MediaProvider] = None
        self.running = False
        self._last_media: Optional[MediaInfo] = None
    
    async def connect(self) -> bool:
        """Connect to Discord RPC."""
        try:
            self.rpc = AioPresence(self.client_id)
            await self.rpc.connect()
            print("✓ Connected to Discord")
            return True
        except DiscordNotFound:
            print("✗ Discord not found. Make sure Discord desktop app is running.")
            return False
        except Exception as e:
            print(f"✗ Failed to connect to Discord: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Discord RPC."""
        if self.rpc:
            try:
                await self.rpc.clear()
                await self.rpc.close()
            except Exception:
                pass
            self.rpc = None
            print("Disconnected from Discord")
    
    def _get_status_text(self, status: PlaybackStatus) -> str:
        """Get display text for playback status."""
        if status == PlaybackStatus.PLAYING:
            return "▶ Playing"
        elif status == PlaybackStatus.PAUSED:
            return "⏸ Paused"
        elif status == PlaybackStatus.STOPPED:
            return "⏹ Stopped"
        return ""
    
    def _get_large_image_key(self, source_app: str) -> str:
        """Get Discord asset key for source app icon."""
        app_lower = source_app.lower()
        return self.APP_ICONS.get(app_lower, "music")
    
    def _build_state_text(self, media: MediaInfo) -> Optional[str]:
        """Build state text with artist/album and time info."""
        parts = []
        if media.artist:
            parts.append(media.artist)
        if media.album:
            parts.append(media.album)
        
        state = " - ".join(parts) if parts else None
        
        # Append time info to state if available
        if media.position_ms is not None and media.duration_ms is not None:
            time_str = f"{MediaInfo.format_time(media.position_ms)} / {MediaInfo.format_time(media.duration_ms)}"
            if state:
                state = f"{state}  [{time_str}]"
            else:
                state = time_str
        
        return state
    
    def _calculate_timestamps(self, media: MediaInfo) -> tuple[Optional[int], Optional[int]]:
        """
        Calculate Discord timestamps for elapsed/remaining time display.
        
        Returns:
            tuple: (start_epoch, end_epoch) or (None, None) if not available
        """
        if media.status != PlaybackStatus.PLAYING:
            return None, None
        
        if media.position_ms is None or media.duration_ms is None:
            return None, None
        
        if media.duration_ms <= 0:
            return None, None
        
        now = time.time()
        # Calculate when the song "started" based on current position
        start_epoch = int(now - (media.position_ms / 1000))
        # Calculate when the song will "end"
        end_epoch = int(start_epoch + (media.duration_ms / 1000))
        
        return start_epoch, end_epoch
    
    async def update_presence(self, media: Optional[MediaInfo]) -> None:
        """Update Discord presence with media info."""
        if not self.rpc:
            return
        
        try:
            if media is None or not media.title:
                # No media playing - clear presence
                await self.rpc.clear()
                return
            
            # Build presence data
            details = media.title
            state = self._build_state_text(media)
            
            # Large image: app icon, small image: playback status
            large_image = self._get_large_image_key(media.source_app)
            large_text = f"via {media.source_app}"
            
            small_image = "playing" if media.status == PlaybackStatus.PLAYING else "paused"
            small_text = self._get_status_text(media.status)
            
            # Calculate timestamps for seek bar
            start_epoch, end_epoch = self._calculate_timestamps(media)
            
            # Build update kwargs
            kwargs = {
                "details": details[:128] if details else None,
                "state": state[:128] if state else None,
                "large_image": large_image,
                "large_text": large_text,
                "small_image": small_image,
                "small_text": small_text,
            }
            
            # Add timestamps only when playing with valid time info
            if start_epoch is not None and end_epoch is not None:
                kwargs["start"] = start_epoch
                kwargs["end"] = end_epoch
            
            await self.rpc.update(**kwargs)
            
        except PipeClosed:
            print("Discord connection lost. Attempting to reconnect...")
            await self.connect()
        except Exception as e:
            print(f"Error updating presence: {e}")
    
    def _media_changed(self, current: Optional[MediaInfo]) -> bool:
        """Check if media has changed (ignores position changes for efficiency)."""
        if self._last_media is None and current is None:
            return False
        if self._last_media is None or current is None:
            return True
        
        return (
            self._last_media.title != current.title or
            self._last_media.artist != current.artist or
            self._last_media.status != current.status or
            self._last_media.source_app != current.source_app or
            self._last_media.duration_ms != current.duration_ms
        )
    
    async def run(self) -> None:
        """Main loop to watch media and update Discord presence."""
        # Initialize provider
        try:
            self.provider = get_provider()
            print(f"✓ Media provider: {self.provider.__class__.__name__}")
        except Exception as e:
            print(f"✗ Failed to initialize media provider: {e}")
            return
        
        # Connect to Discord
        if not await self.connect():
            return
        
        self.running = True
        print("Watching for media changes... (Ctrl+C to stop)")
        
        try:
            update_counter = 0
            while self.running:
                try:
                    media = await self.provider.get_current_media()
                    
                    # Update on media change or periodically (every 15s) for time sync
                    media_changed = self._media_changed(media)
                    update_counter += 1
                    periodic_update = (update_counter >= 8)  # ~16 seconds at 2s interval
                    
                    if media_changed or periodic_update:
                        if media_changed:
                            self._last_media = media
                        if periodic_update:
                            update_counter = 0
                        
                        await self.update_presence(media)
                        
                        if media and media_changed:
                            status_icon = "▶" if media.status == PlaybackStatus.PLAYING else "⏸"
                            time_info = ""
                            if media.position_ms is not None and media.duration_ms is not None:
                                time_info = f" [{MediaInfo.format_time(media.position_ms)} / {MediaInfo.format_time(media.duration_ms)}]"
                            print(f"{status_icon} {media.title} - {media.artist} ({media.source_app}){time_info}")
                        elif not media and media_changed:
                            print("No media playing")
                    
                    await asyncio.sleep(2)  # Poll every 2 seconds
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    await asyncio.sleep(5)
                    
        finally:
            await self.disconnect()
    
    def stop(self) -> None:
        """Stop the main loop."""
        self.running = False


async def main():
    parser = argparse.ArgumentParser(
        description="Display currently playing media in Discord Rich Presence"
    )
    parser.add_argument(
        "--client-id",
        required=True,
        help="Discord Application Client ID"
    )
    args = parser.parse_args()
    
    presence = DiscordMediaPresence(args.client_id)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nStopping...")
        presence.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await presence.run()


if __name__ == "__main__":
    asyncio.run(main())
