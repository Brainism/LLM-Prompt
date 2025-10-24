import argparse, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

plt.style.use('classic')

def save_fig(fig, path, dpi=300):
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print("Saved:", path)

def boxplot_paired(per_item_csv, outdir):
    df = pd.read_csv(per_item_csv, dtype={"id":str})
    df = df.dropna(subset=["base","instr"])
    base = df["base"].values
    instr = df["instr"].values
    fig, ax = plt.subplots(figsize=(8,6))
    ax.boxplot([base, instr], labels=["Base","Instructed"], showmeans=True)
    ax.set_ylabel("BLEU (sacre)")
    ax.set_title(f"Paired BLEU (n={len(df)}) Δ={np.round(np.mean(instr-base),3)}")
    save_fig(fig, os.path.join(outdir, "bleu_boxplot.png"))

def bootstrap_delta_hist(per_item_csv, outdir, nboot=5000):
    df = pd.read_csv(per_item_csv, dtype={"id":str}).dropna(subset=["base","instr"])
    deltas = (df["instr"] - df["base"]).values
    boots = []
    n = len(deltas)
    for i in range(nboot):
        s = np.random.choice(deltas, size=n, replace=True)
        boots.append(np.mean(s))
    boots = np.array(boots)
    fig, ax = plt.subplots(figsize=(10,5))
    ax.hist(boots, bins=60)
    mean = boots.mean()
    ci = np.percentile(boots, [2.5,97.5])
    ax.axvline(0, color='k', linestyle='--')
    ax.axvline(mean, color='r', linewidth=2)
    ax.set_xlabel("Δ BLEU (Instructed - Base)")
    ax.set_title(f"Bootstrap Δ BLEU (mean={mean:.3f}, 95% CI=[{ci[0]:.3f},{ci[1]:.3f}])")
    save_fig(fig, os.path.join(outdir, "bleu_bootstrap_delta.png"))

def bleu_vs_chrf_scatter(aggregated_csv, outdir):
    df = pd.read_csv(aggregated_csv)
    if 'bleu' not in df.columns or 'chrf' not in df.columns:
        print("No bleu/chrf in aggregated CSV -> skipping scatter.")
        return
    d = df.dropna(subset=['bleu','chrf'])
    if len(d)==0:
        print("No rows for scatter.")
        return
    fig, ax = plt.subplots(figsize=(6,6))
    ax.scatter(d['bleu'], d['chrf'], alpha=0.7)
    if len(d) > 1:
        m,b = np.polyfit(d['bleu'], d['chrf'],1)
        xs = np.linspace(d['bleu'].min(), d['bleu'].max(), 100)
        ax.plot(xs, m*xs+b, '--')
    ax.set_xlabel("BLEU (sacre)")
    ax.set_ylabel("chrF")
    ax.set_title("Per-row BLEU vs chrF")
    save_fig(fig, os.path.join(outdir, "bleu_vs_chrf_scatter.png"))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--per_item", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv")
    p.add_argument("--aggregated", default=r"C:\Project\LLM\figs\aggregated_metrics_fixed.csv")
    p.add_argument("--outdir", default=r"C:\Project\LLM\figs\generated")
    args = p.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    boxplot_paired(args.per_item, args.outdir)
    bootstrap_delta_hist(args.per_item, args.outdir, nboot=5000)
    bleu_vs_chrf_scatter(args.aggregated, args.outdir)
    print("All plots attempted. Check:", args.outdir)

if __name__ == "__main__":
    main()