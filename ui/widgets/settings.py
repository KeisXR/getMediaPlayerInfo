"""
Settings widget.

General preferences: theme, language, autostart, notifications,
clipboard template, webhook, Last.fm, and update check.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.i18n import tr, set_language


class SettingsWidget(QWidget):
    """Settings panel."""

    # Emitted when a setting that requires a UI reload is changed (theme/language).
    ui_reload_requested = Signal()
    # Emitted when cache TTL changes so the server can be notified.
    cache_ttl_changed = Signal(int)

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── General ──────────────────────────────────────────────────
        gen_group = QGroupBox(tr("set_general"))
        gen_form = QFormLayout(gen_group)
        gen_form.setHorizontalSpacing(30)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(tr("set_theme_dark"), "dark")
        self._theme_combo.addItem(tr("set_theme_light"), "light")
        self._theme_combo.addItem(tr("set_theme_system"), "system")
        idx = self._theme_combo.findData(self._config.theme)
        self._theme_combo.setCurrentIndex(max(0, idx))
        gen_form.addRow(tr("set_theme") + ":", self._theme_combo)

        # Language
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("日本語", "ja")
        self._lang_combo.addItem("English", "en")
        idx = self._lang_combo.findData(self._config.language)
        self._lang_combo.setCurrentIndex(max(0, idx))
        gen_form.addRow(tr("set_language") + ":", self._lang_combo)

        # Autostart
        self._autostart_cb = QCheckBox(tr("set_autostart"))
        self._autostart_cb.setChecked(self._config.autostart)
        gen_form.addRow("", self._autostart_cb)
        autostart_note = QLabel(tr("set_autostart_note"))
        autostart_note.setObjectName("album_label")
        autostart_note.setWordWrap(True)
        gen_form.addRow("", autostart_note)

        # Close behavior (replaces simple minimize-to-tray checkbox)
        self._close_combo = QComboBox()
        self._close_combo.addItem(tr("set_close_ask"), "ask")
        self._close_combo.addItem(tr("set_close_tray"), "minimize_to_tray")
        self._close_combo.addItem(tr("set_close_quit"), "quit")
        idx = self._close_combo.findData(self._config.close_behavior)
        self._close_combo.setCurrentIndex(max(0, idx))
        gen_form.addRow(tr("set_close_behavior") + ":", self._close_combo)

        # Notifications
        self._notif_cb = QCheckBox(tr("set_notifications"))
        self._notif_cb.setChecked(self._config.notifications_enabled)
        gen_form.addRow("", self._notif_cb)

        root.addWidget(gen_group)

        # ── Clipboard ────────────────────────────────────────────────
        clip_group = QGroupBox(tr("set_clipboard_template"))
        clip_form = QFormLayout(clip_group)
        clip_form.setHorizontalSpacing(30)

        self._clip_edit = QLineEdit(self._config.clipboard_template)
        self._clip_edit.setPlaceholderText("{title} - {artist}")
        clip_form.addRow(tr("set_clipboard_template") + ":", self._clip_edit)
        clip_hint = QLabel("{title}, {artist}, {album}, {source}, {status}")
        clip_hint.setObjectName("album_label")
        clip_form.addRow("", clip_hint)

        root.addWidget(clip_group)

        # ── API / Cache ──────────────────────────────────────────────
        api_group = QGroupBox("API")
        api_form = QFormLayout(api_group)
        api_form.setHorizontalSpacing(30)

        self._cache_ttl_spin = QSpinBox()
        self._cache_ttl_spin.setRange(5, 3600)
        self._cache_ttl_spin.setValue(self._config.cache_ttl)
        self._cache_ttl_spin.setSuffix(" s")
        api_form.addRow(tr("set_cache_ttl") + ":", self._cache_ttl_spin)

        self._poll_spin = QDoubleSpinBox()
        self._poll_spin.setRange(0.5, 60.0)
        self._poll_spin.setSingleStep(0.5)
        self._poll_spin.setValue(self._config.poll_interval)
        self._poll_spin.setSuffix(" s")
        api_form.addRow("Poll interval:", self._poll_spin)

        self._api_autostart_cb = QCheckBox("Auto-start API server on launch")
        self._api_autostart_cb.setChecked(self._config.api_autostart)
        api_form.addRow("", self._api_autostart_cb)

        root.addWidget(api_group)

        # ── Webhook ──────────────────────────────────────────────────
        wh_group = QGroupBox(tr("set_webhook"))
        wh_form = QFormLayout(wh_group)
        wh_form.setHorizontalSpacing(30)

        self._webhook_cb = QCheckBox(tr("set_webhook"))
        self._webhook_cb.setChecked(self._config.webhook_enabled)
        wh_form.addRow("", self._webhook_cb)

        self._webhook_edit = QLineEdit(self._config.webhook_url)
        self._webhook_edit.setPlaceholderText("https://example.com/webhook")
        wh_form.addRow(tr("set_webhook_url") + ":", self._webhook_edit)
        wh_hint = QLabel(tr("set_webhook_hint"))
        wh_hint.setObjectName("album_label")
        wh_hint.setWordWrap(True)
        wh_form.addRow("", wh_hint)

        root.addWidget(wh_group)

        # ── Last.fm ──────────────────────────────────────────────────
        lfm_group = QGroupBox(tr("set_lastfm"))
        lfm_form = QFormLayout(lfm_group)
        lfm_form.setHorizontalSpacing(30)

        self._lfm_cb = QCheckBox(tr("set_lastfm"))
        self._lfm_cb.setChecked(self._config.lastfm_enabled)
        lfm_form.addRow("", self._lfm_cb)

        self._lfm_key_edit = QLineEdit(self._config.lastfm_api_key)
        lfm_form.addRow(tr("set_lastfm_api_key") + ":", self._lfm_key_edit)

        self._lfm_secret_edit = QLineEdit(self._config.lastfm_shared_secret)
        self._lfm_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        lfm_form.addRow(tr("set_lastfm_secret") + ":", self._lfm_secret_edit)

        self._lfm_user_edit = QLineEdit(self._config.lastfm_username)
        lfm_form.addRow(tr("set_lastfm_username") + ":", self._lfm_user_edit)

        self._lfm_session_edit = QLineEdit(self._config.lastfm_session_key)
        self._lfm_session_edit.setEchoMode(QLineEdit.EchoMode.Password)
        lfm_form.addRow(tr("set_lastfm_session_key") + ":", self._lfm_session_edit)

        root.addWidget(lfm_group)

        # ── Save button ──────────────────────────────────────────────
        btn_hl = QHBoxLayout()
        btn_hl.addStretch()
        btn_save = QPushButton(tr("btn_save"))
        btn_save.setObjectName("btn_start")
        btn_save.clicked.connect(self._save)
        btn_hl.addWidget(btn_save)
        root.addLayout(btn_hl)

        root.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self) -> None:
        c = self._config
        old_theme = c.theme
        old_lang = c.language

        c.theme = self._theme_combo.currentData()
        c.language = self._lang_combo.currentData()
        c.autostart = self._autostart_cb.isChecked()
        c.close_behavior = self._close_combo.currentData()
        c.notifications_enabled = self._notif_cb.isChecked()
        c.clipboard_template = self._clip_edit.text().strip() or "{title} - {artist}"
        c.cache_ttl = self._cache_ttl_spin.value()
        c.poll_interval = self._poll_spin.value()
        c.api_autostart = self._api_autostart_cb.isChecked()
        c.webhook_enabled = self._webhook_cb.isChecked()
        c.webhook_url = self._webhook_edit.text().strip()
        c.lastfm_enabled = self._lfm_cb.isChecked()
        c.lastfm_api_key = self._lfm_key_edit.text().strip()
        c.lastfm_shared_secret = self._lfm_secret_edit.text().strip()
        c.lastfm_username = self._lfm_user_edit.text().strip()
        c.lastfm_session_key = self._lfm_session_edit.text().strip()

        c.save()

        if c.autostart:
            self._apply_autostart(True)
        else:
            self._apply_autostart(False)

        if old_theme != c.theme or old_lang != c.language:
            set_language(c.language)
            self.ui_reload_requested.emit()

        self.cache_ttl_changed.emit(c.cache_ttl)

        QMessageBox.information(self, tr("dlg_info"), tr("set_saved"))

    # ------------------------------------------------------------------
    # Autostart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _app_path() -> str:
        """Return the path to the app_entry.py script or the frozen executable."""
        if getattr(sys, "frozen", False):
            return sys.executable
        return str(Path(__file__).parent.parent.parent / "app_entry.py")

    def _apply_autostart(self, enable: bool) -> None:
        system = platform.system()
        try:
            if system == "Windows":
                self._autostart_windows(enable)
            elif system == "Linux":
                self._autostart_linux(enable)
        except Exception as exc:
            QMessageBox.warning(self, tr("dlg_warning"), f"Autostart: {exc}")

    def _autostart_windows(self, enable: bool) -> None:
        import winreg  # type: ignore
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "getMediaPlayerInfo"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE
        ) as reg_key:
            if enable:
                app = self._app_path()
                cmd = f'"{sys.executable}" "{app}"' if not app.endswith(".exe") else f'"{app}"'
                winreg.SetValueEx(reg_key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(reg_key, app_name)
                except FileNotFoundError:
                    pass

    def _autostart_linux(self, enable: bool) -> None:
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / "getMediaPlayerInfo.desktop"
        if enable:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            app = self._app_path()
            exec_cmd = f"{sys.executable} {app}" if not app.endswith(".AppImage") else app
            desktop_file.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=getMediaPlayerInfo Desktop\n"
                f"Exec={exec_cmd}\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            desktop_file.unlink(missing_ok=True)
