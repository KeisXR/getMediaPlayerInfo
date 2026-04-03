"""
Statistics widget.

Shows listening time summaries, top artists and top source apps,
with a simple bar-chart rendered using QPainter.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.history_manager import HistoryManager
from app.i18n import tr
from app.utils import fmt_duration, fmt_ms


class _BarChart(QWidget):
    """Simple horizontal bar chart drawn with QPainter."""

    BAR_HEIGHT = 22
    BAR_GAP = 6
    LABEL_WIDTH = 140
    MAX_BAR_WIDTH = 200
    ACCENT = QColor("#89b4fa")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, int]] = []  # (label, value)
        self.setMinimumHeight(40)

    def set_data(self, items: list[tuple[str, int]]) -> None:
        self._items = items
        required = len(items) * (self.BAR_HEIGHT + self.BAR_GAP) + self.BAR_GAP
        self.setMinimumHeight(max(40, required))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._items:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        max_val = max(v for _, v in self._items) or 1
        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)

        y = self.BAR_GAP
        for label, value in self._items:
            # Label
            painter.setPen(QColor("#cdd6f4"))
            label_rect = QRect(0, y, self.LABEL_WIDTH - 8, self.BAR_HEIGHT)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

            # Bar background
            bar_x = self.LABEL_WIDTH
            bar_w = int(value / max_val * self.MAX_BAR_WIDTH)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#313244"))
            painter.drawRoundedRect(bar_x, y, self.MAX_BAR_WIDTH, self.BAR_HEIGHT, 4, 4)

            # Bar fill
            if bar_w > 0:
                painter.setBrush(self.ACCENT)
                painter.drawRoundedRect(bar_x, y, bar_w, self.BAR_HEIGHT, 4, 4)

            # Value text
            painter.setPen(QColor("#cdd6f4"))
            val_rect = QRect(bar_x + self.MAX_BAR_WIDTH + 8, y, 60, self.BAR_HEIGHT)
            painter.drawText(val_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(value))

            y += self.BAR_HEIGHT + self.BAR_GAP

        painter.end()


class StatisticsWidget(QWidget):
    """Statistics panel."""

    def __init__(self, history: HistoryManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._history = history
        self._setup_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Recalculate all stats from the history manager."""
        today_ms = self._history.today_duration_ms()
        week_ms = self._history.week_duration_ms()
        total_ms = self._history.total_duration_ms()

        self._today_val.setText(fmt_duration(today_ms) if today_ms else "—")
        self._week_val.setText(fmt_duration(week_ms) if week_ms else "—")
        self._total_val.setText(fmt_duration(total_ms) if total_ms else "—")
        self._today_count_val.setText(str(self._history.today_count()))
        self._total_count_val.setText(str(len(self._history.entries())))

        top_artists = self._history.top_artists(10)
        self._artists_chart.set_data(top_artists)
        if not top_artists:
            self._artists_empty.setVisible(True)
            self._artists_chart.setVisible(False)
        else:
            self._artists_empty.setVisible(False)
            self._artists_chart.setVisible(True)

        top_sources = self._history.top_sources(10)
        self._sources_chart.set_data(top_sources)
        if not top_sources:
            self._sources_empty.setVisible(True)
            self._sources_chart.setVisible(False)
        else:
            self._sources_empty.setVisible(False)
            self._sources_chart.setVisible(True)

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import QScrollArea

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Summary cards ────────────────────────────────────────────
        summary_group = QGroupBox(tr("stats_title"))
        summary_form = QFormLayout(summary_group)
        summary_form.setHorizontalSpacing(40)

        self._today_val = QLabel("—")
        summary_form.addRow(tr("stats_today") + ":", self._today_val)

        self._week_val = QLabel("—")
        summary_form.addRow(tr("stats_week") + ":", self._week_val)

        self._total_val = QLabel("—")
        summary_form.addRow(tr("stats_total") + ":", self._total_val)

        self._today_count_val = QLabel("0")
        summary_form.addRow(tr("stats_tracks_today") + ":", self._today_count_val)

        self._total_count_val = QLabel("0")
        summary_form.addRow(tr("stats_tracks_total") + ":", self._total_count_val)

        root.addWidget(summary_group)

        # Refresh button
        btn_hl = QHBoxLayout()
        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.clicked.connect(self.refresh)
        btn_hl.addStretch()
        btn_hl.addWidget(btn_refresh)
        root.addLayout(btn_hl)

        # ── Top artists ──────────────────────────────────────────────
        artists_group = QGroupBox(tr("stats_top_artists"))
        artists_vl = QVBoxLayout(artists_group)
        self._artists_empty = QLabel(tr("stats_no_data"))
        self._artists_empty.setObjectName("album_label")
        self._artists_chart = _BarChart()
        artists_vl.addWidget(self._artists_empty)
        artists_vl.addWidget(self._artists_chart)
        root.addWidget(artists_group)

        # ── Top sources ──────────────────────────────────────────────
        sources_group = QGroupBox(tr("stats_top_sources"))
        sources_vl = QVBoxLayout(sources_group)
        self._sources_empty = QLabel(tr("stats_no_data"))
        self._sources_empty.setObjectName("album_label")
        self._sources_chart = _BarChart()
        sources_vl.addWidget(self._sources_empty)
        sources_vl.addWidget(self._sources_chart)
        root.addWidget(sources_group)

        root.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
