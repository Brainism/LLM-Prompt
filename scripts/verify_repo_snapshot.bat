@echo off
SETLOCAL ENABLEEXTENSIONS

REM ===== verify_repo_snapshot.bat =====
REM Usage: double-click or run from anywhere.
REM It assumes the repo root is C:\Project\LLM. Edit ROOT below if needed.

set "ROOT=C:\Project\LLM"
set "TAG=v0.2-recalc"

echo.
echo [verify] Repo: %ROOT%
cd /d "%ROOT%" || (echo [ERROR] Cannot cd to %ROOT% & exit /b 1)

echo.
echo [1/3] Tag check: %TAG%
git fetch --tags >nul 2>&1

set "HAS_LOCAL="
for /f "delims=" %%A in ('git tag -l %TAG%') do set "HAS_LOCAL=1"
if defined HAS_LOCAL (echo   ✓ Local tag exists: %TAG%) else (echo   ✗ Local tag NOT found: %TAG%)

set "HAS_REMOTE="
for /f "delims=" %%A in ('git ls-remote --tags origin %TAG%') do set "HAS_REMOTE=1"
if defined HAS_REMOTE (echo   ✓ Remote tag on origin: %TAG%) else (echo   ✗ Remote tag NOT found on origin: %TAG%)

for /f %%A in ('git rev-parse HEAD') do set "HEAD_SHA=%%A"
for /f %%A in ('git rev-list -n 1 %TAG% 2^>nul') do set "TAG_SHA=%%A"

if not "%TAG_SHA%"=="" (
  if /I "%TAG_SHA%"=="%HEAD_SHA%" (
    echo   ✓ Tag points to HEAD: %TAG_SHA%
  ) else (
    echo   ⚠ Tag points to %TAG_SHA% (HEAD is %HEAD_SHA%)
  )
) else (
  echo   (skip) Tag SHA unknown
)

echo.
echo [2/3] Last commit contains required paths?
git show --pretty="" --name-only HEAD > "%TEMP%\_changed_files.txt"

call :_check_path "results\quantitative\rouge_scores.json"
call :_check_path "results\stats_summary.csv"
call :_check_path "results\figures\summary_tile.png"
REM Optional: directory presence (any file under figures changed)
findstr /I /C:"results\figures\" "%TEMP%\_changed_files.txt" >nul && (
  echo   ✓ figures directory updated (some file under results\figures\ changed)
) || (
  echo   ◻ figures directory not updated in last commit (ok if not expected)
)

echo.
echo [3/3] .gitignore exception for figures?
findstr /C:"!results/figures/" .gitignore >nul && (
  echo   ✓ .gitignore has '!results/figures/' (no need to force-add next time)
) || (
  echo   ◻ Consider adding this line to .gitignore: !results/figures/
)

echo.
echo Done.
exit /b 0

:_check_path
set "P=%~1"
findstr /I /X /C:"%P%" "%TEMP%\_changed_files.txt" >nul || findstr /I /C:"%P%" "%TEMP%\_changed_files.txt" >nul
if errorlevel 1 (
  echo   ✗ missing in last commit: %P%
) else (
  echo   ✓ included in last commit: %P%
)
exit /b 0
