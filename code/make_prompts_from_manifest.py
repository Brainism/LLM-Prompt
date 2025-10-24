# code/make_prompts_from_manifest.py
import json, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../LLM
MANI = ROOT / "data" / "manifest" / "split_manifest_main.json"
OUT  = ROOT / "prompts" / "prompts.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

if not MANI.exists():
    raise FileNotFoundError(f"매니페스트가 없어요: {MANI}")

data = json.loads(MANI.read_text(encoding="utf-8"))
items = data.get("items", [])
if not items:
    raise ValueError("매니페스트에 items가 비어 있어요.")

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id","input","reference","domain","lang","len_bin","diff_bin","cluster_id"])
    for it in items:
        w.writerow([
            it["id"], it["input"], it["reference"], it["domain"],
            it["lang"], it["len_bin"], it["diff_bin"], it["cluster_id"]
        ])

print(f"Wrote {OUT} (n={len(items)})")