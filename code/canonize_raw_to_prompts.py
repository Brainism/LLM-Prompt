from __future__ import annotations
import csv, json, argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"

SYSTEM_GENERAL_DEFAULT = "You are a helpful assistant. Follow the instruction."
SYSTEM_INSTRUCTED_DEFAULT = "Follow the instruction exactly, obey constraints and output cleanly."

def parse_ts(s: str) -> float:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0

def _ensure_path(p: Optional[str]) -> Optional[Path]:
    return None if p is None else Path(p)

def from_manifest_to_prompts_csv(
    manifest_path: Path,
    out_csv: Path,
    sys_general_text: str = SYSTEM_GENERAL_DEFAULT,
    sys_instructed_text: str = SYSTEM_INSTRUCTED_DEFAULT,
    limit: Optional[int] = None,
    encoding_csv: str = "utf-8-sig",
) -> None:
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        raise SystemExit("[FATAL] manifest.items must be a non-empty list")

    header = [
        "id", "lang", "len_bin", "diff_bin",
        "input", "reference",
        "system_general", "system_instructed"
    ]
    rows: List[List[Any]] = []

    n_in = 0
    for it in items[: (limit or len(items))]:
        n_in += 1
        rid = it.get("id")
        inp = it.get("input", "")
        if not isinstance(rid, str) or not rid.strip():
            continue
        if not isinstance(inp, str) or not inp.strip():
            continue

        rows.append([
            rid,
            it.get("lang"),
            it.get("len_bin"),
            it.get("diff_bin"),
            inp,
            it.get("reference", ""),
            sys_general_text,
            sys_instructed_text
        ])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding=encoding_csv) as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        w.writerows(rows)

    print(f"[OK] wrote {out_csv}  rows={len(rows)}  (from {n_in} items)")

def read_id_set(csv_path: Path, id_col: str) -> list[str]:
    ids: List[str] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ids.append(str(row[id_col]))
    return ids

def load_jsonl(fp: Path) -> List[Dict[str, Any]]:
    if not fp.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in fp.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def write_jsonl(fp: Path, recs: List[Dict[str, Any]]) -> None:
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")

def canonize_one(mode: str, records: List[Dict[str, Any]], allowed_ids: set[str]) -> List[Dict[str, Any]]:
    latest: Dict[str, tuple[float, Dict[str, Any]]] = {}
    kept, dropped = 0, 0
    for r in records:
        rid = str(r.get("id") or r.get("item_id") or r.get("example_id") or "")
        if not rid or rid not in allowed_ids:
            dropped += 1
            continue
        ts = parse_ts(str(r.get("timestamp", "")))
        prev = latest.get(rid)
        if (prev is None) or (ts >= prev[0]):
            latest[rid] = (ts, r)
        kept += 1

    canon = [rec for _, rec in latest.values()]
    canon.sort(key=lambda x: str(x.get("id", "")))
    print(f"[{mode}] input={len(records)} kept={len(canon)} (dedup from {kept}, dropped={dropped})")
    return canon

def backup_then_write(path: Path, recs: List[Dict[str, Any]]) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[INFO] backup -> {backup.name}")
    write_jsonl(path, recs)

def canonize_from_prompts_csv(
    prompts_csv: Path,
    id_column: str = "id",
    general_jsonl: Optional[Path] = None,
    instructed_jsonl: Optional[Path] = None,
) -> None:
    if general_jsonl is None:
        general_jsonl = RAWDIR / "general.jsonl"
    if instructed_jsonl is None:
        instructed_jsonl = RAWDIR / "instructed.jsonl"

    id_list = read_id_set(prompts_csv, id_column)
    id_set = set(id_list)
    print(f"[prompts] ids={len(id_set)}  sample[0:3]={id_list[:3]}")

    g_recs = load_jsonl(general_jsonl)
    i_recs = load_jsonl(instructed_jsonl)

    g_canon = canonize_one("general", g_recs, id_set)
    i_canon = canonize_one("instructed", i_recs, id_set)

    backup_then_write(general_jsonl, g_canon)
    backup_then_write(instructed_jsonl, i_canon)

    print(f"[OK] canonized -> {general_jsonl.name}={len(g_canon)}, {instructed_jsonl.name}={len(i_canon)}")

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="(A) manifest->prompts CSV  /  (B) prompts CSV->JSONL canonize  (둘 중 하나만)"
    )

    ap.add_argument("--manifest", type=str, help="Path to manifest JSON (top-level 'items').")
    ap.add_argument("--out", type=str, help="Output CSV path, e.g., prompts\\main.csv")
    ap.add_argument("--limit", type=int, default=None, help="Optional limit for manifest rows.")
    ap.add_argument("--sys-general-text", type=str, default=SYSTEM_GENERAL_DEFAULT,
                    help="(Mode A) System text for general mode.")
    ap.add_argument("--sys-instructed-text", type=str, default=SYSTEM_INSTRUCTED_DEFAULT,
                    help="(Mode A) System text for instructed mode.")
    ap.add_argument("--csv-encoding", type=str, default="utf-8-sig",
                    help="(Mode A) CSV encoding (default: utf-8-sig).")

    ap.add_argument("--prompts", type=str, help="Prompts CSV path (must contain an ID column).")
    ap.add_argument("--id-column", type=str, default="id", help="ID column name (default: id).")
    ap.add_argument("--general-file", type=str, help="Path to results/raw/general.jsonl (default internal).")
    ap.add_argument("--instructed-file", type=str, help="Path to results/raw/instructed.jsonl (default internal).")

    args = ap.parse_args()

    mode_a = args.manifest is not None or args.out is not None
    mode_b = args.prompts is not None or args.general_file is not None or args.instructed_file is not None

    if mode_a and mode_b:
        ap.error("Use either Mode A (--manifest & --out) OR Mode B (--prompts ...). Not both.")
    if not mode_a and not mode_b:
        ap.error("One of Mode A (--manifest & --out) OR Mode B (--prompts ...) must be provided.")

    if mode_a:
        if not args.manifest or not args.out:
            ap.error("Mode A requires both --manifest and --out.")
    return args

def main():
    args = parse_args()
    if args.manifest:
        from_manifest_to_prompts_csv(
            manifest_path=Path(args.manifest),
            out_csv=Path(args.out),
            sys_general_text=args.sys_general_text,
            sys_instructed_text=args.sys_instructed_text,
            limit=args.limit,
            encoding_csv=args.csv_encoding,
        )
    else:
        canonize_from_prompts_csv(
            prompts_csv=Path(args.prompts),
            id_column=args.id_column,
            general_jsonl=_ensure_path(args.general_file),
            instructed_jsonl=_ensure_path(args.instructed_file),
        )

if __name__ == "__main__":
    main()