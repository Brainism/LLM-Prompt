from __future__ import annotations

import argparse
import csv
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterator

from rouge_score import rouge_scorer

def _read_prompts_csv_for_refs(csv_path: Path) -> Dict[str, str]:
    if not csv_path.exists():
        raise SystemExit(f"[FATAL] prompts CSV not found: {csv_path}")

    def _norm(s: str) -> str:
        return (s or "").strip().lstrip("\ufeff").lower()

    id2ref: Dict[str, str] = {}
    with csv_path.open("r", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        fields = rdr.fieldnames or []
        by_norm = {_norm(c): c for c in fields}

        col_id = by_norm.get("id")
        col_ref = by_norm.get("reference") or by_norm.get("reference_text") or by_norm.get("ref")
        if not col_id or not col_ref:
            raise SystemExit("[FATAL] prompts CSV must have columns 'id' and 'reference'")

        for r in rdr:
            rid = str(r.get(col_id, "")).strip()
            ref = str(r.get(col_ref, "")).strip()
            if rid:
                id2ref[rid] = ref
    return id2ref

def _rougeL_f(ref: str, hyp: str, scorer: rouge_scorer.RougeScorer) -> float:
    if not (ref or "").strip():
        return 0.0
    return scorer.score(ref, hyp)["rougeL"].fmeasure

def _iter_pairs_from_raw(raw_dir: Path, id2ref: Optional[Dict[str, str]]) -> Iterator[Tuple[str, str, str, str]]:
    for p in raw_dir.glob("*.jsonl"):
        with p.open("r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    o = json.loads(ln)
                except Exception:
                    continue
                rid = str(o.get("id", "") or "")
                hyp = o.get("output", "") or ""
                ref = o.get("reference", "") or ""
                if not ref and id2ref and rid in id2ref:
                    ref = id2ref[rid]
                yield (p.name, rid, hyp, ref)

def _mode_a_main(inputs: str, out: str, prompts_csv: Optional[str], by_file: bool) -> None:
    raw_dir = Path(inputs)
    out_path = Path(out)
    id2ref = _read_prompts_csv_for_refs(Path(prompts_csv)) if prompts_csv else None

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    total_f, n = 0.0, 0
    file_aggr: Dict[str, Dict[str, Any]] = {}  # fname -> {"sum": float, "n": int}

    for fname, rid, hyp, ref in _iter_pairs_from_raw(raw_dir, id2ref):
        if not str(ref).strip():
            continue
        f = _rougeL_f(ref, hyp, scorer)
        total_f += f
        n += 1
        if by_file:
            d = file_aggr.setdefault(fname, {"sum": 0.0, "n": 0})
            d["sum"] += f
            d["n"] += 1

    res: Dict[str, Any] = {"rougeL_f1_mean": (total_f / n) if n else 0.0, "n": n}
    if by_file:
        res["by_file"] = [
            {"file": k, "rougeL_f1_mean": (v["sum"] / v["n"]) if v["n"] else 0.0, "n": v["n"]}
            for k, v in sorted(file_aggr.items())
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("[OK] wrote", out_path, res)

def _read_reference_legacy(path: str) -> Dict[str, str]:
    ref: Dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        ref[str(obj["id"])] = str(obj["reference_text"])
    return ref


def _load_outputs_legacy(dirpath: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for p in Path(dirpath).glob("*.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
        items.append(obj)
    return items


def _mode_b_main(inputs_dir: str, reference_path: str, out_path: str) -> None:
    ref = _read_reference_legacy(reference_path)
    outs = _load_outputs_legacy(inputs_dir)
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    per_item: List[Dict[str, Any]] = []
    by_group: Dict[str, List[float]] = defaultdict(list)

    for o in outs:
        sid = str(o.get("id"))
        hyp = str(o.get("output_text", ""))
        grp = str(o.get("prompt_type", "unknown"))
        gt = ref.get(sid, "")
        f = _rougeL_f(gt, hyp, scorer)
        per_item.append(
            {"id": sid, "prompt_type": grp, "rougeL_p": None, "rougeL_r": None, "rougeL_f": f}
        )
        by_group[grp].append(f)

    summary = {
        "overall_mean_f": (sum(x["rougeL_f"] for x in per_item) / max(len(per_item), 1)) if per_item else 0.0,
        "group_mean_f": {k: (sum(v) / max(len(v), 1)) for k, v in by_group.items()},
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps({"per_item": per_item, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] ROUGE-L -> {out_path}")

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ROUGE-L evaluator (Mode A: raw-dir *.jsonl / Mode B: legacy refs+dir). Exactly one mode."
    )
    p.add_argument("--inputs", help="Directory to read from (both modes use this differently)")
    p.add_argument("--out", help="(Mode A) output JSON path, e.g., results/quantitative/rouge_scores.json")
    p.add_argument("--prompts", help="(Optional, Mode A) prompts CSV (must have id,reference columns)")
    p.add_argument("--by-file", action="store_true", help="(Mode A) also include per-file mean")

    p.add_argument("--reference", help="(Mode B) JSONL with {'id','reference_text'} per line")
    p.add_argument("--output", help="(Mode B) output JSON path (per_item + summary) for legacy mode")

    args = p.parse_args()

    mode_a = (args.out is not None) or (args.prompts is not None) or args.by_file
    mode_b = (args.reference is not None) or (args.output is not None)

    if mode_a and mode_b:
        p.error("Use either Mode A (--out/...) OR Mode B (--reference/--output), not both.")

    if mode_a:
        if not args.inputs or not args.out:
            p.error("Mode A requires both --inputs and --out.")
    else:
        if not args.inputs or not args.reference or not args.output:
            p.error("Mode B requires --inputs, --reference and --output.")
    return args


def main():
    args = parse_args()
    if args.out:
        _mode_a_main(inputs=args.inputs, out=args.out, prompts_csv=args.prompts, by_file=bool(args.by_file))
    else:
        _mode_b_main(inputs_dir=args.inputs, reference_path=args.reference, out_path=args.output)


if __name__ == "__main__":
    main()