from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Dict, List, Tuple, Optional

import numpy as np

try:
    from scipy.stats import wilcoxon
except Exception as e:
    raise ImportError("SciPy가 필요합니다. `pip install scipy` 후 다시 실행하세요.") from e

def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg FDR(q)."""
    n = len(pvals)
    if n == 0:
        return pvals
    order = np.argsort(pvals)
    q = np.empty(n, dtype=float)
    cumulative = 1.0
    for rank, idx in enumerate(order[::-1], start=1):
        val = pvals[idx] * n / (n - rank + 1)
        cumulative = min(cumulative, val)
        q[idx] = cumulative
    return np.clip(q, 0, 1)


def paired_bootstrap_ci(
    g: np.ndarray, i: np.ndarray, B: int = 10000, alpha: float = 0.05, seed: int = 123
) -> Tuple[float, float]:
    """Percentile CI for mean(i - g)."""
    rng = np.random.default_rng(seed)
    n = len(g)
    if n == 0:
        return (0.0, 0.0)
    idx = rng.integers(0, n, size=(B, n))
    diffs = (i[idx] - g[idx]).mean(axis=1)
    lo = np.percentile(diffs, 100 * alpha / 2)
    hi = np.percentile(diffs, 100 * (1 - alpha / 2))
    return float(lo), float(hi)

def _infer_metric_key_from_per_item(per_item: List[dict]) -> str:
    """
    From a per_item record, infer the numeric metric key.
    Priority: rougeL_f, bleu4, rougeL, bleu, score, value
    """
    priority = ["rougeL_f", "bleu4", "rougeL", "bleu", "score", "value"]
    if not per_item:
        raise ValueError("per_item is empty")
    sample = per_item[0]
    numeric_keys = [
        k for k, v in sample.items()
        if k not in ("id", "prompt_type", "prompt_id") and isinstance(v, (int, float))
    ]
    for k in priority:
        if k in sample and isinstance(sample[k], (int, float)):
            return k
    if numeric_keys:
        return numeric_keys[0]
    raise ValueError("No numeric metric key found in per_item")


def load_pairs(path: pathlib.Path) -> List[Tuple[str, float, float]]:
    """
    Normalize various JSON schemas to [(id, general, instructed), ...].
    Supported:
      (A) {"metric":"...","items":[{"id","general","instructed"} ...]}
      (B) {"general":[{"id","score"} ...], "instructed":[{"id","score"} ...]}
      (C) {"per_item":[{"id","prompt_type":"general|instructed", "<metric>": number} ...]}
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs: List[Tuple[str, float, float]] = []

    if "items" in data and isinstance(data["items"], list) and data["items"]:
        it0 = data["items"][0]
        if ("general" in it0 and "instructed" in it0) or ("modes" in it0):
            for it in data["items"]:
                pid = str(it.get("id") or it.get("prompt_id") or len(pairs))
                if "general" in it and "instructed" in it:
                    g, ins = it["general"], it["instructed"]
                else:
                    modes = it.get("modes", {})
                    g, ins = modes.get("general"), modes.get("instructed")
                if g is not None and ins is not None:
                    pairs.append((pid, float(g), float(ins)))
            if pairs:
                return pairs
            
    if "general" in data and "instructed" in data:
        gmap = {
            str(d["id"]): float(d.get("score") or d.get("value") or 0.0)
            for d in data["general"]
        }
        imap = {
            str(d["id"]): float(d.get("score") or d.get("value") or 0.0)
            for d in data["instructed"]
        }
        ids = sorted(set(gmap) & set(imap))
        return [(pid, gmap[pid], imap[pid]) for pid in ids]

    if "per_item" in data and isinstance(data["per_item"], list):
        per = data["per_item"]
        mkey = _infer_metric_key_from_per_item(per)
        gmap: Dict[str, float] = {}
        imap: Dict[str, float] = {}
        for x in per:
            pid = str(x.get("id") or x.get("prompt_id") or len(gmap) + len(imap))
            mode = str(x.get("prompt_type") or x.get("mode") or "").lower()
            val = x.get(mkey)
            if val is None:
                continue
            if mode.startswith("gen"):
                gmap[pid] = float(val)
            elif mode.startswith("instr"):
                imap[pid] = float(val)
        ids = sorted(set(gmap) & set(imap))
        if not ids:
            raise ValueError(
                "per_item present but no overlapping ids between general and instructed"
            )
        return [(pid, gmap[pid], imap[pid]) for pid in ids]

    raise ValueError(f"Unsupported JSON schema in {path}")

