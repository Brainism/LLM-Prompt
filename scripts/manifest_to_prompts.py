import json
import csv
import argparse
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise SystemExit(f"[ERR] manifest not found: {manifest_path}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        raise SystemExit("[ERR] manifest.items is empty")

    fieldnames = ["id","input","reference","domain","lang","len_bin","diff_bin"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for it in items:
            row = {
                "id": it.get("id",""),
                "input": it.get("input",""),
                "reference": it.get("reference",""),
                "domain": it.get("domain","general"),
                "lang": it.get("lang","ko"),
                "len_bin": it.get("len_bin","medium"),
                "diff_bin": it.get("diff_bin","medium")
            }
            w.writerow(row)

    print(f"[OK] prompts CSV written: {out_path} (n={len(items)})")

if __name__ == "__main__":
    main()