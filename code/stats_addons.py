# -*- coding: utf-8 -*-
import argparse
import json
import math
from pathlib import Path

import numpy as np

try:
    from scipy.stats import wilcoxon

    SCIPY_OK = True
except Exception:
    SCIPY_OK = False


def load_pairs(path):
    """?ㅼ뼇??JSON 援ъ“瑜?寃ш퀬?섍쾶 ?쎌뼱 (general, instructed) ??諛곗뿴濡?諛섑솚"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    g, i = [], []

    def as_float(x):
        try:
            return float(x)
        except Exception:
            return np.nan

    if isinstance(data, dict):
        if "general" in data and ("instruct" in data or "instructed" in data):
            inst_key = "instruct" if "instruct" in data else "instructed"
            keys = list(data["general"].keys())
            for k in keys:
                if k in data[inst_key]:
                    g.append(as_float(data["general"][k]))
                    i.append(as_float(data[inst_key][k]))
        else:
            # {id: {general:?? instruct(ed):??} ?뺥깭
            for _, v in data.items():
                if isinstance(v, dict):
                    gval = v.get("general", v.get("base"))
                    ival = v.get("instruct", v.get("instructed"))
                    if gval is not None and ival is not None:
                        g.append(as_float(gval))
                        i.append(as_float(ival))
    elif isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                gval = row.get("general", row.get("base"))
                ival = row.get("instruct", row.get("instructed"))
                if gval is not None and ival is not None:
                    g.append(as_float(gval))
                    i.append(as_float(ival))

    g, i = np.array(g, dtype=float), np.array(i, dtype=float)
    mask = ~(np.isnan(g) | np.isnan(i))
    return g[mask], i[mask]


def cohen_d_paired(g, i):
    diff = i - g
    return float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-12))


def bootstrap_ci(diff, n_boot=10000, alpha=0.05, seed=42):
    if n_boot <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    n = len(diff)
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boot[b] = np.mean(diff[idx])
    lo = np.percentile(boot, 100 * (alpha / 2))
    hi = np.percentile(boot, 100 * (1 - alpha / 2))
    return float(lo), float(hi)


def summarize_one(name, path, n_boot, do_wilcoxon):
    g, i = load_pairs(path)
    n = len(g)
    diff = i - g
    out = {
        "metric": name,
        "n": int(n),
        "general_mean": float(np.mean(g)) if n else np.nan,
        "instruct_mean": float(np.mean(i)) if n else np.nan,
        "delta_mean": float(np.mean(diff)) if n else np.nan,
        "delta_pct": float((np.mean(diff) / (np.mean(g) + 1e-12)) * 100.0)
        if n
        else np.nan,
        "cohen_d": cohen_d_paired(g, i) if n > 1 else np.nan,
        "wilcoxon_p": np.nan,
        "boot_ci_lo": np.nan,
        "boot_ci_hi": np.nan,
    }
    if n_boot and n > 1:
        lo, hi = bootstrap_ci(diff, n_boot=n_boot)
        out["boot_ci_lo"], out["boot_ci_hi"] = lo, hi
    if do_wilcoxon and SCIPY_OK and n > 0 and np.any(diff != 0):
        try:
            stat, p = wilcoxon(
                i, g, zero_method="wilcox", alternative="two-sided", mode="auto"
            )
            out["wilcoxon_p"] = float(p)
        except Exception:
            pass
    return out


def bh_fdr(pvals, alpha=0.05):
    """Benjamini?밐ochberg FDR (return q-values in same order)"""
    arr = np.array(pvals, dtype=float)
    m = len(arr)
    order = np.argsort(arr)
    ranks = np.empty(m, dtype=int)
    ranks[order] = np.arange(1, m + 1)
    q = arr * m / ranks
    # monotone
    q_sorted = np.minimum.accumulate(q[order][::-1])[::-1]
    qvals = np.empty(m)
    qvals[order] = q_sorted
    return qvals.tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bleu", type=str, help="path to bleu_sacre.json")
    ap.add_argument("--chrf", type=str, help="path to chrf.json")
    ap.add_argument("--rouge", type=str, help="path to rouge.json")
    ap.add_argument(
        "--out", type=str, default="results/quantitative/stats_summary_enhanced.csv"
    )
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--wilcoxon", action="store_true")
    ap.add_argument("--fdr", action="store_true")
    args = ap.parse_args()

    rows, pvals = [], []
    for name, path in [("BLEU", args.bleu), ("chrF", args.chrf), ("ROUGE", args.rouge)]:
        if path and Path(path).exists():
            row = summarize_one(name, path, args.bootstrap, args.wilcoxon)
            rows.append(row)
            pvals.append(row.get("wilcoxon_p", math.nan))
    # FDR
    if args.fdr and len(rows) >= 2:
        valid_idx = [i for i, p in enumerate(pvals) if not (p is None or math.isnan(p))]
        if valid_idx:
            valid_p = [pvals[i] for i in valid_idx]
            q = bh_fdr(valid_p)
            for j, i in enumerate(valid_idx):
                rows[i]["fdr_q"] = float(q[j])

    # write CSV
    import csv

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "metric",
        "n",
        "general_mean",
        "instruct_mean",
        "delta_mean",
        "delta_pct",
        "boot_ci_lo",
        "boot_ci_hi",
        "wilcoxon_p",
        "fdr_q",
        "cohen_d",
    ]
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            if "fdr_q" not in r:
                r["fdr_q"] = ""
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"[OK] wrote {outp}")


if __name__ == "__main__":
    main()
