import json
import collections
from pathlib import Path

p = Path("split_manifest.json")
if not p.exists():
    print("ERROR: split_manifest.json not found in CWD:", p.resolve())
    raise SystemExit(2)

m = json.loads(p.read_text(encoding="utf-8"))
ids = [it.get("id") for it in m.get("items",[])]
counter = collections.Counter(ids)
dups = [k for k,v in counter.items() if v>1]
print("n_items:", len(ids))
print("unique ids:", len(set(ids)))
print("duplicate ids count:", len(dups))
if dups:
    print("duplicate ids (sample up to 50):")
    for d in dups[:50]:
        print(" -", d, "occurs:", counter[d])
    dd = dups[0]
    print("\nExample entries for duplicate id:", dd)
    for it in [it for it in m.get("items",[]) if it.get("id")==dd]:
        print(json.dumps(it, ensure_ascii=False))
else:
    print("No duplicate ids found.")