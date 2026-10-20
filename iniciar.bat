@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente nao encontrado. Execute instalar.bat primeiro.
  pause
  exit /b 1
)
echo Abrindo Osler Study Optimizer em http://127.0.0.1:8501
echo Para encerrar, pressione Ctrl+C nesta janela.
start "" "http://127.0.0.1:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause
