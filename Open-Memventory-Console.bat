@echo off
REM Open the live Memventory console. Refresh rebuilds the local index and reloads
REM the same browser page. Close the minimized server window to stop it.
cd /d "%~dp0"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )
if not defined PY (
  echo Python was not found on PATH.
  echo Install Python, then reopen this console.
  pause
  exit /b 1
)

start "Memventory Console" /min %PY% serve-second-brain.py
