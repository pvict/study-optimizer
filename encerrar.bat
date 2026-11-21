@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente nao encontrado.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m osler.local_launcher --stop
if errorlevel 1 pause
