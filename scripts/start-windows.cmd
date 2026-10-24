@echo off
cd /d "%~dp0.."
where py >nul 2>nul
if errorlevel 1 (
 echo Python 3.11 veya daha yeni bir surum kurun: https://www.python.org/downloads/windows/
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
.venv\Scripts\python.exe -m server.app
pause
