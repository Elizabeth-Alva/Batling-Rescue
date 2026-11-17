@echo off
rem Construye la aplicacion de escritorio: dist\BatlingRescue.exe (se abre con doble clic, sin instalar Python)
cd /d "%~dp0"
where python >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% -m pip install -r requirements.txt pyinstaller pillow
%PY% tools\build_exe.py
if exist dist\BatlingRescue.exe start "" explorer dist
pause
