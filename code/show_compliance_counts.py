import collections
import csv
import sys
from pathlib import Path

p = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "quantitative"
    / "compliance_by_item.csv"
)
if len(sys.argv) > 1:
    p = Path(sys.argv[1])

c = collections.defaultdict(lambda: [0, 0])
with p.open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        k = (r["scenario"], r["mode"])
        c[k][0] += int(r["passed"])
        c[k][1] += 1

for k, (ok, n) in sorted(c.items()):
    print(f"{k}: {ok}/{n} = {ok/n:.2%}")
