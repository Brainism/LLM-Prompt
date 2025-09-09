@echo off
REM -------------------------------------------------------------------
REM run_full_pipeline.cmd
REM Windows (cmd) batch script for the full LLM pipeline on C:\Project\LLM
REM Designed for: VS Code integrated terminal or plain cmd.exe
REM Saves recent commands to recent_commands.txt and prints progress.
REM -------------------------------------------------------------------

SETLOCAL ENABLEDELAYEDEXPANSION

:: ------------------ Editable settings (change if needed) ------------------
set REPO_ROOT=C:\Project\LLM
set VENV_ACTIVATE=%REPO_ROOT%\.venv\Scripts\activate.bat

:: prompts/manifest paths
set PROMPTS=%REPO_ROOT%\prompts\main.csv
set MANIFEST=%REPO_ROOT%\split_manifest.json

:: outputs
set GENERAL_OUT=%REPO_ROOT%\results\raw\general.jsonl
set INSTRUCTED_OUT=%REPO_ROOT%\results\raw\instructed.jsonl
set METRICS_CSV=%REPO_ROOT%\results\quantitative\metrics_per_item.csv
set METRICS_JSON=%REPO_ROOT%\results\quantitative\metrics_per_item.json
set PASS_METRIC=%REPO_ROOT%\results\quantitative\pass_metric.json
set LCS_METRIC=%REPO_ROOT%\results\quantitative\lcs_metric.json
set STATS_PASS=%REPO_ROOT%\tables\stats_pass.csv
set STATS_LCS=%REPO_ROOT%\tables\stats_lcs.csv
set RECENT=%REPO_ROOT%\recent_commands.txt
set LOGFILE=%REPO_ROOT%\run_full_pipeline.log

:: Ollama / model options
set MODEL=gemma:7b

:: Network / timeout / retries tunables
set TIMEOUT_SECONDS=120
set RETRIES=2

:: Use Ollama CLI? set to 1 to use --use-cli, 0 to use HTTP (requires requests & running HTTP API)
set USE_CLI=1

:: Python encoding - ensure UTF-8 in subprocesses
set PYTHONIOENCODING=utf-8
:: -------------------------------------------------------------------------

cd /d "%REPO_ROOT%" || (echo ERROR: cannot cd to %REPO_ROOT% & exit /b 1)

echo ---------- Pipeline started at %DATE% %TIME% ----------> "%RECENT%"
echo start_time=%DATE% %TIME% >> "%LOGFILE%"

:: activate venv
if exist "%VENV_ACTIVATE%" (
  call "%VENV_ACTIVATE%"
  if errorlevel 1 ( echo ERROR: failed to activate venv & exit /b 1 )
) else (
  echo ERROR: virtualenv activate not found at %VENV_ACTIVATE% & exit /b 1
)

:: ensure output dirs exist
if not exist "%REPO_ROOT%\results\raw" mkdir "%REPO_ROOT%\results\raw"
if not exist "%REPO_ROOT%\results\quantitative" mkdir "%REPO_ROOT%\results\quantitative"
if not exist "%REPO_ROOT%\tables" mkdir "%REPO_ROOT%\tables"

:: build common options for infer_via_ollama.py
set COMMON_OPTS=--model %MODEL% --timeout %TIMEOUT_SECONDS% --retries %RETRIES%

if "%USE_CLI%"=="1" (
  set CLI_FLAG=--use-cli
) else (
  set CLI_FLAG=
)

:: Helper function: echo+append command
:log_cmd
  echo %* >> "%RECENT%"
  echo %* >> "%LOGFILE%"
  goto :eof

:: ---------------- 1) Run inference (general) ----------------
echo.
echo === Running inference (general) ===
if exist "%PROMPTS%" (
  call :log_cmd python scripts\infer_via_ollama.py --prompt-file "%PROMPTS%" --mode general %COMMON_OPTS% %CLI_FLAG% --out "%GENERAL_OUT%"
  python scripts\infer_via_ollama.py --prompt-file "%PROMPTS%" --mode general %COMMON_OPTS% %CLI_FLAG% --out "%GENERAL_OUT%"
) else (
  if exist "%MANIFEST%" (
    call :log_cmd python scripts\infer_via_ollama.py --manifest "%MANIFEST%" --mode general %COMMON_OPTS% %CLI_FLAG% --out "%GENERAL_OUT%"
    python scripts\infer_via_ollama.py --manifest "%MANIFEST%" --mode general %COMMON_OPTS% %CLI_FLAG% --out "%GENERAL_OUT%"
  ) else (
    echo ERROR: neither prompts CSV nor manifest found. Expect %PROMPTS% or %MANIFEST% & exit /b 1
  )
)
if errorlevel 1 ( echo ERROR: general inference failed & exit /b 1 )

