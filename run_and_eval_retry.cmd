@echo off
REM usage: run_and_eval_retry.cmd EX-0049
if "%1"=="" (
  echo Usage: run_and_eval_retry.cmd EX-XXXX
  exit /b 1
)
set ID=%1
set OUT=results\raw\retry_general_%ID%.jsonl

echo Filtering prompts and running inference for %ID% ...
python retry_scripts\retry_selected_v2.py --ids %ID% --prompt-file prompts\main.csv --out %OUT% --mode general --model gemma:7b --use-cli --timeout 600
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] retry_selected_v2.py failed with exit code %ERRORLEVEL%.
  exit /b %ERRORLEVEL%
)

echo Inference finished. Running m3_eval...
python scripts\m3_eval.py --outputs %OUT% --manifest data/manifest/split_manifest_main.json --references data/raw/references/references.jsonl --run_name retry_%ID%
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] m3_eval.py failed with exit code %ERRORLEVEL%.
  exit /b %ERRORLEVEL%
)

echo Done.