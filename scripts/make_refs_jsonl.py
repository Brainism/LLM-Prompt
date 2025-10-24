import csv, json, sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("Usage: python scripts\\make_refs_jsonl.py <prompts.csv> <out.jsonl>")

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
dst.parent.mkdir(parents=True, exist_ok=True)

def norm(s): return (s or "").strip().lstrip("\ufeff").lower()

with src.open("r", encoding="utf-8-sig", newline="") as f, dst.open("w", encoding="utf-8") as out:
    rdr = csv.DictReader(f)
    fields = {norm(c): c for c in (rdr.fieldnames or [])}
    cid  = fields.get("id")
    cref = fields.get("reference") or fields.get("reference_text") or fields.get("ref")
    if not cid or not cref:
        raise SystemExit("[FATAL] prompts CSV must have columns 'id' and 'reference'")

    n = 0
    for r in rdr:
        rid = str(r.get(cid, "")).strip()
        ref = str(r.get(cref, "")).strip()
        if not rid:
            continue
        out.write(json.dumps({"id": rid, "reference_text": ref}, ensure_ascii=False) + "\n")
        n += 1

print(f"[OK] wrote {dst} lines={n}")