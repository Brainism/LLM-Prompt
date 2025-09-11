import csv, json, sys, os
from pathlib import Path

in_csv = sys.argv[1] if len(sys.argv) > 1 else "prompts/main.csv"
out_jsonl = sys.argv[2] if len(sys.argv) > 2 else "data/raw/references/references.jsonl"

Path(out_jsonl).parent.mkdir(parents=True, exist_ok=True)

with open(in_csv, "r", encoding="utf-8-sig") as inf, open(out_jsonl, "w", encoding="utf-8") as outf:
    r = csv.DictReader(inf)
    written = 0
    for row in r:
        ex_id = row.get("id") or row.get("ID") or row.get("Id")
        ref = row.get("reference") or row.get("ref") or row.get("target") or row.get("reference_text") or row.get("target_text") or ""
        if not ex_id:
            continue
        obj = {"id": str(ex_id), "reference": (ref or "").strip()}
        outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
        written += 1

print(f"[OK] wrote {written} records -> {out_jsonl}")