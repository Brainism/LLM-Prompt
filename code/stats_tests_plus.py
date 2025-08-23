import argparse, json, csv, math
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon

def load_diffs(fp: Path):
    obj = json.loads(fp.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    diffs = [float(it.get("diff", it.get("instructed", 0) - it.get("general", 0))) for it in items]
    return np.array(diffs, dtype=float), obj.get("metric", fp.stem)

def bootstrap_ci(diffs, B=10000, alpha=0.05, seed=42):
    rng = np.random.default_rng(seed)
    n = len(diffs)
    if n == 0:
        return (math.nan, math.nan, math.nan)
    boots = rng.choice(diffs, size=(B, n), replace=True).mean(axis=1)
    return float(diffs.mean()), float(np.percentile(boots, 100*alpha/2)), float(np.percentile(boots, 100*(1-alpha/2)))

def benjamini_hochberg(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda k: pvals[k])
    q = [0.0] * m
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        i = order[-rank]
        qval = pvals[i] * m / (i + 1)
        prev = min(prev, qval)
        q[i] = prev
    return q

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bleu", required=True)
    ap.add_argument("--chrf", required=True)
    ap.add_argument("--rouge", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--wilcoxon", action="store_true")
    ap.add_argument("--fdr", action="store_true")
    args = ap.parse_args()

    rows = []
    pvals = []
    metrics = []

    for path in [args.bleu, args.chrf, args.rouge]:
        diffs, name = load_diffs(Path(path))
        mean_diff, lo, hi = bootstrap_ci(diffs, B=args.bootstrap)

        if args.wilcoxon and len(diffs) > 0:
            valid = diffs[~np.isnan(diffs)]
            nz = valid[valid != 0.0]
            if nz.size == 0:
                p = 1.0
            else:
                try:
                    stat, p = wilcoxon(
                        nz,
                        zero_method="wilcox",
                        alternative="two-sided",
                        method="auto",
                    )
                    p = float(p)
                except ValueError:
                    p = float("nan")
        else:
            p = float("nan")

        rows.append([name, len(diffs), mean_diff, lo, hi, p, None])
        pvals.append(p)
        metrics.append(name)

    if args.fdr:
        qvals = benjamini_hochberg([p if not math.isnan(p) else 1.0 for p in pvals])
        for idx, q in enumerate(qvals):
            rows[idx][-1] = q

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "n", "mean_diff", "ci_low", "ci_high", "wilcoxon_p", "bh_fdr_q"])
        w.writerows(rows)

    print("[OK] wrote stats:", out)

if __name__ == "__main__":
    main()