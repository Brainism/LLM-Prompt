import json
import csv
from pathlib import Path
import sys

MANIFEST_PATH = Path("data/manifest/split_manifest_main.json")
OUT_PATH = Path("reports/synthetic_items.csv")

def load_manifest(p: Path):
    if not p.exists():
        print(f"[ERR] manifest not found: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        text = p.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as e:
        print(f"[ERR] Failed to read/parse manifest: {e}", file=sys.stderr)
        sys.exit(3)
    items = data.get("items") or []
    if not isinstance(items, list):
        print("[ERR] manifest.items is not a list", file=sys.stderr)
        sys.exit(4)
    return items

def is_synthetic_id(item_id: str) -> bool:
    if not item_id:
        return False
    s = item_id.upper()
    return ("_SYN" in s) or ("_SYND" in s) or s.endswith("_SYN") or s.endswith("_SYND")

def summarize_item(it):
    return {
        "id": it.get("id",""),
        "synthetic_flag": bool(is_synthetic_id(it.get("id",""))),
        "cluster_id": it.get("cluster_id",""),
        "lang": it.get("lang",""),
        "len_bin": it.get("len_bin",""),
        "diff_bin": it.get("diff_bin",""),
        "n_chars": int(it.get("n_chars")) if it.get("n_chars") not in (None,"") else len(it.get("input","") or ""),
        "input_head": (it.get("input","") or "")[:200].replace("\n"," "),
        "reference_head": (it.get("reference","") or "")[:200].replace("\n"," ")
    }

def write_csv(rows, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id","synthetic_flag","cluster_id","lang","len_bin","diff_bin","n_chars","input_head","reference_head"]
    try:
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
    except Exception as e:
        print(f"[ERR] Failed to write CSV: {e}", file=sys.stderr)
        sys.exit(5)

def main():
    items = load_manifest(MANIFEST_PATH)
    if not items:
        print("[INFO] manifest contains zero items.")
        write_csv([], OUT_PATH)
        print(f"[OK] wrote {OUT_PATH} (n=0)")
        return

    summaries = [summarize_item(it) for it in items]
    synthetic_rows = [s for s in summaries if s["synthetic_flag"]]

    write_csv(synthetic_rows, OUT_PATH)
    print(f"[OK] wrote {OUT_PATH} (n={len(synthetic_rows)})")
    if synthetic_rows:
        print("[SAMPLE]")
        for i, r in enumerate(synthetic_rows[:10], start=1):
            print(f" {i}. id={r['id']}, cell=({r['lang']},{r['len_bin']},{r['diff_bin']}), n_chars={r['n_chars']}")
    else:
        print("[INFO] No synthetic items found in manifest.")

if __name__ == "__main__":
    main()