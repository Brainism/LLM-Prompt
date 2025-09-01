@echo on
setlocal
cd /d %~dp0
chcp 65001 >nul
set PYTHONUTF8=1

echo [STEP0] activate venv
if not exist .\.venv\Scripts\activate.bat (
  echo [ERR] .venv not found. Create it:  py -3.11 -m venv .venv
  pause
  exit /b 1
)
call .\.venv\Scripts\activate

echo [STEP1] fix manifest fields
python scripts\fix_manifest_fields_v3.py data\manifest\split_manifest_main.json --inplace --add-prompt-hash --auto-len-bin || goto :fail

echo [STEP2] validate manifest
python scripts\validate_manifest.py --manifest data\manifest\split_manifest_main.json --schema schema\split_manifest_main.schema.json --max-errors 50 || goto :fail

echo [STEP3] stats summary
python code\stats_tests_plus.py --bleu results\quantitative\bleu_sacre.json --chrf results\quantitative\chrf.json --rouge results\quantitative\rouge.json --output results\quantitative\stats_summary.csv --bootstrap 10000 --wilcoxon --fdr || goto :fail

echo [STEP4] compliance viz
python code\compliance_viz.py || goto :fail

echo [OK] run_all completed.
pause
endlocal
goto :eof

:fail
echo [FAIL] run_all aborted. ErrorLevel=%ERRORLEVEL%
pause
endlocal & exit /b 1
