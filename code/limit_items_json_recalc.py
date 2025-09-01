from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    yield obj
            except Exception:
                continue


def extract_text_field(rec: Dict[str, Any]) -> str:
    candidates = ["output", "prediction", "text", "response", "completion", "answer"]
    for k in candidates:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return json.dumps(rec, ensure_ascii=False)


def extract_json_from_text(text: str) -> Optional[Any]:
    if not text:
        return None
    patterns = [r"\{.*\}", r"\[.*\]"]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            sub = m.group(0)
            try:
                return json.loads(sub)
            except Exception:
                continue
    return None


def eval_record(text: str, json_key: str, min_items: int, max_items: int) -> bool:
    obj = extract_json_from_text(text)
    if not isinstance(obj, dict):
        return False
    arr = obj.get(json_key)
    if not isinstance(arr, list):
        return False
    n = len(arr)
    return min_items <= n <= max_items


def eval_mode(
    jsonl_path: Path, json_key: str, min_items: int, max_items: int
) -> Tuple[int, int]:
    ok = 0
    total = 0
    for rec in read_jsonl(jsonl_path):
        text = extract_text_field(rec)
        total += 1
        if eval_record(text, json_key, min_items, max_items):
            ok += 1
    return ok, total


def update_compliance_summary(
    csv_path: Path, gen_rate: float, inst_rate: float
) -> None:
    rows: List[Dict[str, str]] = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append(dict(row))

    def put(metric: str, value: float) -> None:
        found = False
        for row in rows:
            if row.get("metric") == metric:
                row["value"] = f"{value:.3f}"
                found = True
                break
        if not found:
            rows.append({"metric": metric, "value": f"{value:.3f}"})

    put("general_rate", gen_rate)
    put("instructed_rate", inst_rate)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("results") / "raw",
        help="general.jsonl / instructed.jsonl 이 위치한 디렉터리",
    )
    ap.add_argument("--general-file", type=str, default="general.jsonl")
    ap.add_argument("--instructed-file", type=str, default="instructed.jsonl")
    ap.add_argument(
        "--json-key", type=str, default="tags", help="배열 길이를 확인할 JSON의 키"
    )
    ap.add_argument("--min-items", type=int, default=2, help="허용 최소 길이")
    ap.add_argument("--max-items", type=int, default=5, help="허용 최대 길이")
    ap.add_argument(
        "--summary-csv",
        type=Path,
        default=Path("results") / "quantitative" / "compliance_summary.csv",
    )
    args = ap.parse_args()

    g_path = args.raw_dir / args.general_file
    i_path = args.raw_dir / args.instructed_file

    gen_ok, gen_total = eval_mode(g_path, args.json_key, args.min_items, args.max_items)
    inst_ok, inst_total = eval_mode(
        i_path, args.json_key, args.min_items, args.max_items
    )

    gen_rate = (gen_ok / gen_total) if gen_total else 0.0
    inst_rate = (inst_ok / inst_total) if inst_total else 0.0

    print(f"[limit_items_json] general:    {gen_ok}/{gen_total} = {gen_rate:.3f}")
    print(f"[limit_items_json] instructed: {inst_ok}/{inst_total} = {inst_rate:.3f}")

    update_compliance_summary(args.summary_csv, gen_rate, inst_rate)
    print(f"[ok] updated {args.summary_csv}")


if __name__ == "__main__":
    main()
