@echo off
setlocal EnableDelayedExpansion

REM

echo [1/5] Generate raw (general) ...
python code\run_langchain_experiment.py --prompt-file prompts\prompts.csv --prompt-column input --id-column id --mode general --provider ollama --model gemma:7b --outdir results\raw || goto :error

echo [2/5] Generate raw (instructed) ...
python code\run_langchain_experiment.py --prompt-file prompts\prompts.csv --prompt-column input --id-column id --mode instructed --provider ollama --model gemma:7b-instruct --outdir results\raw || goto :error

echo [3/5] Align refs/hyps ...
python code\aligned_texts.py || goto :error

echo [4/5] Metrics (BLEU/chrF/ROUGE) ...
python code\sacre_eval.py ^
  --refs results\aligned\refs.txt ^
  --hyps-general results\aligned\general.txt ^
  --hyps-instructed results\aligned\instructed.txt ^
  --out-bleu results\quantitative\bleu_sacre.json ^
  --out-chrf results\quantitative\chrf.json ^
  --out-rouge results\quantitative\rouge.json || goto :error

echo [5/5] Stats (bootstrap/Wilcoxon/FDR) ...
python code\stats_tests_plus.py ^
  --bleu results\quantitative\bleu_sacre.json ^
  --chrf results\quantitative\chrf.json ^
  --rouge results\quantitative\rouge.json ^
  --output results\quantitative\stats_summary.csv ^
  --bootstrap 10000 --wilcoxon --fdr || goto :error

echo DONE
goto :eof

:error
echo ERROR at step above. ExitCode=%ERRORLEVEL%
exit /b %ERRORLEVEL%