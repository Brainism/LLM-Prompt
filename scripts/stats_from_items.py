import json, os, math, argparse, csv, random
from typing import List, Dict, Tuple
from statistics import mean
from math import sqrt
from scipy.stats import wilcoxon

def load_items(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and "items" in obj:
        data = obj["items"]
    elif isinstance(obj, list):
        data = obj
    else:
        raise RuntimeError(f"Unsupported JSON shape: {path}")
    rows = []
    for r in data:
        try:
            b = float(r["base"]); i = float(r["instr"])
            if math.isnan(b) or math.isnan(i): continue
            rows.append({"id": r.get("id"), "base": b, "instr": i})
        except Exception:
            continue
    return rows

def cohen_d_paired(base: List[float], instr: List[float]) -> float:
    diffs = [i - b for b, i in zip(base, instr)]
    m = mean(diffs)
    if len(diffs) <= 1:
        return float("nan")
    md = mean(diffs)
    var = sum((x - md) ** 2 for x in diffs) / (len(diffs) - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    return (m / sd) if sd > 0 else float("inf") if m != 0 else 0.0

def bootstrap_ci_mean_delta(base: List[float], instr: List[float], iters=10000, alpha=0.05, seed=42) -> Tuple[float,float]:
    rnd = random.Random(seed)
    diffs = [i - b for b, i in zip(base, instr)]
    n = len(diffs)
    if n == 0:
        return float("nan"), float("nan")
    boots = []
    for _ in range(iters):
        sample = [diffs[rnd.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    lo = float(sorted(boots)[int((alpha/2)*iters)])
    hi = float(sorted(boots)[int((1 - alpha/2)*iters)])
    return lo, hi

def summarize_one(metric_name: str, path: str) -> Dict[str, object]:
    rows = load_items(path)
    base = [r["base"] for r in rows]
    instr = [r["instr"] for r in rows]
    n = len(base)
    if n == 0:
        return dict(metric=metric_name, n=0, mean_base=float("nan"), mean_instr=float("nan"),
                    delta=float("nan"), delta_pct=float("nan"), d=float("nan"),
                    ci_low=float("nan"), ci_high=float("nan"), p=float("nan"))
    mb = mean(base); mi = mean(instr)
    delta = mi - mb
    delta_pct = (delta / mb * 100.0) if mb != 0 else float("inf") if delta != 0 else 0.0
    d = cohen_d_paired(base, instr)
    ci_low, ci_high = bootstrap_ci_mean_delta(base, instr, iters=10000)
    try:
        stat, p = wilcoxon(instr, base, zero_method="wilcox", correction=False, alternative="two-sided", mode="auto")
    except Exception:
        p = float("nan")
    return dict(metric=metric_name, n=n, mean_base=mb, mean_instr=mi, delta=delta,
                delta_pct=delta_pct, d=d, ci_low=ci_low, ci_high=ci_high, p=p)

def bh_fdr(ps):
    import math
    m = len(ps)
    order = sorted(range(m), key=lambda i: (float('inf') if (ps[i] is None or math.isnan(ps[i])) else ps[i]))
    adj = [float('nan')] * m
    for rank, i in enumerate(order, start=1):
        p = ps[i]
        adj[i] = (p * m / rank) if (isinstance(p, float) and not math.isnan(p)) else float('nan')
    q = [float('nan')] * m
    min_so_far = 1.0
    for i in reversed(order):
        val = adj[i]
        if isinstance(val, float) and not math.isnan(val):
            min_so_far = min(min_so_far, val)
            q[i] = min_so_far
    return q

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rouge", default="results/quantitative/rouge.json")
    ap.add_argument("--bleu",  default="results/quantitative/bleu_sacre.json")
    ap.add_argument("--chrf",  default="results/quantitative/chrf.json")
    ap.add_argument("--out",   default="results/quantitative/stats_summary.v2.csv")
    args = ap.parse_args()

    rows = [
        summarize_one("rouge", args.rouge),
        summarize_one("bleu_sacre", args.bleu),
        summarize_one("chrf", args.chrf),
    ]
    ps = [r["p"] for r in rows]
    qs = bh_fdr([p if (isinstance(p, float) and not math.isnan(p)) else 1.0 for p in ps])
    for r, q in zip(rows, qs):
        r["q"] = q

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric","n","mean_base","mean_instr","delta","delta_%","d","CI95_low","CI95_high","p","q"])
        for r in rows:
            w.writerow([
                r["metric"], r["n"], r["mean_base"], r["mean_instr"], r["delta"], r["delta_pct"],
                r["d"], r["ci_low"], r["ci_high"], r["p"], r["q"]
            ])
    print(f"[OK] wrote {args.out}")

if __name__ == "__main__":
    main()