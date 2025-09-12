import os
import argparse
import json
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import trim_mean
import matplotlib.pyplot as plt

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def bootstrap_mean_ci(arr, nboot=10000, seed=12345):
    rng = np.random.default_rng(seed)
    boots = rng.choice(arr, size=(nboot, len(arr)), replace=True).mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(np.mean(boots)), float(lo), float(hi)

def main():
    p = argparse.ArgumentParser(description="Compute robust stats for per-item BLEU (base vs instr).")
    p.add_argument("--per_item", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv", help="per-item CSV with columns id,base,instr")
    p.add_argument("--outdir", default=r"C:\Project\LLM\analysis_outputs", help="output directory")
    p.add_argument("--nboot", type=int, default=10000, help="bootstrap iterations for CI")
    args = p.parse_args()

    outdir = ensure_dir(args.outdir)

    if not os.path.exists(args.per_item):
        raise SystemExit(f"per_item file not found: {args.per_item}")
    df = pd.read_csv(args.per_item, dtype=str)
    df['base'] = pd.to_numeric(df.get('base'), errors='coerce')
    df['instr'] = pd.to_numeric(df.get('instr'), errors='coerce')
    df = df.dropna(subset=['base','instr']).copy()
    df['delta'] = df['instr'] - df['base']

    n = int(len(df))
    mean_delta = float(df['delta'].mean())
    median_delta = float(df['delta'].median())
    trimmed10 = float(trim_mean(df['delta'].values, 0.1)) if n>0 else None

    t_res = stats.ttest_rel(df['instr'], df['base'], nan_policy='omit')
    t_stat = float(t_res.statistic) if not np.isnan(t_res.statistic) else None
    t_p = float(t_res.pvalue) if not np.isnan(t_res.pvalue) else None

    try:
        w_stat, w_p = stats.wilcoxon(df['instr'], df['base'])
        w_stat = float(w_stat); w_p = float(w_p)
    except Exception:
        w_stat = None; w_p = None

    boot_mean, ci_low, ci_high = bootstrap_mean_ci(df['delta'].values, nboot=args.nboot, seed=12345)

    summary = {
        "per_item_file": os.path.abspath(args.per_item),
        "n": n,
        "mean_base": float(df['base'].mean()),
        "mean_instr": float(df['instr'].mean()),
        "mean_delta": mean_delta,
        "median_delta": median_delta,
        "trimmed_mean_10pct": trimmed10,
        "paired_t": {"t_stat": t_stat, "p": t_p},
        "wilcoxon": {"w_stat": w_stat, "p": w_p},
        "bootstrap": {"nboot": args.nboot, "mean_boot": boot_mean, "ci95": [ci_low, ci_high]}
    }
    with open(os.path.join(outdir, "robust_stats_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    print("=== Robust stats summary ===")
    print(f"per_item: {args.per_item}")
    print(f"n = {n}")
    print(f"mean_base = {df['base'].mean():.6f}")
    print(f"mean_instr = {df['instr'].mean():.6f}")
    print(f"mean_delta = {mean_delta:.6f}")
    print(f"median_delta = {median_delta:.6f}")
    print(f"trimmed_mean (10%) = {trimmed10:.6f}")
    print(f"paired t: t={t_stat}, p={t_p}")
    print(f"wilcoxon: stat={w_stat}, p={w_p}")
    print(f"bootstrap mean (nboot={args.nboot}) = {boot_mean:.6f}, 95% CI = [{ci_low:.6f}, {ci_high:.6f}]")
    print(f"Summary JSON written to {os.path.join(outdir, 'robust_stats_summary.json')}")

    sorted_csv = os.path.join(outdir, "per_item_sorted_by_delta.csv")
    df.sort_values("delta", ascending=False).to_csv(sorted_csv, index=False)
    print("Wrote sorted per-item deltas to", sorted_csv)

    plt.rcParams.update({'figure.dpi':150, 'font.size':10})

    fig, ax = plt.subplots(figsize=(6,6))
    ax.boxplot([df['base'].values, df['instr'].values], labels=["Base","Instructed"], showmeans=True)
    ax.set_ylabel("BLEU (sacre)")
    ax.set_title(f"Paired BLEU (n={n}) Δ={mean_delta:.3f}")
    ax.grid(axis='y', linestyle=':', alpha=0.4)
    fig.savefig(os.path.join(outdir, "robust_bleu_boxplot.png"), bbox_inches='tight')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8,4))
    ax.hist(df['delta'].values, bins=60)
    ax.axvline(0, color='k', linestyle='--', linewidth=1)
    ax.set_xlabel("Δ BLEU (instr - base)")
    ax.set_title("Per-item Δ distribution")
    fig.savefig(os.path.join(outdir, "robust_delta_hist.png"), bbox_inches='tight')
    plt.close(fig)

    top10 = df.sort_values("delta", ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(10,4))
    ax.bar(top10['id'].astype(str), top10['delta'].values, color='tab:red')
    ax.set_xlabel("item id")
    ax.set_ylabel("Δ BLEU")
    ax.set_title("Top 10 Δ BLEU contributors")
    fig.savefig(os.path.join(outdir, "robust_top10_delta.png"), bbox_inches='tight')
    plt.close(fig)

    print("Saved plots to", outdir)
    print("Done.")

if __name__ == "__main__":
    main()