"""
Media providers package.
"""
import platform
import os
from typing import Optional, Set
from .base import MediaProvider, MediaInfo


def _is_android() -> bool:
    """Check if running on Android (Termux)."""
    # Check for Termux-specific environment
    if os.environ.get("TERMUX_VERSION"):
        return True
    # Check for Android-specific paths
    if os.path.exists("/system/build.prop"):
        return True
    # Check PREFIX (Termux sets this)
    if "/com.termux" in os.environ.get("PREFIX", ""):
        return True
    return False


# Filter mode constants
FILTER_ALL = "all"              # All sources (default)
FILTER_NO_BROWSER = "no-browser"  # Exclude browsers
FILTER_APPS_ONLY = "apps-only"  # WayDroid and streaming apps only (same as no-browser for now)


def get_provider(filter_mode: str = FILTER_ALL) -> MediaProvider:
    """
    Get the appropriate media provider for the current platform.
    
    Args:
        filter_mode: Filter mode for sources
            - "all": All sources (default)
            - "no-browser": Exclude browser players (Chromium, Firefox, Chrome, etc.)
            - "apps-only": WayDroid and streaming apps only (excludes browsers)
    """
    system = platform.system()
    
    # Get excluded players based on filter mode
    excluded_players: Optional[Set[str]] = None
    if filter_mode in (FILTER_NO_BROWSER, FILTER_APPS_ONLY):
        from .linux import BROWSER_PLAYERS
        excluded_players = set(BROWSER_PLAYERS)
    
    if system == "Linux" and _is_android():
        from .android import AndroidMediaProvider
        return AndroidMediaProvider()
    elif system == "Windows":
        from .windows import WindowsMediaProvider
        return WindowsMediaProvider()
    elif system == "Linux":
        # Use HybridLinuxMediaProvider which combines MPRIS + WayDroid
        from .linux import HybridLinuxMediaProvider
        return HybridLinuxMediaProvider(excluded_players=excluded_players)
    else:
        raise NotImplementedError(f"Platform {system} is not supported")


def get_vrchat_provider() -> MediaProvider:
    """Get the VRChat media provider (Windows only)."""
    system = platform.system()
    if system != "Windows":
        raise NotImplementedError("VRChat provider is only available on Windows")
    
    from .vrchat import VRChatMediaProvider
    return VRChatMediaProvider()


__all__ = [
    "MediaProvider", 
    "MediaInfo", 
    "get_provider", 
    "get_vrchat_provider",
    "FILTER_ALL",
    "FILTER_NO_BROWSER",
    "FILTER_APPS_ONLY",
]
