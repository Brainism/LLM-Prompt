import sys, csv
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: python scripts\\clean_recover_remove_empty_id.py <in_csv> <out_csv>")
    sys.exit(1)

inp = Path(sys.argv[1])
out = Path(sys.argv[2])
if not inp.exists():
    print("Input not found:", inp); sys.exit(2)

with open(inp, "r", encoding="utf-8-sig", errors="replace", newline="") as fh, \
     open(out, "w", encoding="utf-8-sig", newline="") as outfh:
    reader = csv.reader(fh)
    writer = csv.writer(outfh)
    hdr = next(reader, None)
    writer.writerow(["id","prediction"])
    kept = 0
    dropped = 0
    for r in reader:
        if not r:
            continue
        rid = r[0].strip() if len(r) >= 1 else ""
        rid = rid.replace("\ufeff","").strip()
        if rid == "":
            
            dropped += 1
            continue
        pred = "" if len(r) == 1 else ",".join(r[1:]).strip()
        writer.writerow([rid, pred])
        kept += 1

print(f"Wrote {out} (kept={kept}, dropped_empty_id={dropped})")