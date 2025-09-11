@echo off
setlocal EnableExtensions
cd /d C:\Project\LLM
call .\.venv\Scripts\activate

if not exist data\manifest\split_manifest_main.json (
  echo [ERR] missing data\manifest\split_manifest_main.json
  exit /b 1
)

python -X utf8 scripts\manifest_to_prompts.py --manifest data\manifest\split_manifest_main.json --out prompts\main.csv
if errorlevel 1 exit /b 1

echo [OK] prompts\main.csv created