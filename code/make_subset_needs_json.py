from __future__ import annotations
import csv, re
from pathlib import Path

SRC = Path("prompts/prompts.csv")
DST = Path("prompts/prompts_needs_json.csv")

ID_RE = re.compile(r"^ex-(\d{4})$")

def truthy(v: str) -> bool:
    return str(v or "").strip().lower() in ("1","true","y","yes")

def natkey(id_str: str):
    m = ID_RE.match(id_str or "")
    return int(m.group(1)) if m else 10**9

def main():
    if not SRC.exists():
        raise FileNotFoundError(f"missing: {SRC}")

    rows = list(csv.DictReader(SRC.open("r", encoding="utf-8-sig")))
    if not rows:
        raise RuntimeError("empty prompts.csv")

    picked = [r for r in rows if truthy(r.get("needs_json"))]

    seen = set()
    uniq = []
    for r in reversed(picked):
        pid = (r.get("id") or "").strip()
        if pid and pid not in seen:
            seen.add(pid)
            uniq.append(r)
    uniq.reverse()

    uniq.sort(key=lambda r: natkey((r.get("id") or "").strip()))

    hdr = list(rows[0].keys())
    with DST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        for r in uniq:
            w.writerow(r)

    back = list(csv.DictReader(DST.open("r", encoding="utf-8-sig")))
    ids = [r.get("id") for r in back]
    bad = [i for i in ids if not ID_RE.match(i or "")]
    print(f"[ok] wrote {DST} rows={len(back)} (header included)")
    print(f"[ids] first: {ids[:5]}")
    if bad:
        print(f"[warn] malformed ids found: {bad}")

if __name__ == "__main__":
    main()