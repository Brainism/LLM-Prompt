@echo off
setlocal ENABLEEXTENSIONS DISABLEDELAYEDEXPANSION
if not exist logs mkdir logs

REM ← 꼭 이 괄호 안에만 멀티라인 명령을 넣고,
REM    리다이렉션은 괄호 밖에서 "딱 한 번"만!
(
  python code\sacre_eval.py ^
    --refs reference\reference_corpus.jsonl ^
    --hyps-general results\batch_outputs\general.jsonl ^
    --hyps-instructed results\batch_outputs\instructed.jsonl

  python code\stats_tests_unified.py ^
    --bootstrap 10000 --wilcoxon --fdr ^
    --output results\quantitative\stats_summary.csv
) > logs\pipeline.out 2> logs\pipeline.err

echo [OK] done. Logs: logs\pipeline.out / logs\pipeline.err
endlocal
