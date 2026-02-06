@echo off
setlocal

cd /d "%~dp0"

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Run the server
echo.
echo Starting Media Player API server...
echo API: http://localhost:8765
echo WebSocket: ws://localhost:8765/ws
echo.
echo Press Ctrl+C to stop
echo.
python main.py

pause
