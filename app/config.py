"""
Application configuration management.

Config is stored in:
  - Windows: %APPDATA%\\getMediaPlayerInfo\\config.json
  - Linux:   ~/.config/getMediaPlayerInfo/config.json
  - macOS:   ~/Library/Application Support/getMediaPlayerInfo/config.json
"""
from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


def _get_config_dir() -> Path:
    """Return the OS-appropriate config directory."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / others: follow XDG
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "getMediaPlayerInfo"


CONFIG_DIR: Path = _get_config_dir()
CONFIG_FILE: Path = CONFIG_DIR / "config.json"
HISTORY_FILE: Path = CONFIG_DIR / "history.json"
LOG_FILE: Path = CONFIG_DIR / "app.log"


@dataclass
class AppConfig:
    # UI
    theme: str = "dark"          # dark | light | system
    language: str = "ja"         # ja | en
    window_width: int = 960
    window_height: int = 640
    window_x: int = -1           # -1 = center
    window_y: int = -1

    # Behavior
    minimize_to_tray: bool = True
    start_minimized: bool = False
    autostart: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8765
    api_autostart: bool = True
    api_log_max_lines: int = 200

    # Media / Provider
    filter_mode: str = "all"     # all | no-browser | apps-only
    cache_ttl: int = 30
    poll_interval: float = 2.0   # seconds between media polls

    # Notifications
    notifications_enabled: bool = True

    # Clipboard
    clipboard_template: str = "{title} - {artist}"

    # Webhook
    webhook_url: str = ""
    webhook_enabled: bool = False

    # Discord Rich Presence
    discord_enabled: bool = False
    discord_client_id: str = ""
    discord_details_template: str = "{title}"
    discord_state_template: str = "{artist}"

    # Last.fm scrobbling
    lastfm_enabled: bool = False
    lastfm_api_key: str = ""
    lastfm_shared_secret: str = ""
    lastfm_username: str = ""
    lastfm_session_key: str = ""

    # --- persistence helpers ---

    def save(self) -> None:
        """Persist config to disk (creates directory if needed)."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from disk.  Returns defaults if file is missing or corrupt."""
        if not CONFIG_FILE.exists():
            return cls()
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Only apply keys that exist in the dataclass to be forward/backward-compatible
            valid_keys = cls.__dataclass_fields__.keys()
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered)
        except Exception:
            return cls()

    def format_clipboard(self, media: Optional[object]) -> str:
        """Format the clipboard template string with the given MediaInfo object."""
        if media is None:
            return ""
        return self.clipboard_template.format(
            title=getattr(media, "title", ""),
            artist=getattr(media, "artist", ""),
            album=getattr(media, "album", ""),
            source=getattr(media, "source_app", ""),
            status=getattr(media, "status", ""),
        )

    def format_discord_details(self, media: Optional[object]) -> str:
        """Format the Discord details template."""
        if media is None:
            return ""
        return self.discord_details_template.format(
            title=getattr(media, "title", ""),
            artist=getattr(media, "artist", ""),
            album=getattr(media, "album", ""),
            source=getattr(media, "source_app", ""),
            status=getattr(media, "status", ""),
        )

    def format_discord_state(self, media: Optional[object]) -> str:
        """Format the Discord state template."""
        if media is None:
            return ""
        return self.discord_state_template.format(
            title=getattr(media, "title", ""),
            artist=getattr(media, "artist", ""),
            album=getattr(media, "album", ""),
            source=getattr(media, "source_app", ""),
            status=getattr(media, "status", ""),
        )