def summarize(pairs: List[Tuple[str, float, float]]) -> Dict:
    g = np.array([g for _, g, _ in pairs], dtype=float)
    i = np.array([i for *_, i in pairs], dtype=float)
    diff = i - g
    n = len(diff)
    mean_g, mean_i = float(g.mean()), float(i.mean())
    mean_diff = float(diff.mean())
    sd_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    d = mean_diff / sd_diff if sd_diff > 0 else float("nan")
    try:
        p = float(wilcoxon(i, g, zero_method="pratt", alternative="two-sided").pvalue)
    except Exception:
        p = 1.0
    ci_lo, ci_hi = paired_bootstrap_ci(g, i, B=10000, alpha=0.05)
    return dict(
        n=n,
        mean_base=mean_g,
        mean_instr=mean_i,
        mean_diff=mean_diff,
        sd_diff=sd_diff,
        d=d,
        ci_low=ci_lo,
        ci_high=ci_hi,
        p_wilcoxon=p,
    )

def _search_dirs() -> List[pathlib.Path]:
    """Search up to 3 levels up for results/quantitative/."""
    here = pathlib.Path.cwd()
    dirs = [here / "results" / "quantitative"]
    p = here
    for _ in range(3):
        p = p.parent
        dirs.append(p / "results" / "quantitative")
    return [d for d in dirs if d.exists() and d.is_dir()]


def _try_load_metric_name(p: pathlib.Path) -> Optional[str]:
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        m = obj.get("metric")
        if not m:
            name = p.stem.lower()
            if "rouge" in name:
                m = "rouge"
            elif "bleu" in name:
                m = "bleu"
            elif "chrf" in name:
                m = "chrf"
            elif "codebleu" in name:
                m = "codebleu"
            else:
                m = None
        _ = load_pairs(p)
        return m or p.stem
    except Exception:
        return None


def discover_metric_files() -> Dict[str, pathlib.Path]:
    """Pick suitable metric files from discovered folders."""
    candidates: Dict[str, pathlib.Path] = {}
    prefs = {
        "rouge": ["rouge_corpus", "rouge_l_f1_corpus", "rouge", "rouge_l"],
        "bleu":  ["bleu_sacre", "bleu", "codebleu"],
        "chrf":  ["chrf", "chrf_sacre"],
    }
    for d in _search_dirs():
        for p in sorted(d.glob("*.json")):
            m = _try_load_metric_name(p)
            if not m:
                continue
            ml = m.lower()
            bucket = None
            if "rouge" in ml:
                bucket = "rouge"
            elif "codebleu" in ml or ml == "bleu":
                bucket = "bleu"
            elif "chrf" in ml:
                bucket = "chrf"
            if not bucket:
                continue
            if bucket not in candidates:
                candidates[bucket] = p
            else:
                new_rank = next((i for i, k in enumerate(prefs[bucket]) if k in p.stem.lower()), 99)
                old_rank = next((i for i, k in enumerate(prefs[bucket]) if k in candidates[bucket].stem.lower()), 99)
                if new_rank < old_rank:
                    candidates[bucket] = p
    return candidates

def _fmt4(x: float) -> str:
    if x != x:
        return "nan"
    return f"{x:.4f}"


