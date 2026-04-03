"""
Now Playing widget.

Shows the currently playing track with album-art placeholder, title,
artist, album, playback-status badge, a progress bar and a
"copy to clipboard" button.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.config import AppConfig
from app.utils import fmt_ms


class NowPlayingWidget(QWidget):
    """Main 'Now Playing' panel."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._current_media: Optional[dict] = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_media(self, data: dict) -> None:
        """Refresh the panel from the /now-playing API response dict."""
        media = data.get("media")
        self._current_media = media
        if not media or not media.get("title"):
            self._show_empty()
            return
        self._show_media(media)

    def clear(self) -> None:
        """Reset to the 'nothing playing' state."""
        self._current_media = None
        self._show_empty()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Card ──────────────────────────────────────────────────
        card = QGroupBox(tr("nav_now_playing"))
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        # Top row: art + info
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # Album art placeholder
        self._art_label = QLabel()
        self._art_label.setObjectName("art_label")
        self._art_label.setFixedSize(140, 140)
        self._art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art_label.setText("🎵")
        font = QFont()
        font.setPointSize(40)
        self._art_label.setFont(font)
        top_row.addWidget(self._art_label, 0, Qt.AlignmentFlag.AlignTop)

        # Text info column
        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        self._title_label = QLabel(tr("np_no_media"))
        self._title_label.setObjectName("title_label")
        self._title_label.setWordWrap(True)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        info_col.addWidget(self._title_label)

        self._artist_label = QLabel("")
        self._artist_label.setObjectName("artist_label")
        self._artist_label.setWordWrap(True)
        info_col.addWidget(self._artist_label)

        self._album_label = QLabel("")
        self._album_label.setObjectName("album_label")
        self._album_label.setWordWrap(True)
        info_col.addWidget(self._album_label)

        info_col.addSpacerItem(
            QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # Status badge
        self._status_badge = QLabel("")
        self._status_badge.setObjectName("status_badge_unknown")
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_col.addWidget(self._status_badge)

        # Source label
        source_row = QHBoxLayout()
        self._source_icon = QLabel("▶")
        self._source_label = QLabel("")
        self._source_label.setObjectName("album_label")
        source_row.addWidget(self._source_icon)
        source_row.addWidget(self._source_label)
        source_row.addStretch()
        info_col.addLayout(source_row)

        top_row.addLayout(info_col)
        card_layout.addLayout(top_row)

        # Progress bar row
        progress_row = QVBoxLayout()
        progress_row.setSpacing(4)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 1000)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        progress_row.addWidget(self._progress_bar)

        time_row = QHBoxLayout()
        self._pos_label = QLabel("0:00")
        self._pos_label.setObjectName("album_label")
        self._dur_label = QLabel("0:00")
        self._dur_label.setObjectName("album_label")
        time_row.addWidget(self._pos_label)
        time_row.addStretch()
        time_row.addWidget(self._dur_label)
        progress_row.addLayout(time_row)

        card_layout.addLayout(progress_row)

        # Copy button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._copy_btn = QPushButton(tr("btn_copy"))
        self._copy_btn.setToolTip(
            tr("np_copy_template") + f": {self._config.clipboard_template}"
        )
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self._copy_btn)
        card_layout.addLayout(btn_row)

        root.addWidget(card)

        # ── Status indicators row ──────────────────────────────────
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.NoFrame)
        status_hl = QHBoxLayout(status_frame)
        status_hl.setContentsMargins(0, 0, 0, 0)
        status_hl.setSpacing(20)

        self._api_indicator = self._make_indicator("API")
        status_hl.addLayout(self._api_indicator["layout"])

        self._provider_indicator = self._make_indicator(tr("prov_title"))
        status_hl.addLayout(self._provider_indicator["layout"])

        status_hl.addStretch()
        root.addWidget(status_frame)

        root.addStretch()

        # Feedback timer for "Copied!" message
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(
            lambda: self._copy_btn.setText(tr("btn_copy"))
        )

        # Initialise to empty state
        self._show_empty()

    @staticmethod
    def _make_indicator(label_text: str) -> dict:
        """Return a small dot + label indicator layout dict."""
        dot = QLabel("●")
        dot.setStyleSheet("color: #f38ba8; font-size: 10px;")
        lbl = QLabel(label_text)
        lbl.setObjectName("album_label")
        hl = QHBoxLayout()
        hl.setSpacing(6)
        hl.addWidget(dot)
        hl.addWidget(lbl)
        return {"layout": hl, "dot": dot, "label": lbl}

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _show_empty(self) -> None:
        self._title_label.setText(tr("np_no_media"))
        self._artist_label.setText("")
        self._album_label.setText("")
        self._source_label.setText("")
        self._source_icon.setText("●")
        self._source_icon.setStyleSheet("color: #6c7086;")
        self._set_status_badge("unknown")
        self._progress_bar.setValue(0)
        self._pos_label.setText("0:00")
        self._dur_label.setText("0:00")
        self._art_label.setText("🎵")
        self._copy_btn.setEnabled(False)

    def _show_media(self, media: dict) -> None:
        title = media.get("title") or ""
        artist = media.get("artist") or ""
        album = media.get("album") or ""
        source = media.get("source_app") or ""
        status = media.get("status") or "unknown"
        pos_ms = media.get("position_ms")
        dur_ms = media.get("duration_ms")

        self._title_label.setText(title or tr("np_no_media"))
        self._artist_label.setText(artist)
        self._album_label.setText(album)
        self._source_label.setText(source)
        self._source_icon.setText("▶" if status == "playing" else "●")
        self._source_icon.setStyleSheet(
            "color: #a6e3a1;" if status == "playing" else "color: #f9e2af;"
        )
        self._set_status_badge(status)

        # Progress
        if pos_ms is not None and dur_ms and dur_ms > 0:
            self._progress_bar.setValue(int(pos_ms / dur_ms * 1000))
            self._pos_label.setText(fmt_ms(pos_ms))
            self._dur_label.setText(fmt_ms(dur_ms))
        else:
            self._progress_bar.setValue(0)
            self._pos_label.setText("")
            self._dur_label.setText("")

        self._copy_btn.setEnabled(bool(title))

    def _set_status_badge(self, status: str) -> None:
        status_map = {
            "playing": (tr("status_playing"), "status_badge_playing"),
            "paused": (tr("status_paused"), "status_badge_paused"),
            "stopped": (tr("status_stopped_play"), "status_badge_stopped"),
            "unknown": (tr("status_unknown"), "status_badge_unknown"),
            "cached": (tr("status_unknown"), "status_badge_unknown"),
        }
        text, obj_name = status_map.get(status, (status, "status_badge_unknown"))
        self._status_badge.setText(text)
        self._status_badge.setObjectName(obj_name)
        # Force style re-evaluation
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)

    # ------------------------------------------------------------------
    # Server/Provider indicator updaters (called from MainWindow)
    # ------------------------------------------------------------------

    def set_api_status(self, running: bool) -> None:
        dot = self._api_indicator["dot"]
        lbl = self._api_indicator["label"]
        if running:
            dot.setStyleSheet("color: #a6e3a1; font-size: 10px;")
            lbl.setText(f"API ● {tr('status_running')}")
        else:
            dot.setStyleSheet("color: #f38ba8; font-size: 10px;")
            lbl.setText(f"API ● {tr('status_stopped')}")

    def set_provider_status(self, provider_name: str, connected: bool) -> None:
        dot = self._provider_indicator["dot"]
        lbl = self._provider_indicator["label"]
        if connected:
            dot.setStyleSheet("color: #a6e3a1; font-size: 10px;")
            lbl.setText(f"{provider_name} ● {tr('status_connected')}")
        else:
            dot.setStyleSheet("color: #f38ba8; font-size: 10px;")
            lbl.setText(f"{provider_name} ● {tr('status_disconnected')}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _copy_to_clipboard(self) -> None:
        if not self._current_media:
            return

        text = self._config.clipboard_template.format(
            title=self._current_media.get("title", ""),
            artist=self._current_media.get("artist", ""),
            album=self._current_media.get("album", ""),
            source=self._current_media.get("source_app", ""),
            status=self._current_media.get("status", ""),
        )
        QApplication.clipboard().setText(text)
        self._copy_btn.setText(tr("np_copied"))
        self._feedback_timer.start(2000)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
