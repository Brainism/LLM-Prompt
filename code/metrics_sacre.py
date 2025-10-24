from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Iterator

import sacrebleu
from sacrebleu.metrics import BLEU, CHRF

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
        col_ref = (
            by_norm.get("reference")
            or by_norm.get("reference_text")
            or by_norm.get("ref")
        )
        if not col_id or not col_ref:
            raise SystemExit("[FATAL] prompts CSV must have columns 'id' and 'reference'")

        for r in rdr:
            rid = str(r.get(col_id, "")).strip()
            ref = str(r.get(col_ref, "")).strip()
            if rid:
                id2ref[rid] = ref
    return id2ref

def iter_pairs_from_raw(
    raw_dir: Path,
    id2ref: Optional[Dict[str, str]],
) -> Iterator[Tuple[str, str, str, str]]:
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
                hyp = o.get("output") or ""
                ref = o.get("reference") or ""
                rid = str(o.get("id", "") or "")
                if not ref and id2ref and rid in id2ref:
                    ref = id2ref[rid]
                yield (p.name, rid, hyp, ref)

def corpus_bleu_chrf(hyps: List[str], refs: List[str]) -> Tuple[float, float]:
    if not hyps:
        return 0.0, 0.0
    bleu = BLEU(effective_order=True)
    chrf = CHRF()
    b = bleu.corpus_score(hyps, [refs]).score
    c = chrf.corpus_score(hyps, [refs]).score
    return b, c

def mode_a_main(inputs: str, out: str, prompts_csv: Optional[str], by_file: bool) -> None:
    raw_dir = Path(inputs)
    out_path = Path(out)
    id2ref = _read_prompts_csv_for_refs(Path(prompts_csv)) if prompts_csv else None

    all_hyps: List[str] = []
    all_refs: List[str] = []
    per_file: Dict[str, Dict[str, Any]] = {}

    for fp, rid, hyp, ref in iter_pairs_from_raw(raw_dir, id2ref):
        if not str(ref).strip():
            continue
        all_hyps.append(hyp or "")
        all_refs.append(ref or "")
        if by_file:
            d = per_file.setdefault(fp, {"hyps": [], "refs": []})
            d["hyps"].append(hyp or "")
            d["refs"].append(ref or "")

    b, c = corpus_bleu_chrf(all_hyps, all_refs)
    out_obj: Dict[str, Any] = {"BLEU": b, "chrF": c, "n": len(all_hyps)}

    if by_file:
        by = []
        for fname, d in sorted(per_file.items()):
            bb, cc = corpus_bleu_chrf(d["hyps"], d["refs"])
            by.append({"file": fname, "BLEU": bb, "chrF": cc, "n": len(d["hyps"])})
        out_obj["by_file"] = by

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)
    print("[OK] wrote", out_path, {"BLEU": b, "chrF": c, "n": len(all_hyps)})

