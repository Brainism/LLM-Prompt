import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANI = ROOT / "data" / "manifest" / "split_manifest_main.json"
DOC = ROOT / "docs" / "data_report.md"
DOC.parent.mkdir(parents=True, exist_ok=True)

m = json.loads(MANI.read_text(encoding="utf-8"))
items = m["items"]

cnt = len(items)
by = lambda k: collections.Counter(x[k] for x in items)

lines = []
lines += ["# Data Report (split_manifest_main)", ""]
lines += [f"- Total items: **{cnt}**", ""]
for key in ["domain", "lang", "len_bin", "diff_bin", "license"]:
    c = by(key)
    lines += [f"## {key}", ""]
    for k, v in c.most_common():
        lines += [f"- {k}: {v}"]
    lines += [""]

DOC.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {DOC}")
