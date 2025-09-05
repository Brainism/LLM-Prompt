import json
import csv
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SYSTEM_GENERAL = "You are a helpful assistant. Follow the instruction."
DEFAULT_SYSTEM_INSTRUCTED = "Follow the instruction exactly, obey constraints and output cleanly."

def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"[FATAL] manifest not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"[FATAL] invalid JSON: {path}: {e}")

def write_csv(path: Path, header: List[str], rows: List[List[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser(description="Convert manifest JSON to prompts CSV.")
    ap.add_argument("--manifest", required=True, help="Path to manifest JSON with top-level 'items'")
    ap.add_argument("--out", required=True, help="Output CSV path, e.g., prompts\\main.csv")
    ap.add_argument("--general", default=DEFAULT_SYSTEM_GENERAL, help="System text for general mode")
    ap.add_argument("--instructed", default=DEFAULT_SYSTEM_INSTRUCTED, help="System text for instructed mode")
    ap.add_argument("--limit", type=int, default=None, help="Optional limit for number of items")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    out_path = Path(args.out)

    data = load_json(manifest_path)
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        raise SystemExit("[FATAL] manifest.items must be a non-empty list")

    header = ["id","lang","len_bin","diff_bin","input","reference","system_general","system_instructed"]
    rows: List[List[Any]] = []

    n_in = 0
    for it in items[: args.limit or len(items)]:
        n_in += 1
        rid = it.get("id")
        inp = it.get("input", "")
        ref = it.get("reference", "")
        lang = it.get("lang")
        len_bin = it.get("len_bin")
        diff_bin = it.get("diff_bin")

        if not isinstance(rid, str) or not rid.strip():
            continue
        if not isinstance(inp, str) or not inp.strip():
            continue

        rows.append([
            rid, lang, len_bin, diff_bin, inp, ref,
            args.general, args.instructed
        ])

    write_csv(out_path, header, rows)
    print(f"[OK] wrote {out_path}  rows={len(rows)}  (from {n_in} items)")

if __name__ == "__main__":
    main()