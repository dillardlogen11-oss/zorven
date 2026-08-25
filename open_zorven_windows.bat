@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 or newer is required.
    echo Install Python, then run this file again.
    pause
    exit /b 1
)

set "SETUP_KEY=%SETUP_KEY%"
if "%SETUP_KEY%"=="" set "SETUP_KEY=Zorven-Setup-2026-Alpha-7f9d2c1e-Q7R9xM2k"

start "" http://127.0.0.1:8765/login
py -3 zorven/server.py

endlocal
