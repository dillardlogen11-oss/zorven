@echo off
cd /d "%~dp0"
set "API_HOST=%~1"
if "%API_HOST%"=="" set "API_HOST=http://127.0.0.1:8765"
start "Zorven Backend" python server.py
ping 127.0.0.1 -n 2 > nul
python desktop_app.py --host "%API_HOST%"
