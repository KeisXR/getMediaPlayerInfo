"""
Main window for getMediaPlayerInfo Desktop.

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  Sidebar (QListWidget) │  Content (QStackedWidget)      │
  └─────────────────────────────────────────────────────────┘
  └─ QStatusBar ────────────────────────────────────────────┘

The main window owns the ServerWorker and MediaPollThread and wires
everything together.
"""
from __future__ import annotations

import threading
import urllib.request
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from app.config import AppConfig
from app.history_manager import HistoryManager
from app.media_worker import MediaPollThread
from app.server_worker import ServerWorker
from app.i18n import tr, set_language

from ui.tray_icon import TrayIcon
from ui.widgets.now_playing import NowPlayingWidget
from ui.widgets.history import HistoryWidget
from ui.widgets.provider import ProviderWidget
from ui.widgets.api_server import ApiServerWidget
from ui.widgets.discord_tab import DiscordWidget
from ui.widgets.statistics import StatisticsWidget
from ui.widgets.settings import SettingsWidget


# Navigation entries: (translation_key, widget_factory_index)
_NAV_KEYS = [
    "nav_now_playing",
    "nav_history",
    "nav_provider",
    "nav_api",
    "nav_discord",
    "nav_statistics",
    "nav_settings",
]


def _load_stylesheet(name: str) -> str:
    """Load a QSS file from ui/styles/."""
    qss_path = Path(__file__).parent / "styles" / f"{name}.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


