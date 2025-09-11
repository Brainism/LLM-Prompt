import json, sys
from pathlib import Path

if len(sys.argv) < 3:
    print("Usage: python scripts\\make_manifest_for_id.py EX-0049 tmp\\manifest_EX-0049.json")
    raise SystemExit(1)
id_to = sys.argv[1]
out_path = Path(sys.argv[2])
orig = Path("data/manifest/split_manifest_main.json")
m = json.load(open(orig, "r", encoding="utf-8"))
items = []
if isinstance(m, dict) and "items" in m:
    for it in m["items"]:
        if it.get("id")==id_to:
            items.append(it)
elif isinstance(m, list):
    for it in m:
        if it.get("id")==id_to:
            items.append(it)
else:
    for k,v in m.items():
        if k==id_to or (isinstance(v, dict) and v.get("id")==id_to):
            items.append(v)
if not items:
    print("ID not found:", id_to); raise SystemExit(2)
out = {"items": items}
out_path.parent.mkdir(parents=True, exist_ok=True)
open(out_path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print("Wrote", out_path)