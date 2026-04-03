"""
getMediaPlayerInfo Desktop – GUI entry point.

Usage:
    python app_entry.py [--no-tray] [--light] [--dark] [--lang en|ja]

This file starts the PySide6 application, loads saved configuration,
initialises the main window (which also spins up the embedded API server),
and enters the Qt event loop.
"""
from __future__ import annotations

import argparse
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="getMediaPlayerInfo Desktop – GUI application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app_entry.py                 # Start with saved settings
  python app_entry.py --light         # Force light theme
  python app_entry.py --lang en       # Force English UI
  python app_entry.py --no-tray       # Disable system tray
""",
    )
    parser.add_argument("--light", action="store_true", help="Force light theme")
    parser.add_argument("--dark", action="store_true", help="Force dark theme")
    parser.add_argument("--lang", choices=["ja", "en"], help="UI language")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray icon")
    parser.add_argument("--minimized", action="store_true", help="Start minimized to tray")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    # PySide6 must be imported after sys.argv is ready
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QCoreApplication
        from PySide6.QtGui import QFont
    except ImportError:
        print(
            "Error: PySide6 is not installed.\n"
            "Install it with:  pip install -r requirements-gui.txt",
            file=sys.stderr,
        )
        return 1

    # High-DPI support (Qt6 handles this automatically, but explicit is clearer)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("getMediaPlayerInfo Desktop")
    app.setApplicationDisplayName("getMediaPlayerInfo Desktop")
    app.setOrganizationName("KeisXR")

    # Use the native system font for crisp rendering on every platform.
    # On Windows this gives Segoe UI; on Linux the GTK/KDE default; on macOS SF Pro.
    import platform as _plat
    _sys = _plat.system()
    if _sys == "Windows":
        app.setFont(QFont("Segoe UI", 10))
    elif _sys == "Darwin":
        app.setFont(QFont("SF Pro Text", 13))
    # Linux: leave Qt to pick the system font automatically

    # Prevent the app from quitting when the last window is hidden (tray mode)
    app.setQuitOnLastWindowClosed(False)

    # Load configuration
    from app.config import AppConfig
    from app.history_manager import HistoryManager
    from app.i18n import set_language

    config = AppConfig.load()

    # CLI overrides
    if args.light:
        config.theme = "light"
    elif args.dark:
        config.theme = "dark"

    if args.lang:
        config.language = args.lang

    if args.minimized:
        config.start_minimized = True

    if args.no_tray:
        config.close_behavior = "quit"

    set_language(config.language)

    history = HistoryManager()

    # Create and show main window
    from ui.main_window import MainWindow

    window = MainWindow(config, history)
    if not config.start_minimized:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
