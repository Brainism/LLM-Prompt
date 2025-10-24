@echo off
REM 백업 브랜치는 수동으로 생성 권장(또는 아래 주석 제거하고 자동 생성)
:: git checkout -b cleanup-backup-20250912
:: git push -u origin cleanup-backup-20250912

mkdir archived_outputs 2>nul
move results archived_outputs\results 2>nul
move run_full_pipeline.log archived_outputs\ 2>nul
git rm -r --cached results
git add .gitignore
git commit -m "chore: move results to archived_outputs and update gitignore"
git push
echo DONE