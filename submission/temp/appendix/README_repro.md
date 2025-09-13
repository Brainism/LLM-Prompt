# Repro README (for submission)

Environment:
- OS: Windows (tested)
- Python: 3.11 (use virtualenv .venv)
- Packages: see requirements.txt (pip freeze in repo)
- Key packages: pandas, numpy, scipy, matplotlib, sacrebleu

Reproduction steps:
1. Activate env:
   > .venv\Scripts\Activate.ps1   (PowerShell)
   or
   > .venv\Scripts\activate      (cmd)

2. Install dependencies:
   > python -m pip install -r requirements.txt

3. Generate figures:
   > python tools\generate_highperf_figs.py --stats_csv "LLM-clean\results\quantitative\stats_summary.v2.csv" --bleu_json "LLM-clean\results\quantitative\bleu_sacre.json" --comp_csv "figs\compliance_by_scenario.csv" --error_html "figs\error_board.html" --out "figs" --nboot 5000

4. Recompute robust stats:
   > python tools\recompute_stats.py --per_item "LLM-clean\results\quantitative\per_item_full_60.csv" --nboot 10000

5. Human eval analysis (if annotations available):
   > python tools\human_eval_analysis.py --csv human_eval_annotation_template_filled.csv --out analysis_outputs/human_eval/results.json

Random seeds:
- bootstrap seed: default (set by scripts to fixed value if needed). If reproducibility requested, set environment variable SEED=42 and re-run scripts.

Files included in submission:
- figs/*.png
- per_item_table.csv
- analysis_outputs/*.json / .txt
- final_package.zip and checksums.txt