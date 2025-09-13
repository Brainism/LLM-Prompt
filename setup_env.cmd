@echo off
REM safe_setup_env.cmd - create venv only if missing; otherwise activate and install deps (for cmd)

REM If .venv exists, skip creation
if exist .venv (
  echo .venv already exists. Activating...
  call .venv\Scripts\activate
) else (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo ERROR: Failed to create virtual environment. Try running this script as Administrator, or check that no files are locked.
    exit /b 1
  )
  call .venv\Scripts\activate
)

echo Virtual environment active: %VIRTUAL_ENV%

echo Upgrading pip...
python -m pip install --upgrade pip

if exist requirements.txt (
  echo Installing requirements from requirements.txt ...
  pip install -r requirements.txt
) else (
  echo WARNING: requirements.txt not found in repo root.
)

echo Checking key files:
if exist docs\paper\appendix\README_repro.md ( echo OK: docs\paper/appendix/README_repro.md found ) else ( echo MISSING: docs\paper/appendix/README_repro.md )
if exist figs\aggregated_metrics_fixed_with_chrf_rouge.csv ( echo OK: figs CSV found ) else ( echo MISSING: figs\aggregated_metrics_fixed_with_chrf_rouge.csv )

echo Setup complete. venv should be active in this cmd session.
pause