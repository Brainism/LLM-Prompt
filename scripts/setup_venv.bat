@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo [1/4] Checking Python launcher...
where py >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher `py` not found. Install Python 3.x from https://www.python.org
  exit /b 1
)

echo [2/4] Creating virtual env (.venv) if missing...
if not exist .venv (
  py -3 -m venv .venv
  if errorlevel 1 goto :err
)

echo [3/4] Activating venv and upgrading pip...
call .\.venv\Scripts\activate
python -m pip install -U pip
if errorlevel 1 goto :err

echo [4/4] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 goto :err

echo.
echo [OK] Environment ready. To activate later:  call .\.venv\Scripts\activate
exit /b 0

:err
echo [FAIL] Error code %errorlevel%
exit /b %errorlevel%