:: ---------------- 2) Run inference (instructed) ----------------
echo.
echo === Running inference (instructed) ===
if exist "%PROMPTS%" (
  call :log_cmd python scripts\infer_via_ollama.py --prompt-file "%PROMPTS%" --mode instructed %COMMON_OPTS% %CLI_FLAG% --out "%INSTRUCTED_OUT%"
  python scripts\infer_via_ollama.py --prompt-file "%PROMPTS%" --mode instructed %COMMON_OPTS% %CLI_FLAG% --out "%INSTRUCTED_OUT%"
) else (
  call :log_cmd python scripts\infer_via_ollama.py --manifest "%MANIFEST%" --mode instructed %COMMON_OPTS% %CLI_FLAG% --out "%INSTRUCTED_OUT%"
  python scripts\infer_via_ollama.py --manifest "%MANIFEST%" --mode instructed %COMMON_OPTS% %CLI_FLAG% --out "%INSTRUCTED_OUT%"
)
if errorlevel 1 ( echo ERROR: instructed inference failed & exit /b 1 )

:: ---------------- 3) Aggregate metrics ----------------
echo.
echo === Aggregating metrics ===
call :log_cmd python scripts\metrics_aggregate.py --prompts "%PROMPTS%" --general "%GENERAL_OUT%" --instructed "%INSTRUCTED_OUT%" --out_csv "%METRICS_CSV%" --out_json "%METRICS_JSON%"
python scripts\metrics_aggregate.py --prompts "%PROMPTS%" --general "%GENERAL_OUT%" --instructed "%INSTRUCTED_OUT%" --out_csv "%METRICS_CSV%" --out_json "%METRICS_JSON%"
if errorlevel 1 ( echo ERROR: metrics_aggregate failed & exit /b 1 )

:: ---------------- 4) Convert metrics -> stats JSONs ----------------
echo.
echo === Preparing metric JSONs for stats ===
call :log_cmd python scripts\metrics_to_stats_json.py --metrics_json "%METRICS_JSON%" --metric pass --out "%PASS_METRIC%"
python scripts\metrics_to_stats_json.py --metrics_json "%METRICS_JSON%" --metric pass --out "%PASS_METRIC%"
if errorlevel 1 ( echo ERROR: metrics_to_stats_json (pass) failed & exit /b 1 )

call :log_cmd python scripts\metrics_to_stats_json.py --metrics_json "%METRICS_JSON%" --metric lcs_ratio --out "%LCS_METRIC%"
python scripts\metrics_to_stats_json.py --metrics_json "%METRICS_JSON%" --metric lcs_ratio --out "%LCS_METRIC%"
if errorlevel 1 ( echo ERROR: metrics_to_stats_json (lcs) failed & exit /b 1 )

:: ---------------- 5) Statistical tests ----------------
echo.
echo === Running statistical tests (lcs) ===
call :log_cmd python scripts\stats_tests_unified.py --chrf "%LCS_METRIC%" --bootstrap 10000 --wilcoxon --fdr --output "%STATS_LCS%"
python scripts\stats_tests_unified.py --chrf "%LCS_METRIC%" --bootstrap 10000 --wilcoxon --fdr --output "%STATS_LCS%"
if errorlevel 1 ( echo ERROR: stats_tests_unified (lcs) failed & exit /b 1 )

echo.
echo === Running statistical tests (pass) ===
call :log_cmd python scripts\stats_tests_unified.py --chrf "%PASS_METRIC%" --bootstrap 10000 --wilcoxon --fdr --output "%STATS_PASS%"
python scripts\stats_tests_unified.py --chrf "%PASS_METRIC%" --bootstrap 10000 --wilcoxon --fdr --output "%STATS_PASS%"
if errorlevel 1 ( echo ERROR: stats_tests_unified (pass) failed & exit /b 1 )

:: ---------------- Optional: basic checks ----------------
echo.
echo === Quick checks: listing outputs and head of CSV ===
call :log_cmd dir "%REPO_ROOT%\results\quantitative\metrics_per_item.*" "%REPO_ROOT%\tables\stats_*.csv"
dir "%REPO_ROOT%\results\quantitative\metrics_per_item.*" "%REPO_ROOT%\tables\stats_*.csv"

echo.
echo ----- Pipeline completed at %DATE% %TIME% ----- >> "%RECENT%"
echo end_time=%DATE% %TIME% >> "%LOGFILE%"
echo Pipeline completed successfully.
exit /b 0