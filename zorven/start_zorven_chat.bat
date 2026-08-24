@echo off
cd /d "%~dp0"
start "Zorven Backend" python server.py
ping 127.0.0.1 -n 2 > nul
python desktop_app.py
