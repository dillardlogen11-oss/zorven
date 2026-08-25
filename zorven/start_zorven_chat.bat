@echo off
cd /d "%~dp0"
set "API_HOST=%~1"
if "%API_HOST%"=="" set "API_HOST=http://127.0.0.1:8765"

where py >nul 2>&1
if errorlevel 1 (
echo Python was not found. Install Python 3.10 or newer, then run this file again.
pause
exit /b 1
)

start "Zorven Backend" cmd /c "py -3 server.py"
ping 127.0.0.1 -n 2 > nul
py -3 desktop_app.py --host "%API_HOST%"