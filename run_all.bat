@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 0) venv
if not exist .venv (
  py -m venv .venv
)
call .\.venv\Scripts\activate
python -m pip install --upgrade pip >nul 2>&1

REM 1) 디렉터리
if not exist results\raw\v2 mkdir results\raw\v2
if not exist results\quantitative mkdir results\quantitative
if not exist tables mkdir tables
if not exist figs mkdir figs
if not exist docs mkdir docs
if not exist configs mkdir configs

REM 2) 매니페스트 검증 + 프롬프트 생성
python scripts\validate_manifest.py --manifest data\manifest\split_manifest_main.json --schema schema\split_manifest_main.schema.json --max-errors 200 || goto :err
python code\canonize_raw_to_prompts.py --manifest data\manifest\split_manifest_main.json --out prompts\main.csv || goto :err

REM 3) 추론(v2, 겹침 방지)
python code\run_langchain_experiment.py --prompt-file prompts\main.csv --mode general    --outdir results\raw\v2 --provider ollama --model gemma:7b --temperature 0.0 --overwrite || goto :err
python code\run_langchain_experiment.py --prompt-file prompts\main.csv --mode instructed --outdir results\raw\v2 --provider ollama --model gemma:7b --temperature 0.0 --overwrite || goto :err

REM 4) 품질 지표(집계)
python code\metrics_sacre.py --inputs results\raw\v2 --out results\quantitative\bleu_chrf.v2.json --prompts prompts\main.csv --by-file || goto :err
python code\rouge_eval.py    --inputs results\raw\v2 --out results\quantitative\rouge_scores.v2.json --prompts prompts\main.csv --by-file || goto :err

REM 5) 컴플라이언스
python code\compliance_check.py --mode heuristic --raw-dir results\raw\v2 --apply-from prompts\main.csv --forbid-terms rules\forbidden_terms.txt --out results\quantitative\compliance_summary.v2.csv || goto :err
python code\compliance_check.py --mode cvd       --inputs  results\raw\v2 --forbid rules\forbidden_terms.txt --schema rules\schema\output.schema.json --out results\quantitative\compliance_cvd.v2.csv || goto :err

REM 6) 지연 요약
python code\make_latency_summary.py --inputs results\raw\v2 --out results\quantitative\latency_summary.v2.csv || goto :err

REM 7) 통계용 per-id 지표 생성 (from raw v2)
python scripts\make_item_metrics_from_raw.py --prompts prompts\main.csv --gen results\raw\v2\general.jsonl --ins results\raw\v2\instructed.jsonl --outdir results\quantitative || goto :err

REM 8) 통계 요약(BH-FDR 포함)
python scripts\stats_from_items.py --rouge results\quantitative\rouge.json --bleu results\quantitative\bleu_sacre.json --chrf results\quantitative\chrf.json --out results\quantitative\stats_summary.v2.csv || goto :err

REM 9) 표/그림 산출 (tables/*, figs/*)
python scripts\export_tables_and_figs.py || goto :err

REM 10) 환경표 갱신
python scripts\capture_env.py || goto :err

REM 11) 청소 (찌꺼기 파일 제거)
powershell -NoP -C "Get-ChildItem -File -Recurse | Where-Object { $_.Name -match '^(0|1)$' -or $_.Name -match '\[' -or $_.Name -in @('bool','int','float','str','None','Dict','Tuple','np.ndarray','List[Path]','List[str]') } | Remove-Item -Force"

echo.
echo [OK] ALL DONE
exit /b 0

:err
echo.
echo [ERR] FAILED with code %ERRORLEVEL%
exit /b %ERRORLEVEL%