@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
	echo Python was not found. Install Python 3.10 or newer, then run this file again.
	pause
	exit /b 1
)

if exist server.log del /q server.log
start "Zorven Backend" /min cmd /c "py -3 server.py > server.log 2>&1"
for /l %%i in (1,1,20) do (
	powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/health -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"
	if not errorlevel 1 goto ready
	timeout /t 1 /nobreak >nul
)

echo Zorven could not start. Check the backend window for the error.
pause
exit /b 1

:ready
start "" http://127.0.0.1:8765/login
endlocal
