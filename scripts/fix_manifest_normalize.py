import json, argparse, shutil
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--in", dest="infile", required=True)
args = parser.parse_args()
inpath = Path(args.infile)
bak = inpath.with_suffix(".json.bak")
shutil.copy(inpath, bak)
data = json.loads(inpath.read_text(encoding="utf-8"))
changed = False
if isinstance(data, dict) and "$schema" in data:
    del data["$schema"]; changed = True
for item in data.get("items", []):
    if "len_bin" in item and item["len_bin"] == "mid":
        item["len_bin"] = "medium"; changed = True
    if "diff_bin" in item and item["diff_bin"] == "mid":
        item["diff_bin"] = "medium"; changed = True
    if "len_bin" not in item:
        item["len_bin"] = "short"; changed = True
    if "diff_bin" not in item:
        item["diff_bin"] = "easy"; changed = True
if changed:
    inpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] normalized and wrote {inpath}. backup at {bak}")
else:
    print("[OK] no changes needed")