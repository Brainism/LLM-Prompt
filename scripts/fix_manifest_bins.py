import json
import sys

p = sys.argv[1]
d = json.load(open(p, "r", encoding="utf-8"))
for it in d["items"]:
    if it.get("len_bin") == "mid":
        it["len_bin"] = "medium"
    if it.get("diff_bin") == "mid":
        it["diff_bin"] = "medium"
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
