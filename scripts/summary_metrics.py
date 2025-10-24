import json
from statistics import mean
from pathlib import Path

p=Path("results/quantitative/metrics_per_item.json")
if not p.exists():
    print("missing metrics_oer_item.json")
    raise SystemExit(1)
obj=json.loads(p.read_text(encoding='utf-8'))
per = obj.get("per_item", [])
by_mode = {}
for r in per:
    mode=r.get("mode")
    by_mode.setdefault(mode, []).append(r)
for m,rows in by_mode.items():
    lcs=[r.get("lcs_ratio",0) for r in rows]
    ps=[r.get("pass",0) for r in rows]
    print(f"{m}: n={len(rows)} mean(lcs){mean(lcs):.4f} mean_pass={mean(ps):4f}")