def mode_b_main(refs: str, hyps_general: str, hyps_instructed: str, out_bleu: str, out_chrf: str) -> None:
    refs_lines = [ln.rstrip("\n") for ln in Path(refs).read_text(encoding="utf-8").splitlines()]
    g_lines    = [ln.rstrip("\n") for ln in Path(hyps_general).read_text(encoding="utf-8").splitlines()]
    i_lines    = [ln.rstrip("\n") for ln in Path(hyps_instructed).read_text(encoding="utf-8").splitlines()]
    if not (len(refs_lines) == len(g_lines) == len(i_lines)):
        raise SystemExit("refs/general/instructed 길이가 다릅니다.")

    bleu_g = sacrebleu.corpus_bleu(g_lines, [refs_lines])
    bleu_i = sacrebleu.corpus_bleu(i_lines, [refs_lines])
    chrf_m = sacrebleu.CHRF()
    chrf_g = chrf_m.corpus_score(g_lines, [refs_lines])
    chrf_i = chrf_m.corpus_score(i_lines, [refs_lines])

    items_bleu: List[Dict[str, Any]] = []
    items_chrf: List[Dict[str, Any]] = []
    for idx, (r, hg, hi) in enumerate(zip(refs_lines, g_lines, i_lines), 1):
        sb_g = sacrebleu.sentence_bleu(hg, [r]).score
        sb_i = sacrebleu.sentence_bleu(hi, [r]).score
        sc_g = chrf_m.sentence_score(hg, [r]).score
        sc_i = chrf_m.sentence_score(hi, [r]).score
        items_bleu.append({"id": str(idx), "general": sb_g / 100.0, "instructed": sb_i / 100.0})
        items_chrf.append({"id": str(idx), "general": sc_g / 100.0, "instructed": sc_i / 100.0})

    Path(out_bleu).parent.mkdir(parents=True, exist_ok=True)
    Path(out_chrf).parent.mkdir(parents=True, exist_ok=True)

    sig = getattr(bleu_g, "signature", None)
    with Path(out_bleu).open("w", encoding="utf-8") as f:
        json.dump({
            "metric": "bleu_sacre",
            "items": items_bleu,
            "corpus": {"general": bleu_g.score / 100.0, "instructed": bleu_i.score / 100.0},
            **({"signature": str(sig)} if sig is not None else {})
        }, f, ensure_ascii=False, indent=2)

    with Path(out_chrf).open("w", encoding="utf-8") as f:
        json.dump({
            "metric": "chrf",
            "items": items_chrf,
            "corpus": {"general": chrf_g.score / 100.0, "instructed": chrf_i.score / 100.0}
        }, f, ensure_ascii=False, indent=2)

    print("[OK] sacreBLEU/chrF ->", out_bleu, ",", out_chrf)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute BLEU/chrF (raw-dir mode OR 3-line-files mode). Exactly one mode.")
    p.add_argument("--inputs", help="results/raw directory (Mode A)")
    p.add_argument("--out", help="Output JSON path for Mode A, e.g., results/quantitative/bleu_chrf.json")
    p.add_argument("--prompts", help="(Optional, Mode A) prompts CSV with columns id,reference")
    p.add_argument("--by-file", action="store_true", help="(Mode A) also include per-file metrics")

    p.add_argument("--refs", help="(Mode B) references .txt (one per line)")
    p.add_argument("--hyps-general", help="(Mode B) general hyps .txt (one per line)")
    p.add_argument("--hyps-instructed", help="(Mode B) instructed hyps .txt (one per line)")
    p.add_argument("--out-bleu", help="(Mode B) output JSON for BLEU details")
    p.add_argument("--out-chrf", help="(Mode B) output JSON for chrF details")

    args = p.parse_args()

    mode_a = args.inputs is not None or args.out is not None
    mode_b = args.refs or args.hyps_general or args.hyps_instructed or args.out_bleu or args.out_chrf

    if mode_a and mode_b:
        p.error("Use either Mode A (--inputs/--out...) OR Mode B (--refs/--hyps-.../--out-...). Not both.")
    if not mode_a and not mode_b:
        p.error("One of the modes must be specified.")

    if mode_a:
        if not args.inputs or not args.out:
            p.error("Mode A requires both --inputs and --out.")
    else:
        miss = [k for k in ["refs", "hyps_general", "hyps_instructed", "out_bleu", "out_chrf"] if getattr(args, k) is None]
        if miss:
            p.error("Mode B requires --refs, --hyps-general, --hyps-instructed, --out-bleu, --out-chrf.")
    return args

def main():
    args = parse_args()
    if args.inputs:
        mode_a_main(inputs=args.inputs, out=args.out, prompts_csv=args.prompts, by_file=args.by_file)
    else:
        mode_b_main(
            refs=args.refs,
            hyps_general=args.hyps_general,
            hyps_instructed=args.hyps_instructed,
            out_bleu=args.out_bleu,
            out_chrf=args.out_chrf
        )

if __name__ == "__main__":
    main()