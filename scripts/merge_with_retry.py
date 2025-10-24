import argparse
import json
from pathlib import Path
import sys

def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                items.append(json.loads(s))
            except Exception as e:
                print(f"[WARN] skipping malformed line {i} in {path}: {e}", file=sys.stderr)
    return items

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--orig", default="results/raw/general.jsonl", help="Original JSONL (one json per line)")
    p.add_argument("--retry", default="results/raw/retry_general_EX-0049_fixed.jsonl", help="Retry JSONL to merge (replace by id)")
    p.add_argument("--out", default="results/raw/general_with_retry.jsonl", help="Output merged JSONL")
    p.add_argument("--backup", action="store_true", help="If set and out exists, make a backup <out>.bak")
    args = p.parse_args()

    orig_path = Path(args.orig)
    retry_path = Path(args.retry)
    out_path = Path(args.out)

    if not orig_path.exists():
        print(f"[ERROR] orig not found: {orig_path}", file=sys.stderr); sys.exit(2)
    if not retry_path.exists():
        print(f"[ERROR] retry not found: {retry_path}", file=sys.stderr); sys.exit(2)

    orig_items = load_jsonl(orig_path)
    retry_items = load_jsonl(retry_path)

    retry_map = {}
    for it in retry_items:
        iid = it.get("id")
        if iid is None:
            print("[WARN] retry item without id, skipping:", it, file=sys.stderr)
            continue
        retry_map[iid] = it

    replaced = 0
    new_items = []
    for it in orig_items:
        iid = it.get("id")
        if iid in retry_map:
            new_items.append(retry_map[iid])
            replaced += 1
        else:
            new_items.append(it)

    if args.backup and out_path.exists():
        bak = out_path.with_suffix(out_path.suffix + ".bak")
        out_path.replace(bak)
        print(f"[INFO] moved existing {out_path} -> {bak}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for it in new_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"[OK] WROTE {out_path} (orig_count={len(orig_items)}, retry_count={len(retry_items)}, replaced={replaced})")

if __name__ == "__main__":
    main()