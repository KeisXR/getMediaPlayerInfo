"""
Play History widget.

Displays a searchable table of previously played tracks with
CSV / JSON export and a clear button.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.history_manager import HistoryManager
from app.i18n import tr


class HistoryWidget(QWidget):
    """Play history panel."""

    _COLUMNS = [
        "hist_col_time",
        "hist_col_title",
        "hist_col_artist",
        "hist_col_album",
        "hist_col_source",
        "hist_col_duration",
    ]

    def __init__(self, history: HistoryManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._history = history
        self._setup_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload the table from the history manager."""
        entries = self._history.entries()
        self._model.setRowCount(0)
        for entry in entries:
            row = [
                QStandardItem(entry.local_time_str()),
                QStandardItem(entry.title),
                QStandardItem(entry.artist),
                QStandardItem(entry.album),
                QStandardItem(entry.source_app),
                QStandardItem(entry.duration_str()),
            ]
            for item in row:
                item.setEditable(False)
            self._model.appendRow(row)

        count = self._model.rowCount()
        self._count_label.setText(f"{count} {tr('hist_col_title').lower()}s")

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ── Header row ─────────────────────────────────────────────
        header_hl = QHBoxLayout()
        header_hl.setSpacing(12)

        # Search bar
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText(tr("hist_search_placeholder"))
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._on_search)
        header_hl.addWidget(self._search_box)

        self._count_label = QLabel("0")
        self._count_label.setObjectName("album_label")
        header_hl.addWidget(self._count_label)

        header_hl.addStretch()

        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.clicked.connect(self.refresh)
        header_hl.addWidget(btn_refresh)

        root.addLayout(header_hl)

        # ── Table ───────────────────────────────────────────────────
        group = QGroupBox(tr("hist_title"))
        group_vl = QVBoxLayout(group)
        group_vl.setContentsMargins(8, 8, 8, 8)
        group_vl.setSpacing(8)

        self._model = QStandardItemModel(0, len(self._COLUMNS))
        self._model.setHorizontalHeaderLabels([tr(k) for k in self._COLUMNS])

        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)  # search all columns

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        # Column widths
        self._table.setColumnWidth(0, 110)  # time
        self._table.setColumnWidth(1, 200)  # title
        self._table.setColumnWidth(2, 140)  # artist
        self._table.setColumnWidth(3, 140)  # album
        self._table.setColumnWidth(4, 100)  # source
        self._table.setColumnWidth(5, 70)   # duration

        group_vl.addWidget(self._table)
        root.addWidget(group)

        # ── Footer buttons ──────────────────────────────────────────
        footer_hl = QHBoxLayout()
        footer_hl.setSpacing(8)

        btn_csv = QPushButton(tr("btn_export_csv"))
        btn_csv.clicked.connect(self._export_csv)
        footer_hl.addWidget(btn_csv)

        btn_json = QPushButton(tr("btn_export_json"))
        btn_json.clicked.connect(self._export_json)
        footer_hl.addWidget(btn_json)

        footer_hl.addStretch()

        btn_clear = QPushButton(tr("btn_clear"))
        btn_clear.clicked.connect(self._clear_history)
        footer_hl.addWidget(btn_clear)

        root.addLayout(footer_hl)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("btn_export_csv"), "history.csv", "CSV (*.csv)"
        )
        if path:
            self._history.export_csv(Path(path))
            self._show_info(tr("hist_export_success"))

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("btn_export_json"), "history.json", "JSON (*.json)"
        )
        if path:
            self._history.export_json(Path(path))
            self._show_info(tr("hist_export_success"))

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            tr("dlg_confirm"),
            tr("hist_clear_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._history.clear()
            self.refresh()

    def _show_info(self, msg: str) -> None:
        QMessageBox.information(self, tr("dlg_info"), msg)
