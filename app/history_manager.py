"""
Play history management.

Each play event is stored as a JSON-line entry in:
  <CONFIG_DIR>/history.json
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import HISTORY_FILE, CONFIG_DIR
from .utils import fmt_ms as _fmt_ms


@dataclass
class HistoryEntry:
    """One recorded track-play event."""
    timestamp: str          # ISO 8601
    title: str
    artist: str
    album: str
    source_app: str
    duration_ms: Optional[int]
    position_ms: Optional[int]

    @classmethod
    def from_media(cls, media: object) -> "HistoryEntry":
        """Create entry from a MediaInfo-like object."""
        return cls(
            timestamp=datetime.now(timezone.utc).astimezone().isoformat(),
            title=getattr(media, "title", ""),
            artist=getattr(media, "artist", ""),
            album=getattr(media, "album", ""),
            source_app=getattr(media, "source_app", ""),
            duration_ms=getattr(media, "duration_ms", None),
            position_ms=getattr(media, "position_ms", None),
        )

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def local_time_str(self) -> str:
        """Return a short human-readable local time string."""
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%m/%d %H:%M")
        except Exception:
            return self.timestamp

    def duration_str(self) -> str:
        """Return formatted duration string or empty string."""
        if self.duration_ms is None:
            return ""
        return _fmt_ms(self.duration_ms)


class HistoryManager:
    """Manages reading and writing the play history."""

    MAX_ENTRIES = 10_000  # Cap in-memory list to avoid unbounded growth

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []
        self._last_title: str = ""
        self._last_artist: str = ""
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, media: object) -> bool:
        """Record a new play event if it differs from the previous one.

        Returns True if a new entry was added.
        """
        title = getattr(media, "title", "")
        artist = getattr(media, "artist", "")

        if not title:
            return False

        if title == self._last_title and artist == self._last_artist:
            return False  # Same track, skip

        self._last_title = title
        self._last_artist = artist

        entry = HistoryEntry.from_media(media)
        self._entries.insert(0, entry)   # newest first

        # Trim
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[: self.MAX_ENTRIES]

        self._save()
        return True

    def entries(self) -> list[HistoryEntry]:
        """Return all entries (newest first)."""
        return list(self._entries)

    def clear(self) -> None:
        """Remove all entries."""
        self._entries = []
        self._last_title = ""
        self._last_artist = ""
        self._save()

    def export_csv(self, path: Path) -> None:
        """Export history to a CSV file."""
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["timestamp", "title", "artist", "album", "source_app", "duration_ms"])
            for e in self._entries:
                writer.writerow([e.timestamp, e.title, e.artist, e.album, e.source_app, e.duration_ms])

    def export_json(self, path: Path) -> None:
        """Export history to a JSON file."""
        data = [asdict(e) for e in self._entries]
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    # --- Statistics helpers ---

    def total_duration_ms(self) -> int:
        """Sum of all recorded durations in ms."""
        return sum(e.duration_ms for e in self._entries if e.duration_ms)

    def today_duration_ms(self) -> int:
        """Sum of durations recorded today (local time)."""
        today = datetime.now().date()
        total = 0
        for e in self._entries:
            try:
                dt = datetime.fromisoformat(e.timestamp)
                if dt.date() == today and e.duration_ms:
                    total += e.duration_ms
            except Exception:
                pass
        return total

    def week_duration_ms(self) -> int:
        """Sum of durations recorded in the current ISO week."""
        from datetime import timedelta
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        total = 0
        for e in self._entries:
            try:
                dt = datetime.fromisoformat(e.timestamp)
                if dt.date() >= start_of_week and e.duration_ms:
                    total += e.duration_ms
            except Exception:
                pass
        return total

    def top_artists(self, n: int = 10) -> list[tuple[str, int]]:
        """Return top-n artists by play count, sorted descending."""
        counts: dict[str, int] = {}
        for e in self._entries:
            if e.artist:
                counts[e.artist] = counts.get(e.artist, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def top_sources(self, n: int = 10) -> list[tuple[str, int]]:
        """Return top-n source apps by play count."""
        counts: dict[str, int] = {}
        for e in self._entries:
            if e.source_app:
                counts[e.source_app] = counts.get(e.source_app, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def today_count(self) -> int:
        today = datetime.now().date()
        return sum(
            1 for e in self._entries
            if self._entry_date(e) == today
        )

    def _entry_date(self, e: HistoryEntry):
        try:
            return datetime.fromisoformat(e.timestamp).date()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not HISTORY_FILE.exists():
            return
        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._entries = [HistoryEntry.from_dict(d) for d in data]
            if self._entries:
                self._last_title = self._entries[0].title
                self._last_artist = self._entries[0].artist
        except Exception:
            self._entries = []

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self._entries]
        with HISTORY_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
