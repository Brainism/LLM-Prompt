import sys
import csv
from pathlib import Path

if len(sys.argv) != 4:
    print("Usage: python scripts\\update_master_from_recover_robust.py <master_csv> <recover_csv> <out_csv>")
    sys.exit(1)

master_p = Path(sys.argv[1])
recover_p = Path(sys.argv[2])
out_p = Path(sys.argv[3])

if not master_p.exists():
    print("Master file not found:", master_p); sys.exit(2)
if not recover_p.exists():
    print("Recover file not found:", recover_p); sys.exit(3)

def read_as_map(path):
    m = {}
    with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as fh:
        reader = csv.reader(fh)
        headers = next(reader, None)
        for row in reader:
            if not row:
                continue
            id_ = row[0].strip()
            pred = ""
            if len(row) >= 2:
                pred = ",".join(row[1:]).strip()
            m[id_] = pred
    return m

def read_master_rows(path):
    rows = []
    with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as fh:
        reader = csv.reader(fh)
        headers = next(reader, None)
        for row in reader:
            if not row:
                continue
            if len(row) == 1:
                row = [row[0], ""]
            rows.append(row)
    return headers, rows

recover_map = read_as_map(recover_p)
headers, master_rows = read_master_rows(master_p)

out_header = ['id','prediction']
with open(out_p, 'w', encoding='utf-8-sig', newline='') as outfh:
    writer = csv.writer(outfh)
    writer.writerow(out_header)
    n_updated = 0
    n_total = 0
    for row in master_rows:
        n_total += 1
        id_ = row[0].strip()
        if id_ and id_ in recover_map and recover_map[id_] != "":
            writer.writerow([id_, recover_map[id_]])
            n_updated += 1
        else:
            if len(row) >= 2:
                pred = ",".join(row[1:]).strip()
            else:
                pred = ""
            writer.writerow([id_, pred])
    extra = [rid for rid in recover_map.keys() if rid not in {r[0].strip() for r in master_rows}]
    for rid in extra:
        writer.writerow([rid, recover_map[rid]])

print(f"Wrote updated master {out_p} (rows={n_total + len(extra)}), updated {n_updated} rows, appended {len(extra)} extra rows.")