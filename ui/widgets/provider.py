"""
Provider widget.

Shows the active media provider, its connection state,
and lets the user change the filter mode (requires server restart).
"""
from __future__ import annotations

import platform
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.i18n import tr


_FILTER_OPTIONS = [
    ("prov_filter_all", "all"),
    ("prov_filter_no_browser", "no-browser"),
    ("prov_filter_apps_only", "apps-only"),
]


class ProviderWidget(QWidget):
    """Provider status and configuration panel."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._setup_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_from_api(self, root_data: dict) -> None:
        """Update display from the GET / API response."""
        provider_class = root_data.get("provider") or "—"
        self._provider_class_label.setText(provider_class)

    def set_connected(self, connected: bool) -> None:
        if connected:
            self._dot.setStyleSheet("color: #a6e3a1; font-size: 16px;")
            self._status_label.setText(tr("status_connected"))
        else:
            self._dot.setStyleSheet("color: #f38ba8; font-size: 16px;")
            self._status_label.setText(tr("status_disconnected"))

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Status card ─────────────────────────────────────────────
        status_group = QGroupBox(tr("prov_title"))
        status_vl = QVBoxLayout(status_group)

        dot_row = QHBoxLayout()
        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #f38ba8; font-size: 16px;")
        self._status_label = QLabel(tr("status_disconnected"))
        dot_row.addWidget(self._dot)
        dot_row.addWidget(self._status_label)
        dot_row.addStretch()
        status_vl.addLayout(dot_row)

        form = QFormLayout()
        form.setHorizontalSpacing(20)

        self._platform_label = QLabel(platform.system())
        form.addRow(tr("prov_platform") + ":", self._platform_label)

        self._provider_class_label = QLabel("—")
        form.addRow(tr("prov_class") + ":", self._provider_class_label)

        status_vl.addLayout(form)
        root.addWidget(status_group)

        # ── Filter mode card ────────────────────────────────────────
        filter_group = QGroupBox(tr("prov_filter_mode"))
        filter_vl = QVBoxLayout(filter_group)

        self._filter_combo = QComboBox()
        for key, value in _FILTER_OPTIONS:
            self._filter_combo.addItem(tr(key), value)

        # Select current setting
        current_index = next(
            (i for i, (_, v) in enumerate(_FILTER_OPTIONS) if v == self._config.filter_mode),
            0,
        )
        self._filter_combo.setCurrentIndex(current_index)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_vl.addWidget(self._filter_combo)

        self._restart_note = QLabel(tr("prov_restart_required"))
        self._restart_note.setObjectName("album_label")
        self._restart_note.setVisible(False)
        filter_vl.addWidget(self._restart_note)

        root.addWidget(filter_group)

        root.addStretch()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_filter_changed(self, index: int) -> None:
        _, value = _FILTER_OPTIONS[index]
        if value != self._config.filter_mode:
            self._config.filter_mode = value
            self._config.save()
            self._restart_note.setVisible(True)
        else:
            self._restart_note.setVisible(False)
