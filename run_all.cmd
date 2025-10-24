@echo off
REM run_all.cmd - run recompute_stats, generate figs, make top/bottom CSVs
call .venv\Scripts\activate

REM Set reproducibility seed
set SEED=42

REM 1) Recompute robust stats (if script exists)
if exist tools\recompute_stats.py (
  echo Running recompute_stats.py ...
  python tools\recompute_stats.py --per_item "LLM-clean\results\quantitative\per_item_full_60.csv" --nboot 10000 --out analysis_outputs\recomputed_stats.json
) else (
  echo SKIP: tools\recompute_stats.py not found.
)

REM 2) Generate figures (use high quality)
if exist tools\generate_highperf_figs.py (
  echo Generating figures (normal) ...
  python tools\generate_highperf_figs.py --stats_csv "LLM-clean\results\quantitative\stats_summary.v2.csv" --bleu_json "LLM-clean\results\quantitative\bleu_sacre.json" --comp_csv "figs\compliance_by_scenario.csv" --error_html "figs\error_board.html" --out "figs" --nboot 5000
  echo Generating high-res figures ...
  python tools\generate_highperf_figs.py --stats_csv "LLM-clean\results\quantitative\stats_summary.v2.csv" --bleu_json "LLM-clean\results\quantitative\bleu_sacre.json" --comp_csv "figs\compliance_by_scenario.csv" --error_html "figs\error_board.html" --out "figs_highres" --nboot 5000 --dpi 300
) else (
  echo SKIP: tools\generate_highperf_figs.py not found.
)

REM 3) Create top10 / bottom10 CSVs using our helper python
if exist scripts\make_top_bottom.py (
  echo Creating top10/bottom10 CSVs ...
  python scripts\make_top_bottom.py --aggregated "figs\aggregated_metrics_fixed_with_chrf_rouge.csv" --out_dir "docs\paper\tables"
) else (
  echo ERROR: scripts\make_top_bottom.py not found. Please create it from provided template.
  exit /b 1
)

echo RUN_ALL finished.
pause
