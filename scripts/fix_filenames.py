import os
import sys
import pandas as pd

ROOT = r"C:\Project\LLM"

src = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
if not os.path.exists(src):
    print(f"ERROR: Source not found: {src}")
    sys.exit(1)

os.makedirs(os.path.join(ROOT, "docs", "paper", "tables"), exist_ok=True)

with open(os.path.join(ROOT, "docs", "paper", "tables", "READ_ME.txt"), "w", encoding="utf-8") as fh:
    fh.write("Source of truth: aggregated_metrics_fixed_with_chrf_rouge.csv\n")
print("OK: aggregated_metrics_fixed_with_chrf_rouge.csv 존재")

q = os.path.join(ROOT, "per_item_full_60.csv")
if os.path.exists(q):
    try:
        df_q = pd.read_csv(q, encoding="utf-8-sig")
        n = len(df_q)
    except Exception as e:
        print("ERROR reading per_item_full_60.csv:", e)
        n = None

    if n == 50:
        dst = os.path.join(ROOT, "per_item_full_50.csv")
        os.replace(q, dst)
        print("RENAMED: per_item_full_60.csv -> per_item_full_50.csv")
    else:
        print(f"INFO: per_item_full_60.csv exists but row count = {n}")
else:
    print("WARN: per_item_full_60.csv 없음")

print("DONE")