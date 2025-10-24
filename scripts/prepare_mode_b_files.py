from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Dict, List, Tuple

def load_prompts(csv_path: Path) -> Tuple[List[str], Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        cols = {c.strip().lstrip("\ufeff").lower(): c for c in (rdr.fieldnames or [])}
        col_id = cols.get("id")
        col_ref = cols.get("reference") or cols.get("reference_text") or cols.get("ref")
        if not col_id or not col_ref:
            raise SystemExit("[FATAL] prompts CSV must have columns 'id' and 'reference'")
        order: List[str] = []
        id2ref: Dict[str, str] = {}
        for r in rdr:
            rid = str(r.get(col_id, "")).strip()
            ref = str(r.get(col_ref, "")).strip()
            if rid:
                order.append(rid)
                id2ref[rid] = ref
        return order, id2ref

def load_jsonl_last(path: Path, field: str) -> Dict[str, str]:
    id2out: Dict[str, str] = {}
    if not path.exists():
        return id2out
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except Exception:
            continue
        rid = str(o.get("id", "") or "")
        if not rid:
            continue
        id2out[rid] = str(o.get(field, "") or "")
    return id2out

def write_lines(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Prepare refs/hyps text files for Mode B metrics.")
    ap.add_argument("--prompts", required=True, help="prompts/main.csv (must have id,reference)")
    ap.add_argument("--general-jsonl", required=True, help="results/raw/general.jsonl")
    ap.add_argument("--instructed-jsonl", required=True, help="results/raw/instructed.jsonl")
    ap.add_argument("--out-refs", default="refs.txt")
    ap.add_argument("--out-hyps-general", default="hyps_general.txt")
    ap.add_argument("--out-hyps-instructed", default="hyps_instructed.txt")
    args = ap.parse_args()

    order, id2ref = load_prompts(Path(args.prompts))
    id2g = load_jsonl_last(Path(args.general_jsonl), "output")
    id2i = load_jsonl_last(Path(args.instructed_jsonl), "output")

    ids = [rid for rid in order if rid in id2ref and rid in id2g and rid in id2i]

    refs = [id2ref[rid] for rid in ids]
    hyps_g = [id2g[rid] for rid in ids]
    hyps_i = [id2i[rid] for rid in ids]

    write_lines(Path(args.out_refs), refs)
    write_lines(Path(args.out_hyps_general), hyps_g)
    write_lines(Path(args.out_hyps_instructed), hyps_i)

    missing_ref = [rid for rid in order if rid not in id2ref]
    missing_g   = [rid for rid in order if rid not in id2g]
    missing_i   = [rid for rid in order if rid not in id2i]

    print(f"[OK] wrote {args.out_refs}={len(refs)}, {args.out_hyps_general}={len(hyps_g)}, {args.out_hyps_instructed}={len(hyps_i)}")
    if missing_ref: print(f"[WARN] missing reference for {len(missing_ref)} id(s) (first 5): {missing_ref[:5]}")
    if missing_g:   print(f"[WARN] missing general output for {len(missing_g)} id(s) (first 5): {missing_g[:5]}")
    if missing_i:   print(f"[WARN] missing instructed output for {len(missing_i)} id(s) (first 5): {missing_i[:5]}")

if __name__ == "__main__":
    main()