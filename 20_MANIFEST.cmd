@echo off
setlocal EnableExtensions
cd /d C:\Project\LLM
call .\.venv\Scripts\activate

if not exist data\candidates.csv (
  echo [ERR] missing data\candidates.csv
  exit /b 1
)
if not exist schema\split_manifest_main.schema.json (
  echo [ERR] missing schema\split_manifest_main.schema.json
  exit /b 1
)

python -X utf8 scripts\make_n50_manifest.py --candidates data\candidates.csv --out data\manifest\split_manifest_main.json --n 50 --seed 42
if errorlevel 1 exit /b 1

python -X utf8 scripts\validate_manifest.py --manifest data\manifest\split_manifest_main.json --schema schema\split_manifest_main.schema.json
if errorlevel 1 exit /b 1

echo [OK] manifest ready