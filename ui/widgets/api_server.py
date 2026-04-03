"""
API Server widget.

Controls for starting/stopping the embedded uvicorn server,
real-time access log, QR code for mobile access, and a link to Swagger UI.
"""
from __future__ import annotations

import socket
import webbrowser
from typing import Optional, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.i18n import tr


class ApiServerWidget(QWidget):
    """API server control panel."""

    def __init__(
        self,
        config: AppConfig,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._on_start = on_start
        self._on_stop = on_stop
        self._running = False
        self._setup_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._btn_start.setEnabled(False)
            self._btn_stop.setEnabled(True)
            self._status_dot.setStyleSheet("color: #a6e3a1; font-size: 14px;")
            self._status_label.setText(tr("status_running"))
            url = f"http://localhost:{self._port_spin.value()}"
            self._url_label.setText(url)
            self._update_qr(url)
        else:
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
            self._status_dot.setStyleSheet("color: #f38ba8; font-size: 14px;")
            self._status_label.setText(tr("status_stopped"))

    def append_log(self, line: str) -> None:
        """Append a line to the access log viewer."""
        self._log_edit.append(line)
        # Keep log bounded
        doc = self._log_edit.document()
        max_lines = self._config.api_log_max_lines
        if doc.blockCount() > max_lines:
            cursor = self._log_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Server controls ─────────────────────────────────────────
        ctrl_group = QGroupBox(tr("api_title"))
        ctrl_vl = QVBoxLayout(ctrl_group)

        # Status row
        status_row = QHBoxLayout()
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("color: #f38ba8; font-size: 14px;")
        self._status_label = QLabel(tr("status_stopped"))
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        ctrl_vl.addLayout(status_row)

        # Settings form
        form = QFormLayout()
        form.setHorizontalSpacing(20)

        self._host_edit = QLineEdit(self._config.api_host)
        form.addRow(tr("api_host") + ":", self._host_edit)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(self._config.api_port)
        form.addRow(tr("api_port") + ":", self._port_spin)

        self._url_label = QLabel("—")
        self._url_label.setObjectName("album_label")
        self._url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow(tr("api_url") + ":", self._url_label)

        ctrl_vl.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton(tr("btn_start"))
        self._btn_start.setObjectName("btn_start")
        self._btn_start.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton(tr("btn_stop"))
        self._btn_stop.setObjectName("btn_stop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        btn_row.addWidget(self._btn_stop)

        btn_docs = QPushButton(tr("api_docs"))
        btn_docs.clicked.connect(self._open_docs)
        btn_row.addWidget(btn_docs)

        btn_row.addStretch()
        ctrl_vl.addLayout(btn_row)

        root.addWidget(ctrl_group)

        # ── Log ─────────────────────────────────────────────────────
        log_group = QGroupBox(tr("api_log"))
        log_vl = QVBoxLayout(log_group)
        log_vl.setContentsMargins(8, 8, 8, 8)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText(tr("api_log"))
        self._log_edit.setMaximumHeight(200)
        log_vl.addWidget(self._log_edit)

        btn_clear_log = QPushButton(tr("api_log_clear"))
        btn_clear_log.clicked.connect(self._log_edit.clear)
        log_vl.addWidget(btn_clear_log)

        root.addWidget(log_group)

        # ── QR Code ─────────────────────────────────────────────────
        qr_group = QGroupBox(tr("api_qr_title"))
        qr_hl = QHBoxLayout(qr_group)

        self._qr_label = QLabel(tr("api_qr_title"))
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setFixedSize(160, 160)
        self._qr_label.setObjectName("art_label")
        qr_hl.addWidget(self._qr_label)

        qr_info_vl = QVBoxLayout()
        qr_info_vl.setSpacing(8)

        self._lan_label = QLabel("")
        self._lan_label.setObjectName("album_label")
        self._lan_label.setWordWrap(True)
        self._lan_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        qr_info_vl.addWidget(QLabel(tr("api_qr_title")))
        qr_info_vl.addWidget(self._lan_label)
        qr_info_vl.addStretch()
        qr_hl.addLayout(qr_info_vl)

        root.addWidget(qr_group)
        root.addStretch()

        # Populate LAN IP immediately
        self._populate_lan_urls()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _populate_lan_urls(self) -> None:
        """Show LAN URLs for mobile access."""
        ips = self._get_local_ips()
        port = self._port_spin.value()
        urls = "\n".join(f"http://{ip}:{port}" for ip in ips)
        self._lan_label.setText(urls or "—")

    def _get_local_ips(self) -> list[str]:
        ips = []
        try:
            hostname = socket.gethostname()
            ips = [i[4][0] for i in socket.getaddrinfo(hostname, None)
                   if i[0] == socket.AF_INET and not i[4][0].startswith("127.")]
        except Exception:
            pass
        return list(set(ips))

    def _update_qr(self, url: str) -> None:
        """Try to render a QR code; fall back to text if qrcode is not installed."""
        try:
            import qrcode  # type: ignore
            from PIL.ImageQt import ImageQt  # type: ignore

            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            qt_img = ImageQt(img)
            pixmap = QPixmap.fromImage(qt_img).scaled(
                150, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._qr_label.setPixmap(pixmap)
        except ImportError:
            self._qr_label.setText(f"QR:\n{url}\n\n(pip install qrcode[pil]\nto show QR image)")
        except Exception as exc:
            self._qr_label.setText(str(exc))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_start_clicked(self) -> None:
        # Save port/host from UI before starting
        self._config.api_port = self._port_spin.value()
        self._config.api_host = self._host_edit.text().strip() or "0.0.0.0"
        self._config.save()
        if self._on_start:
            self._on_start()
        self._populate_lan_urls()

    def _on_stop_clicked(self) -> None:
        if self._on_stop:
            self._on_stop()

    def _open_docs(self) -> None:
        port = self._port_spin.value()
        webbrowser.open(f"http://localhost:{port}/docs")
