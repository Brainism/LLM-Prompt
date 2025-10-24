$txt = @'
# README_for_reviewers

## Purpose
This file explains the minimal steps to reproduce the main example outputs included in `final_package.zip`.

## Environment
- OS: Windows / Linux (tested on Windows PowerShell)
- Python: 3.10+
- Create virtualenv:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1   # PowerShell
  pip install -r requirements.txt