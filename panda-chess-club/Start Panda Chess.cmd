@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe main.py
  goto done
)
where py >nul 2>nul
if errorlevel 1 (
  python main.py
) else (
  py -3 main.py
)
:done
if errorlevel 1 (
  echo Requires Python 3.10+ and NumPy. Install using your Python: python -m pip install -r requirements.txt
  pause
)