class MainWindow(QMainWindow):
    """Application main window."""

    # Relay server log lines from the background ServerWorker thread to the UI
    _server_log_signal = Signal(str)

    def __init__(self, config: AppConfig, history: HistoryManager) -> None:
        super().__init__()
        self._config = config
        self._history = history
        self._server: Optional[ServerWorker] = None
        self._poll_thread: Optional[MediaPollThread] = None
        self._last_title: str = ""
        self._last_artist: str = ""
        self._webhook_thread: Optional[threading.Thread] = None

        set_language(config.language)
        self._apply_theme(config.theme)
        self._setup_ui()
        self._setup_tray()
        self._server_log_signal.connect(self._api_widget.append_log)
        self._setup_workers()

        # Apply saved geometry
        if config.window_x >= 0 and config.window_y >= 0:
            self.move(config.window_x, config.window_y)
        self.resize(config.window_width, config.window_height)

        if config.start_minimized:
            self.hide()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self, theme: str) -> None:
        if theme == "system":
            QApplication.instance().setStyleSheet("")
            return
        qss = _load_stylesheet(theme)
        QApplication.instance().setStyleSheet(qss)

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle(tr("app_name"))
        self.setMinimumSize(800, 560)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        hl = QHBoxLayout(central)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        hl.addWidget(splitter)

        # ── Sidebar ──────────────────────────────────────────────────
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(190)
        self._sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for key in _NAV_KEYS:
            item = QListWidgetItem(tr(key))
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._sidebar.addItem(item)

        self._sidebar.setCurrentRow(0)
        self._sidebar.currentRowChanged.connect(self._on_nav_changed)
        splitter.addWidget(self._sidebar)

        # ── Content area ─────────────────────────────────────────────
        content_wrapper = QWidget()
        content_wrapper.setObjectName("content_area")
        content_vl = QHBoxLayout(content_wrapper)
        content_vl.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        content_vl.addWidget(self._stack)
        splitter.addWidget(content_wrapper)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # ── Create tab widgets ────────────────────────────────────────
        self._np_widget = NowPlayingWidget(self._config)
        self._hist_widget = HistoryWidget(self._history)
        self._prov_widget = ProviderWidget(self._config)
        self._api_widget = ApiServerWidget(
            self._config,
            on_start=self._start_server,
            on_stop=self._stop_server,
        )
        self._discord_widget = DiscordWidget(self._config)
        self._stats_widget = StatisticsWidget(self._history)
        self._settings_widget = SettingsWidget(self._config)
        self._settings_widget.ui_reload_requested.connect(self._on_ui_reload)

        for w in [
            self._np_widget,
            self._hist_widget,
            self._prov_widget,
            self._api_widget,
            self._discord_widget,
            self._stats_widget,
            self._settings_widget,
        ]:
            self._stack.addWidget(w)

        # ── Status bar ────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_api_lbl = QLabel("API: ○")
        self._status_api_lbl.setObjectName("album_label")
        self._status_bar.addWidget(self._status_api_lbl)

        self._status_media_lbl = QLabel(tr("np_no_media"))
        self._status_media_lbl.setObjectName("album_label")
        self._status_bar.addWidget(self._status_media_lbl)

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        self._tray = TrayIcon(self)
        self._tray.show_window_requested.connect(self._toggle_window)
        self._tray.quit_requested.connect(self._quit)
        self._tray.copy_now_playing_requested.connect(self._copy_now_playing)
        if self._tray.is_available():
            self._tray.show()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    def _setup_workers(self) -> None:
        if self._config.api_autostart:
            self._start_server()

    def _start_server(self) -> None:
        if self._server and self._server.is_running:
            return
        self._server = ServerWorker(
            host=self._config.api_host,
            port=self._config.api_port,
            filter_mode=self._config.filter_mode,
            on_log=self._on_server_log,
        )
        self._server.start()
        self._api_widget.set_running(True)
        self._np_widget.set_api_status(True)
        self._status_api_lbl.setText(
            f"API: ● http://localhost:{self._config.api_port}"
        )

        # Start poller after a short delay for uvicorn to bind
        QTimer.singleShot(2500, self._start_poller)

    def _stop_server(self) -> None:
        self._stop_poller()
        if self._server:
            self._server.stop()
            self._server = None
        self._api_widget.set_running(False)
        self._np_widget.set_api_status(False)
        self._status_api_lbl.setText("API: ○")

    def _start_poller(self) -> None:
        if self._poll_thread and self._poll_thread.isRunning():
            return
        self._poll_thread = MediaPollThread(
            port=self._config.api_port,
            interval=self._config.poll_interval,
            startup_delay=0,  # server already running
        )
        self._poll_thread.media_updated.connect(self._on_media_updated)
        self._poll_thread.server_status_changed.connect(self._on_server_status_changed)
        self._poll_thread.start()
        # Fetch root endpoint once for provider name
        QTimer.singleShot(1000, self._fetch_root_info)

    def _stop_poller(self) -> None:
        if self._poll_thread:
            self._poll_thread.stop()
            self._poll_thread = None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_nav_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        # Refresh data-heavy tabs on switch
        if index == 1:  # history
            self._hist_widget.refresh()
        elif index == 5:  # statistics
            self._stats_widget.refresh()

    @Slot(dict)
    def _on_media_updated(self, data: dict) -> None:
        """Called every ~2 s with the latest /now-playing response."""
        media = data.get("media") or {}

        # Update Now Playing tab
        self._np_widget.update_media(data)

        # Update Discord tab
        self._discord_widget.update_media(data)

        # Update status bar
        title = media.get("title", "")
        artist = media.get("artist", "")
        if title:
            self._status_media_lbl.setText(
                f"♪  {title}" + (f"  –  {artist}" if artist else "")
            )
        else:
            self._status_media_lbl.setText(tr("np_no_media"))

        # Record history if track changed
        changed = title != self._last_title or artist != self._last_artist
        if changed and title:
            self._last_title = title
            self._last_artist = artist
            m = SimpleNamespace(**media)
            if not hasattr(m, "source_app"):
                m.source_app = ""
            if self._history.record(m):
                # Desktop notification
                if self._config.notifications_enabled:
                    self._tray.show_message(title, artist or tr("np_source"))

                # Webhook
                if self._config.webhook_enabled and self._config.webhook_url:
                    self._fire_webhook(media)

        # Update tray
        self._tray.update_media(data)

    @Slot(bool)
    def _on_server_status_changed(self, connected: bool) -> None:
        self._np_widget.set_provider_status(
            "API", connected
        )
        self._prov_widget.set_connected(connected)

    def _on_server_log(self, line: str) -> None:
        """Relay server log to the API widget (called from background thread)."""
        self._server_log_signal.emit(line)

    def _fetch_root_info(self) -> None:
        """Fetch GET / once to obtain provider class name."""
        import urllib.request
        import json as _json
        try:
            url = f"http://127.0.0.1:{self._config.api_port}/"
            with urllib.request.urlopen(url, timeout=3) as r:
                data = _json.loads(r.read().decode())
            self._prov_widget.update_from_api(data)
        except Exception:
            pass

    @Slot()
    def _on_ui_reload(self) -> None:
        """Theme or language changed – re-apply stylesheet and rebuild texts."""
        self._apply_theme(self._config.theme)
        # Rebuild sidebar labels
        for i, key in enumerate(_NAV_KEYS):
            item = self._sidebar.item(i)
            if item:
                item.setText(tr(key))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_window(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _copy_now_playing(self) -> None:
        # Delegate to NowPlayingWidget's copy action
        self._np_widget._copy_to_clipboard()

    def _quit(self) -> None:
        self._stop_server()
        QApplication.quit()

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    def _fire_webhook(self, media: dict) -> None:
        url = self._config.webhook_url
        if not url:
            return

        def _send():
            try:
                payload = json.dumps(media, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass

        t = threading.Thread(target=_send, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._config.minimize_to_tray and self._tray.is_available():
            event.ignore()
            self.hide()
        else:
            self._stop_server()
            # Save window geometry
            self._config.window_width = self.width()
            self._config.window_height = self.height()
            self._config.window_x = self.x()
            self._config.window_y = self.y()
            self._config.save()
            event.accept()
