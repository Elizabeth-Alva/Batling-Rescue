@echo off
cd /d "%~dp0"
where python >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% -m pip install -r requirements.txt
%PY% murcielago_cueva.py
pause
