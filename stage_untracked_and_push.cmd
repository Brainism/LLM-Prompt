@echo off
REM stage_untracked_and_push.cmd
REM Adds only untracked files (excluding .gitignore), commits, and pushes to current branch.

REM 0) ensure in repo root
if not exist .git (
  echo ERROR: Not a git repository (no .git). cd to repository root.
  exit /b 1
)

REM 1) get current branch
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if "%BRANCH%"=="" set "BRANCH=main"
echo Current branch: %BRANCH%

REM 2) create list of untracked files (excluding ignored)
git ls-files --others --exclude-standard > untracked_list.txt
if not exist untracked_list.txt (
  echo No untracked files found.
  exit /b 0
)
for /f "usebackq delims=" %%f in ("untracked_list.txt") do set /a COUNT+=1
if "%COUNT%"=="0" (
  echo No untracked files found.
  del untracked_list.txt 2>nul
  exit /b 0
)

echo Found %COUNT% untracked files. Listing first 50:
powershell -Command "Get-Content .\untracked_list.txt -TotalCount 50"

REM 3) Add each untracked file (handles spaces)
echo.
echo Adding untracked files...
for /f "usebackq delims=" %%f in ("untracked_list.txt") do (
  echo git add "%%f"
  git add "%%f"
  if errorlevel 1 (
    echo WARNING: failed to add %%f
  )
)

REM 4) Commit (skip if nothing to commit)
git diff --cached --name-only > staged_list.txt
if not exist staged_list.txt (
  echo Nothing staged.
  exit /b 0
)
for /f "usebackq delims=" %%g in ("staged_list.txt") do set /a STAGED+=1
if "%STAGED%"=="0" (
  echo Nothing staged to commit.
  del staged_list.txt untracked_list.txt 2>nul
  exit /b 0
)

set COMMIT_MSG=chore: add untracked files (from VSCode)
echo Committing %STAGED% files with message: "%COMMIT_MSG%"
git commit -m "%COMMIT_MSG%"

if errorlevel 1 (
  echo Commit failed. See output above.
  exit /b 1
)

REM 5) Push to origin <branch>
echo Pushing to origin/%BRANCH% ...
git push -u origin %BRANCH%
if errorlevel 1 (
  echo Push failed. You may need to set upstream or resolve conflicts.
  exit /b 1
)

echo DONE: untracked files added, committed and pushed.
del untracked_list.txt staged_list.txt 2>nul
pause