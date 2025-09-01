import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.stats import wilcoxon as scipy_wilcoxon
except Exception:
    scipy_wilcoxon = None


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def load_any_metric(path: Path) -> Tuple[np.ndarray, str]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    name = obj.get("metric") or path.stem

    diffs: List[float] = []

    if isinstance(obj, dict):
        if "pairs" in obj and isinstance(obj["pairs"], list):
            for p in obj["pairs"]:
                gf = _to_float(p.get("general"))
                ifv = _to_float(p.get("instructed"))
                if gf is not None and ifv is not None:
                    diffs.append(ifv - gf)

        elif "general" in obj and "instructed" in obj:
            g_list = obj.get("general", [])
            i_list = obj.get("instructed", [])
            for g, i in zip(g_list, i_list):
                gf = _to_float(g)
                ifv = _to_float(i)
                if gf is not None and ifv is not None:
                    diffs.append(ifv - gf)

        elif "items" in obj and isinstance(obj["items"], list):
            for it in obj["items"]:
                if "diff" in it:
                    d = _to_float(it.get("diff"))
                    if d is not None:
                        diffs.append(d)
                else:
                    gf = _to_float(it.get("general"))
                    ifv = _to_float(it.get("instructed"))
                    if gf is not None and ifv is not None:
                        diffs.append(ifv - gf)

    arr = np.array(diffs, dtype=float) if diffs else np.array([], dtype=float)
    return arr, name


def load_three(
    bleu: Optional[str], chrf: Optional[str], rouge: Optional[str]
) -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    for name, p in [("bleu", bleu), ("chrf", chrf), ("rouge", rouge)]:
        if p:
            diffs, inferred = load_any_metric(Path(p))
            out[(inferred or name).lower()] = diffs
    return out


def bootstrap_ci(
    diffs: np.ndarray, B: int = 10000, alpha: float = 0.05, seed: int = 42
) -> Tuple[float, float, float]:
    diffs = diffs.astype(float)
    diffs = diffs[~np.isnan(diffs)]
    n = diffs.size
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    boots = rng.choice(diffs, size=(B, n), replace=True).mean(axis=1)
    mean = float(diffs.mean())
    lo = float(np.quantile(boots, alpha / 2.0))
    hi = float(np.quantile(boots, 1.0 - alpha / 2.0))
    return mean, lo, hi


def wilcoxon_pvalue(diffs: np.ndarray) -> Tuple[float, float]:
    diffs = diffs.astype(float)
    diffs = diffs[~np.isnan(diffs)]
    if diffs.size == 0:
        return float("nan"), float("nan")

    nz = diffs[diffs != 0.0]
    if nz.size == 0:
        return 0.0, 1.0

    if scipy_wilcoxon is not None:
        try:
            stat, p = scipy_wilcoxon(
                nz, zero_method="wilcox", alternative="two-sided", method="auto"
            )
            return float(stat), float(p)
        except Exception:
            pass

    s = float(np.sum(np.sign(nz)))
    n = float(nz.size)
    z = s / math.sqrt(n)
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return float(z), float(p)


def cohens_d_paired(diffs: np.ndarray) -> float:
    diffs = diffs.astype(float)
    diffs = diffs[~np.isnan(diffs)]
    n = diffs.size
    if n < 2:
        return 0.0
    sd = float(np.std(diffs, ddof=0)) or 1e-12
    return float(np.mean(diffs) / sd)


def bh_fdr(names: List[str], pvals: List[float]) -> Dict[str, float]:
    m = len(pvals)
    clean = [
        (names[i], (1.0 if (pvals[i] is None or math.isnan(pvals[i])) else pvals[i]))
        for i in range(m)
    ]
    order = sorted(range(m), key=lambda i: clean[i][1])
    q_tmp = [0.0] * m
    min_q = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        k = m - rank + 1
        p = clean[idx][1]
        q = min(min_q, p * m / k)
        min_q = q
        q_tmp[idx] = q
    return {names[i]: q_tmp[i] for i in range(m)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bleu", help="Path to BLEU JSON")
    ap.add_argument("--chrf", help="Path to chrF JSON")
    ap.add_argument("--rouge", help="Path to ROUGE JSON")
    ap.add_argument("--output", required=True, help="Output CSV path")
    ap.add_argument("--bootstrap", type=int, default=10000, help="Bootstrap iterations")
    ap.add_argument(
        "--alpha", type=float, default=0.05, help="CI alpha (default 0.05 for 95% CI)"
    )
    ap.add_argument(
        "--wilcoxon", action="store_true", help="Run Wilcoxon signed-rank test on diffs"
    )
    ap.add_argument(
        "--fdr",
        action="store_true",
        help="Apply Benjamini–Hochberg FDR across reported metrics",
    )
    args = ap.parse_args()

    metrics_map = load_three(args.bleu, args.chrf, args.rouge)
    if not metrics_map:
        raise SystemExit("[FATAL] No metrics provided. Use --bleu/--chrf/--rouge.")

    rows: List[Tuple[str, int, float, float, float, float, float, float]] = []
    names: List[str] = []
    pvals: List[float] = []

    for name, diffs in metrics_map.items():
        mean_diff, lo, hi = bootstrap_ci(diffs, B=args.bootstrap, alpha=args.alpha)

        stat_or_z, p = (float("nan"), float("nan"))
        if args.wilcoxon:
            stat_or_z, p = wilcoxon_pvalue(diffs)

        d = cohens_d_paired(diffs)

        rows.append((name, int(diffs.size), mean_diff, lo, hi, stat_or_z, p, d))
        names.append(name)
        pvals.append(p)

    qmap: Dict[str, float] = {}
    if args.fdr and len(rows) > 0:
        qmap = bh_fdr(names, pvals)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "metric",
                "n",
                "mean_diff",
                "ci_lo",
                "ci_hi",
                "stat_or_z",
                "p",
                "q_fdr",
                "cohens_d",
            ]
        )
        for name, n, md, lo, hi, stat, p, d in rows:
            q = qmap.get(name, "")
            w.writerow([name, n, md, lo, hi, stat, p, q, d])

    print(f"[OK] wrote: {out}")


if __name__ == "__main__":
    main()
