@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Installation (une seule fois)...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
.venv\Scripts\python nettoyage.py
pause
