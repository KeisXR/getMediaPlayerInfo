# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for getMediaPlayerInfo Desktop
#
# Build a single self-contained .exe with all dependencies bundled:
#   pip install pyinstaller
#   pyinstaller getMediaPlayerInfo.spec
#
# Output: dist/getMediaPlayerInfo.exe  (Windows)
#         dist/getMediaPlayerInfo      (Linux)

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  (defined by PyInstaller)

# Collect all package data that PyInstaller cannot find automatically
datas = [
    (str(ROOT / "ui" / "styles"), "ui/styles"),
]

# Hidden imports that PyInstaller's static analysis misses
hiddenimports = [
    # FastAPI / Uvicorn
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    # Windows WinRT
    "winrt.windows.media.control",
    "winrt.windows.storage.streams",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    # Provider / app modules
    "providers",
    "providers.base",
    "providers.windows",
    "providers.linux",
    "providers.vrchat",
    "system_info",
    "main",
    "discord_presence",
    "app.config",
    "app.history_manager",
    "app.i18n",
    "app.media_worker",
    "app.server_worker",
    "app.utils",
    "ui.main_window",
    "ui.tray_icon",
    "ui.widgets.now_playing",
    "ui.widgets.history",
    "ui.widgets.provider",
    "ui.widgets.api_server",
    "ui.widgets.discord_tab",
    "ui.widgets.statistics",
    "ui.widgets.settings",
    # pypresence
    "pypresence",
]

block_cipher = None

a = Analysis(
    [str(ROOT / "app_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "tkinter",
        "test",
        "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="getMediaPlayerInfo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app – no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # uncomment and provide icon file
)
