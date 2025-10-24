import csv
import json
from pathlib import Path

PROMPTS_CSV = Path("prompts/main.csv")
METRIC_FILES = [
    Path("results/quantitative/bleu_sacre.json"),
    Path("results/quantitative/rouge.json"),
    Path("results/quantitative/chrf.json"),
]

def load_prompt_ids(p_csv):
    if not p_csv.exists():
        raise FileNotFoundError(f"Prompts file not found: {p_csv}")
    with p_csv.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    ids = [r[0] for r in rows[1:] if r]
    return ids

def inspect_metrics(prompt_ids, metric_paths):
    prompt_set = set(prompt_ids)
    for mp in metric_paths:
        if not mp.exists():
            print(f"{mp}  -> MISSING")
            continue
        try:
            data = json.load(mp.open(encoding="utf-8"))
        except Exception as e:
            print(f"{mp}  -> ERROR loading: {e!r}")
            continue
        metric_ids = [item.get("id") for item in data if isinstance(item, dict)]
        inter = prompt_set & set(metric_ids)
        missing = sorted(set(prompt_ids) - set(metric_ids))
        print(f"{mp}  total_metric_ids={len(metric_ids)}  total_prompts={len(prompt_ids)}  intersection={len(inter)}")
        if missing:
            print(f"  sample prompt IDs missing from metric (first 5): {missing[:5]}")
        else:
            print("  all prompt ids present in metrics.")
        print("-" * 60)

def main():
    try:
        prompt_ids = load_prompt_ids(PROMPTS_CSV)
    except FileNotFoundError as e:
        print("ERROR:", e)
        return
    inspect_metrics(prompt_ids, METRIC_FILES)

if __name__ == "__main__":
    main()