import csv
from pathlib import Path
fn = Path("results/quantitative/metrics_per_item.csv")
if not fn.exists():
    print("Missing file:", fn)
    raise SystemExit(1)
with fn.open(encoding="utf-8", newline="") as f:
    r = csv.reader(f)
    for i, row in enumerate(r):
        print(row)
        if i >= 9:
            break