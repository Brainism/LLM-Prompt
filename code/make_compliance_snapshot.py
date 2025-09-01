import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "results" / "quantitative" / "compliance_summary.csv"
dst = ROOT / "docs" / "compliance_snapshot.md"
dst.parent.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise SystemExit(f"[fail] not found: {src}")

rows = []
with src.open("r", encoding="utf-8") as f:
    for i, r in enumerate(csv.reader(f)):
        if i == 0:
            header = r
        else:
            rows.append(r)

lines = []
lines.append("# Compliance Snapshot")
lines.append("")
lines.append(f"- source: `{src.as_posix()}`")
lines.append("")
lines.append("| metric | general | instructed |")
lines.append("|---|---:|---:|")
for r in rows:
    metric, g, ins = r[0], r[1], r[2]
    lines.append(f"| {metric} | {g} | {ins} |")

dst.write_text("\n".join(lines), encoding="utf-8")
print(f"[ok] wrote {dst}")