def print_table(rows: List[Dict]) -> None:
    headers = ["metric", "n", "mean_base", "mean_instr", "delta", "d", "CI95_low", "CI95_high", "p", "q"]
    colw = {h: max(len(h), 8) for h in headers}
    for r in rows:
        colw["metric"] = max(colw["metric"], len(str(r["metric"])))

    def fmt_row(r: Dict) -> List[str]:
        return [
            str(r["metric"]).ljust(colw["metric"]),
            str(r["n"]).rjust(colw["n"]),
            _fmt4(r["mean_base"]).rjust(colw["mean_base"]),
            _fmt4(r["mean_instr"]).rjust(colw["mean_instr"]),
            _fmt4(r["mean_diff"]).rjust(colw["delta"]),
            _fmt4(r["d"]).rjust(colw["d"]),
            _fmt4(r["ci_low"]).rjust(colw["CI95_low"]),
            _fmt4(r["ci_high"]).rjust(colw["CI95_high"]),
            _fmt4(r["p_wilcoxon"]).rjust(colw["p"]),
            _fmt4(r["q_fdr"]).rjust(colw["q"]),
        ]

    line = " | ".join([
        "metric".ljust(colw["metric"]),
        "n".rjust(colw["n"]),
        "mean_base".rjust(colw["mean_base"]),
        "mean_instr".rjust(colw["mean_instr"]),
        "delta".rjust(colw["delta"]),
        "d".rjust(colw["d"]),
        "CI95_low".rjust(colw["CI95_low"]),
        "CI95_high".rjust(colw["CI95_high"]),
        "p".rjust(colw["p"]),
        "q".rjust(colw["q"]),
    ])
    print(line)
    print("-" * len(line))
    for r in rows:
        print(" | ".join(fmt_row(r)))

def parse_args():
    ap = argparse.ArgumentParser(description="Paired stats with autodiscovery.")
    ap.add_argument("--rouge", type=pathlib.Path, help="ROUGE json")
    ap.add_argument("--bleu", type=pathlib.Path, help="BLEU/CodeBLEU json")
    ap.add_argument("--chrf", type=pathlib.Path, help="chrF json")
    ap.add_argument("--output", type=pathlib.Path, default=pathlib.Path("results/stats_summary.csv"))
    ap.add_argument("--dry-run", action="store_true", help="자동 탐색 결과만 출력하고 종료")
    return ap.parse_args()


def main():
    args = parse_args()

    if not any([args.rouge, args.bleu, args.chrf]):
        discovered = discover_metric_files()
        args.rouge = args.rouge or discovered.get("rouge")
        args.bleu  = args.bleu  or discovered.get("bleu")
        args.chrf  = args.chrf  or discovered.get("chrf")

    if args.dry_run:
        print("[auto-discovery]")
        print("  rouge:", args.rouge)
        print("  bleu :", args.bleu)
        print("  chrf :", args.chrf)
        return

    rows: List[Dict] = []
    used_paths: List[pathlib.Path] = []
    for pth in [args.rouge, args.bleu, args.chrf]:
        if not pth:
            continue
        used_paths.append(pth)
        pairs = load_pairs(pth)
        res = summarize(pairs)
        try:
            metric = json.loads(pth.read_text(encoding="utf-8")).get("metric", pth.stem)
        except Exception:
            metric = pth.stem
        rows.append({"metric": metric, "level": "global", **res})

    if not rows:
        print("❌ 사용할 지표 파일을 찾지 못했습니다.")
        print("   - 자동 탐색 경로: ./results/quantitative/ (또는 상위 폴더의 동일 경로)")
        print("   - 또는 직접 지정: --rouge path.json --bleu path.json --chrf path.json")
        sys.exit(2)

    pvals = np.array([r["p_wilcoxon"] for r in rows], dtype=float)
    qvals = bh_fdr(pvals) if len(pvals) else np.array([])
    for r, q in zip(rows, qvals):
        r["q_fdr"] = float(q)

    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "metric", "level", "n",
        "mean_base", "mean_instr", "mean_diff", "sd_diff", "d",
        "ci_low", "ci_high", "p_wilcoxon", "q_fdr",
    ]
    with out.open("w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join([
                str(r["metric"]), str(r["level"]), f"{r['n']}",
                f"{r['mean_base']:.4f}", f"{r['mean_instr']:.4f}", f"{r['mean_diff']:.4f}",
                f"{r['sd_diff']:.4f}" if not np.isnan(r['sd_diff']) else "nan",
                f"{r['d']:.4f}" if not np.isnan(r['d']) else "nan",
                f"{r['ci_low']:.4f}", f"{r['ci_high']:.4f}",
                f"{r['p_wilcoxon']:.4f}", f"{r.get('q_fdr', 1.0):.4f}",
            ]) + "\n")

    print_table(rows)
    print(f"\n[OK] stats -> {out}")
    if used_paths:
        print("used files:")
        for p in used_paths:
            print(" -", p)


if __name__ == "__main__":
    main()