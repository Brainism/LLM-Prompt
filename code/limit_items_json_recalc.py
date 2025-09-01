from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def truthy(v: str) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "y", "yes")


def load_targets(csv_path: Path) -> set[str]:
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig")))
    return {(r.get("id") or "").strip() for r in rows if truthy(r.get("needs_json"))}


def iter_jsonl(p: Path):
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            yield json.loads(s)
        except Exception:
            continue


def eval_mode(
    jsonl_path: Path, targets: set[str], key: str, min_items: int, max_items: int
) -> tuple[int, int]:
    total = 0
    ok = 0
    for rec in iter_jsonl(jsonl_path):
        rid = str(rec.get("id", "")).strip()
        if rid not in targets:
            continue
        total += 1
        out = rec.get("output")
        try:
            obj = json.loads(out) if isinstance(out, str) else out
        except Exception:
            obj = None
        arr = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(arr, list) and (min_items <= len(arr) <= max_items):
            ok += 1
    return ok, total


def update_compliance_summary(
    csv_path: Path, gen_rate: float, inst_rate: float
) -> None:
    rows = []
    found = False
    if csv_path.exists():
        rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig")))
        header = (
            rows[0].keys() if rows else ("metric", "general_rate", "instructed_rate")
        )
    else:
        header = ("metric", "general_rate", "instructed_rate")

    new_rows = []
    for r in rows:
        metric = r.get("metric")
        if metric == "limit_items_json":
            r = dict(r)
            if "general_rate" in r:
                r["general_rate"] = f"{gen_rate:.3f}"
                r["instructed_rate"] = f"{inst_rate:.3f}"
            else:
                r["general"] = f"{gen_rate:.3f}"
                r["instructed"] = f"{inst_rate:.3f}"
            found = True
        new_rows.append(r)

    if not found:
        new_rows.append(
            {
                "metric": "limit_items_json",
                "general_rate": f"{gen_rate:.3f}",
                "instructed_rate": f"{inst_rate:.3f}",
            }
        )
        header = ("metric", "general_rate", "instructed_rate")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in new_rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--apply-from", type=Path, required=True, help="prompts.csv (needs_json 기준)"
    )
    ap.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("results") / "raw_patched",
        help="평가 대상 로그 폴더",
    )
    ap.add_argument("--json-key", default="tags", help="배열 키 이름 (기본: tags)")
    ap.add_argument("--min-items", type=int, default=2, help="최소 아이템 수")
    ap.add_argument("--max-items", type=int, default=5, help="최대 아이템 수")
    ap.add_argument(
        "--summary-csv",
        type=Path,
        default=Path("results") / "quantitative" / "compliance_summary.csv",
    )
    args = ap.parse_args()

    targets = load_targets(args.apply_from)

    gen_ok, gen_total = eval_mode(
        args.raw_dir / "general.jsonl",
        args.targets if hasattr(args, "targets") else targets,
        args.json_key,
        args.min_items,
        args.max_items,
    )
    inst_ok, inst_total = eval_mode(
        args.raw_dir / "instructed.jsonl",
        targets,
        args.json_key,
        args.min_items,
        args.max_items,
    )

    gen_rate = (gen_ok / gen_total) if gen_total else 0.0
    inst_rate = (inst_ok / inst_total) if inst_total else 0.0

    print(f"[limit_items_json] general: {gen_ok}/{gen_total} = {gen_rate:.3f}")
    print(f"[limit_items_json] instructed: {inst_ok}/{inst_total} = {inst_rate:.3f}")

    update_compliance_summary(args.summary_csv, gen_rate, inst_rate)
    print(f"[ok] updated {args.summary_csv}")


if __name__ == "__main__":
    main()
