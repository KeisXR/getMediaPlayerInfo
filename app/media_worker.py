"""
Background QThread that polls the local API server for media info.

The thread issues a simple HTTP GET to /now-playing every *interval* seconds
using Python's built-in urllib (no extra dependencies required).  When the
media changes, it emits the ``media_updated`` signal with the raw JSON dict
from the server, enriched with ``thumbnail_bytes`` (raw image bytes) fetched
from the localhost-only ``/thumbnail`` endpoint.  Connection state is tracked
and broadcast via ``server_status_changed``.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Optional

from PySide6.QtCore import QThread, Signal


class MediaPollThread(QThread):
    """Polls GET /now-playing (and /thumbnail) and emits signals on changes."""

    #: Emitted with the full JSON response dict from the server, plus an optional
    #: ``thumbnail_bytes`` key containing raw image bytes (or None).
    media_updated = Signal(dict)

    #: Emitted when the connection state to the local server changes.
    #: True = server reachable, False = server down/starting.
    server_status_changed = Signal(bool)

    def __init__(
        self,
        port: int = 8765,
        interval: float = 2.0,
        startup_delay: float = 2.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.port = port
        self.interval = interval
        self.startup_delay = startup_delay
        self._running = False
        self._last_title: str = ""
        self._last_artist: str = ""
        self._last_status: str = ""

    # ------------------------------------------------------------------
    # QThread interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        was_connected = False

        # Give uvicorn a moment to bind its socket before we start polling
        time.sleep(self.startup_delay)

        while self._running:
            try:
                url = f"http://127.0.0.1:{self.port}/now-playing"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data: dict = json.loads(resp.read().decode("utf-8"))

                if not was_connected:
                    was_connected = True
                    self.server_status_changed.emit(True)

                # Try to fetch album art from the localhost-only endpoint
                data["thumbnail_bytes"] = self._fetch_thumbnail()

                # Always emit the latest data so the UI stays fresh
                self.media_updated.emit(data)

            except (urllib.error.URLError, OSError):
                if was_connected:
                    was_connected = False
                    self.server_status_changed.emit(False)
            except Exception:
                pass

            # Sleep in small chunks so we can react to stop() quickly
            deadline = time.monotonic() + self.interval
            while self._running and time.monotonic() < deadline:
                time.sleep(0.1)

    def _fetch_thumbnail(self) -> Optional[bytes]:
        """Fetch raw thumbnail bytes from the localhost-only /thumbnail endpoint."""
        try:
            url = f"http://127.0.0.1:{self.port}/thumbnail"
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            pass
        return None

    def stop(self) -> None:
        """Ask the thread to stop gracefully."""
        self._running = False
        self.wait(5000)  # wait up to 5 s for the thread to finish
