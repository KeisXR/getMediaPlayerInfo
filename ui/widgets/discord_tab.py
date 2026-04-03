"""
Discord Rich Presence widget.

Toggle, Client ID input, display-template editor and a live preview.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.i18n import tr


class DiscordWidget(QWidget):
    """Discord Rich Presence configuration panel."""

    # Used to relay status updates from the background presence thread safely
    _status_signal = Signal(bool, str)

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._presence_thread: Optional[threading.Thread] = None
        self._presence_running = False
        self._current_media: Optional[dict] = None
        self._setup_ui()
        self._status_signal.connect(self._apply_status)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_media(self, data: dict) -> None:
        """Receive latest media data for preview."""
        self._current_media = data.get("media")
        self._refresh_preview()

    def get_enabled(self) -> bool:
        return self._enable_cb.isChecked()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Enable toggle ────────────────────────────────────────────
        toggle_group = QGroupBox(tr("discord_title"))
        toggle_vl = QVBoxLayout(toggle_group)

        self._enable_cb = QCheckBox(tr("discord_enable"))
        self._enable_cb.setChecked(self._config.discord_enabled)
        self._enable_cb.toggled.connect(self._on_toggle)
        toggle_vl.addWidget(self._enable_cb)

        # Status row
        status_hl = QHBoxLayout()
        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #f38ba8; font-size: 14px;")
        self._status_label = QLabel(tr("status_disconnected"))
        status_hl.addWidget(self._dot)
        status_hl.addWidget(self._status_label)
        status_hl.addStretch()
        toggle_vl.addLayout(status_hl)

        root.addWidget(toggle_group)

        # ── Config ───────────────────────────────────────────────────
        config_group = QGroupBox("Configuration")
        form = QFormLayout(config_group)
        form.setHorizontalSpacing(20)

        self._client_id_edit = QLineEdit(self._config.discord_client_id)
        self._client_id_edit.setPlaceholderText("e.g. 1234567890123456789")
        self._client_id_edit.textChanged.connect(self._on_settings_changed)
        form.addRow(tr("discord_client_id") + ":", self._client_id_edit)

        client_hint = QLabel(tr("discord_client_id_hint"))
        client_hint.setObjectName("album_label")
        client_hint.setWordWrap(True)
        form.addRow("", client_hint)

        self._details_edit = QLineEdit(self._config.discord_details_template)
        self._details_edit.setPlaceholderText("{title}")
        self._details_edit.textChanged.connect(self._on_settings_changed)
        form.addRow("Details template:", self._details_edit)

        self._state_edit = QLineEdit(self._config.discord_state_template)
        self._state_edit.setPlaceholderText("{artist}")
        self._state_edit.textChanged.connect(self._on_settings_changed)
        form.addRow("State template:", self._state_edit)

        hint = QLabel(tr("discord_template_hint"))
        hint.setObjectName("album_label")
        hint.setWordWrap(True)
        form.addRow("", hint)

        btn_save = QPushButton(tr("btn_save"))
        btn_save.clicked.connect(self._save_settings)
        form.addRow("", btn_save)

        root.addWidget(config_group)

        # ── Preview ──────────────────────────────────────────────────
        preview_group = QGroupBox(tr("discord_preview"))
        preview_vl = QVBoxLayout(preview_group)

        self._preview_label = QLabel("—")
        self._preview_label.setWordWrap(True)
        preview_vl.addWidget(self._preview_label)

        root.addWidget(preview_group)
        root.addStretch()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_toggle(self, checked: bool) -> None:
        self._config.discord_enabled = checked
        self._config.save()
        if checked:
            self._start_presence()
        else:
            self._stop_presence()

    def _on_settings_changed(self) -> None:
        self._refresh_preview()

    def _save_settings(self) -> None:
        self._config.discord_client_id = self._client_id_edit.text().strip()
        self._config.discord_details_template = self._details_edit.text().strip()
        self._config.discord_state_template = self._state_edit.text().strip()
        self._config.save()

    # ------------------------------------------------------------------
    # Presence management
    # ------------------------------------------------------------------

    def _start_presence(self) -> None:
        client_id = self._client_id_edit.text().strip()
        if not client_id:
            self._set_status(False, tr("discord_client_id_hint"))
            return

        self._stop_presence()
        self._presence_running = True
        self._presence_thread = threading.Thread(
            target=self._run_presence, args=(client_id,), daemon=True
        )
        self._presence_thread.start()

    def _stop_presence(self) -> None:
        self._presence_running = False
        self._set_status(False)

    def _run_presence(self, client_id: str) -> None:
        """Run Discord Rich Presence in a background thread."""
        import asyncio
        try:
            from pypresence import AioPresence, exceptions as pp_exc

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _inner():
                rpc = AioPresence(client_id)
                try:
                    await rpc.connect()
                except pp_exc.DiscordNotFound:
                    self._set_status(False, tr("discord_not_found"))
                    return
                except Exception as exc:
                    self._set_status(False, str(exc))
                    return

                self._set_status(True)

                last_title = None
                while self._presence_running:
                    try:
                        if self._current_media:
                            media = self._current_media
                            title = media.get("title", "")
                            details = self._format_template(
                                self._details_edit.text(), media
                            )
                            state = self._format_template(
                                self._state_edit.text(), media
                            )
                            if title != last_title:
                                last_title = title
                                await rpc.update(
                                    details=details[:128] if details else None,
                                    state=state[:128] if state else None,
                                )
                    except Exception:
                        pass
                    await asyncio.sleep(3)

                try:
                    await rpc.clear()
                    await rpc.close()
                except Exception:
                    pass
                self._set_status(False)

            loop.run_until_complete(_inner())
        except ImportError:
            self._set_status(False, "pypresence not installed")
        except Exception as exc:
            self._set_status(False, str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_template(template: str, media: dict) -> str:
        return template.format(
            title=media.get("title", ""),
            artist=media.get("artist", ""),
            album=media.get("album", ""),
            source=media.get("source_app", ""),
            status=media.get("status", ""),
        )

    def _refresh_preview(self) -> None:
        if not self._current_media:
            self._preview_label.setText("—")
            return
        details = self._format_template(self._details_edit.text(), self._current_media)
        state = self._format_template(self._state_edit.text(), self._current_media)
        self._preview_label.setText(f"Details: {details}\nState:   {state}")

    def _set_status(self, connected: bool, note: str = "") -> None:
        # Safe to call from any thread – routed via queued Signal
        self._status_signal.emit(connected, note)

    def _apply_status(self, connected: bool, note: str = "") -> None:
        if connected:
            self._dot.setStyleSheet("color: #a6e3a1; font-size: 14px;")
            self._status_label.setText(tr("status_connected"))
        else:
            self._dot.setStyleSheet("color: #f38ba8; font-size: 14px;")
            self._status_label.setText(
                tr("status_disconnected") + (f": {note}" if note else "")
            )
