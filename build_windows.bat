@echo off
REM Build getMediaPlayerInfo Desktop as a single Windows executable
REM Requirements: Python 3.10+, all packages from requirements-gui.txt
REM
REM Usage:
REM   1. Open this folder in a terminal (PowerShell / cmd)
REM   2. Run:  build_windows.bat
REM   3. The output is:  dist\getMediaPlayerInfo.exe

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements-gui.txt >nul 2>&1
python -m pip install pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python 3.10+ is in PATH.
    exit /b 1
)

echo [2/3] Building executable...
python -m PyInstaller --clean getMediaPlayerInfo.spec
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed. See output above.
    exit /b 1
)

echo [3/3] Done!
echo.
echo Output: dist\getMediaPlayerInfo.exe
echo.
pause
