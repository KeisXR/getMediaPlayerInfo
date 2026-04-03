"""
System tray icon and context menu.
"""
from __future__ import annotations

from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

from app.i18n import tr


def _make_tray_pixmap(status: str = "unknown") -> QPixmap:
    """Create a 32×32 coloured music-note icon for the tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))  # transparent

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    color_map = {
        "playing": QColor("#a6e3a1"),
        "paused": QColor("#f9e2af"),
        "stopped": QColor("#f38ba8"),
        "unknown": QColor("#6c7086"),
        "cached": QColor("#6c7086"),
    }
    color = color_map.get(status, QColor("#6c7086"))

    painter.setBrush(color)
    painter.setPen(color)
    painter.drawEllipse(2, 2, 28, 28)

    painter.setPen(QColor("#1e1e2e"))
    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x0084, "♪")  # Qt.AlignCenter

    painter.end()
    return pixmap


class TrayIcon(QObject):
    """Manages the system tray icon and its context menu."""

    show_window_requested = Signal()
    quit_requested = Signal()
    copy_now_playing_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._media: Optional[dict] = None

        self._icon = QSystemTrayIcon(self)
        self._icon.setIcon(QIcon(_make_tray_pixmap("unknown")))
        self._icon.setToolTip(tr("app_name"))
        self._icon.activated.connect(self._on_activated)

        self._build_menu()
        self._icon.setContextMenu(self._menu)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        self._icon.show()

    def hide(self) -> None:
        self._icon.hide()

    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def update_media(self, data: dict) -> None:
        """Refresh tray icon and tooltip from an API response dict."""
        media = data.get("media")
        self._media = media
        if media and media.get("title"):
            title = media["title"]
            artist = media.get("artist", "")
            status = media.get("status", "unknown")
            tooltip = f"{title}"
            if artist:
                tooltip += f"\n{artist}"
            tooltip += f"\n[{status}]"
            self._icon.setToolTip(tooltip)
            self._icon.setIcon(QIcon(_make_tray_pixmap(status)))
            self._now_playing_action.setText(f"♪  {title[:40]}")
        else:
            self._icon.setToolTip(tr("app_name") + "\n" + tr("tray_no_media"))
            self._icon.setIcon(QIcon(_make_tray_pixmap("unknown")))
            self._now_playing_action.setText(tr("tray_no_media"))

    def show_message(self, title: str, body: str) -> None:
        """Show a balloon / toast notification."""
        if QSystemTrayIcon.supportsMessages():
            self._icon.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 4000)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        self._menu = QMenu()

        self._now_playing_action = self._menu.addAction(tr("tray_no_media"))
        self._now_playing_action.setEnabled(False)

        self._menu.addSeparator()

        show_action = self._menu.addAction(tr("tray_show"))
        show_action.triggered.connect(self.show_window_requested)

        copy_action = self._menu.addAction(tr("tray_copy_now_playing"))
        copy_action.triggered.connect(self.copy_now_playing_requested)

        self._menu.addSeparator()

        quit_action = self._menu.addAction(tr("tray_quit"))
        quit_action.triggered.connect(self.quit_requested)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click → toggle window
            self.show_window_requested.emit()
