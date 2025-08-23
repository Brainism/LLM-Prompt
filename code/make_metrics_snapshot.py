from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
src  = ROOT / "results" / "quantitative" / "stats_summary.csv"
dst  = ROOT / "docs" / "metrics_snapshot.md"
dst.parent.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise SystemExit(f"[fail] not found: {src}")

rows = []
with src.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

def g(r,k,default=""):
    for cand in [k, k.lower(), k.upper()]:
        if cand in r: return r[cand]
    return default

lines = []
lines.append("# Metrics Snapshot")
lines.append("")
lines.append(f"- source: `{src.as_posix()}`")
lines.append("")
if rows:
    cols = [c for c in rows[0].keys()]
    show = [c for c in cols if c.lower() in
            {"metric","mean_general","mean_instructed","delta","p","q","ci_low","ci_high","effect_size"}]
    if not show: show = cols
    lines.append("| " + " | ".join(show) + " |")
    lines.append("|" + "|".join(["---"]*len(show)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(g(r,c,"") for c in show) + " |")
else:
    lines.append("_no rows in stats_summary.csv_")

dst.write_text("\n".join(lines), encoding="utf-8")
print(f"[ok] wrote {dst}")