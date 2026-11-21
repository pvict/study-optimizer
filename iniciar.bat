@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente nao encontrado. Execute instalar.bat primeiro.
  pause
  exit /b 1
)
echo Abrindo Osler... aguarde o navegador.
".venv\Scripts\python.exe" -m osler.local_launcher
if errorlevel 1 pause
