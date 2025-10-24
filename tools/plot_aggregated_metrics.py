import os
import argparse
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams.update({'font.size': 14})

def safe_read_csv(path):
    df = pd.read_csv(path, dtype=str)
    df = df.rename(columns=lambda c: c.strip())
    return df

def to_numeric_col(df, colnames):
    for c in colnames:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def boot_ci(data, nboot=5000, alpha=0.05):
    data = np.array(data)
    data = data[~np.isnan(data)]
    if len(data) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(0)
    means = []
    for _ in range(nboot):
        sample = rng.choice(data, size=len(data), replace=True)
        means.append(np.nanmean(sample))
    lo = np.percentile(means, 100 * (alpha/2))
    hi = np.percentile(means, 100 * (1-alpha/2))
    return (lo, hi)

def save_fig(fig, outpath, dpi=300):
    fig.savefig(outpath, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print("Saved:", outpath)

def mean_bar_by_mode(df, outdir):
    key = 'mode'
    if key not in df.columns:
        print("No 'mode' column for mean_bar_by_mode, skipping")
        return
    groups = df.groupby(key)
    modes = []
    means = []
    cis = []
    ns = []
    for name, g in groups:
        arr = g['bleu'].dropna().astype(float).values
        modes.append(str(name))
        ns.append(len(arr))
        if len(arr)>0:
            means.append(np.mean(arr))
            cis.append(boot_ci(arr))
        else:
            means.append(np.nan)
            cis.append((np.nan,np.nan))
    fig, ax = plt.subplots(figsize=(6,5))
    x = np.arange(len(modes))
    ax.bar(x, means)
    yerr = np.array([[means[i]-cis[i][0] if not math.isnan(means[i]) else 0 for i in range(len(means))],
                     [cis[i][1]-means[i] if not math.isnan(means[i]) else 0 for i in range(len(means))]])
    ax.errorbar(x, means, yerr=yerr, fmt='none', capsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(modes, rotation=0)
    ax.set_ylabel('BLEU (sacre)')
    title = f"BLEU mean by mode (n per mode = {', '.join([f'{m}:{n}' for m,n in zip(modes,ns)])})"
    ax.set_title(title)
    out = os.path.join(outdir, "mean_bleu_by_mode.png")
    save_fig(fig, out)

def mean_bar_by_model_mode(df, outdir):
    if 'model' not in df.columns:
        return
    df2 = df.copy()
    df2 = df2.dropna(subset=['bleu'])
    grouped = df2.groupby(['model','mode'])['bleu'].mean().unstack(fill_value=np.nan)
    if grouped.shape[0] == 0:
        return
    fig, ax = plt.subplots(figsize=(max(6, grouped.shape[0]*0.8),5))
    idx = np.arange(len(grouped.index))
    width = 0.35
    cols = list(grouped.columns)
    for i,c in enumerate(cols):
        ax.bar(idx + i*width, grouped[c].values, width=width, label=str(c))
    ax.set_xticks(idx + width*(len(cols)-1)/2)
    ax.set_xticklabels(grouped.index, rotation=30, ha='right')
    ax.set_ylabel('BLEU (sacre)')
    ax.set_title("BLEU by model and mode (means)")
    ax.legend(title="mode")
    out = os.path.join(outdir, "mean_bleu_by_model_mode.png")
    save_fig(fig, out)

def bleu_boxplot_by_mode(df, outdir):
    if 'mode' not in df.columns:
        return
    groups = []
    labels = []
    for name, g in df.groupby('mode'):
        arr = g['bleu'].dropna().astype(float).values
        if len(arr)>0:
            groups.append(arr)
            labels.append(str(name))
    if not groups:
        return
    fig, ax = plt.subplots(figsize=(6,5))
    ax.boxplot(groups, labels=labels, showmeans=True)
    ax.set_ylabel('BLEU (sacre)')
    ax.set_title('BLEU distribution by mode')
    out = os.path.join(outdir, "bleu_boxplot_by_mode.png")
    save_fig(fig, out)

def bleu_vs_chrf_scatter(df, outdir):
    if 'bleu' not in df.columns or 'chrf' not in df.columns:
        return
    sub = df.dropna(subset=['bleu','chrf'])
    if sub.shape[0] == 0:
        return
    x = sub['bleu'].astype(float)
    y = sub['chrf'].astype(float)
    fig, ax = plt.subplots(figsize=(6,6))
    ax.scatter(x, y, alpha=0.7)
    mn = min(x.min(), y.min())
    mx = max(x.max(), y.max())
    ax.plot([mn, mx], [mn, mx], linestyle='--', linewidth=1)
    ax.set_xlabel('BLEU (sacre)')
    ax.set_ylabel('chrF')
    ax.set_title('Per-row BLEU vs chrF')
    out = os.path.join(outdir, "bleu_vs_chrf_scatter.png")
    save_fig(fig, out)

def compliance_by_mode(df, outdir):
    if 'mode' not in df.columns or 'compliance' not in df.columns:
        return
    dfc = df.copy()
    dfc['compliance_num'] = pd.to_numeric(dfc['compliance'], errors='coerce')
    agg = dfc.groupby('mode')['compliance_num'].agg(lambda s: np.nanmean(s.values))
    if agg.isnull().all():
        print("compliance numeric all NaN; skipping compliance_by_mode")
        return
    fig, ax = plt.subplots(figsize=(6,5))
    x = np.arange(len(agg.index))
    ax.bar(x, agg.values)
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=0)
    ax.set_ylabel('Compliance (pass rate)')
    ax.set_title('Compliance pass rate by mode')
    out = os.path.join(outdir, "compliance_by_mode.png")
    save_fig(fig, out)

def metrics_summary_text(stats_csv, outdir):
    try:
        s = pd.read_csv(stats_csv)
    except Exception as e:
        print("Could not read stats CSV:", e)
        return
    lines = []
    for _, row in s.iterrows():
        metric = str(row.get('metric',''))
        n = int(row.get('n',0))
        mb = row.get('mean_base','')
        mi = row.get('mean_instr','')
        d = row.get('delta','')
        p = row.get('p','')
        lines.append(f"{metric:12s} | n={n:>2d} | base={mb:8} | instr={mi:8} | Δ={d:8} | p={p}")
    fig_w = 1200/300
    fig_h = max(1.5, len(lines)*0.3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis('off')
    text = "\n".join(lines)
    ax.text(0, 1, text, fontfamily='monospace', fontsize=12, va='top')
    out = os.path.join(outdir, "metrics_summary_text.png")
    save_fig(fig, out)

def main():
    parser = argparse.ArgumentParser(description="Plot aggregated metrics CSV")
    parser.add_argument('--input', required=True)
    parser.add_argument('--stats', required=False)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    inp = args.input
    stats = args.stats
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)

    print("Loading:", inp)
    df = safe_read_csv(inp)

    df = df.dropna(how='all')
    rename_map = {}
    for c in list(df.columns):
        lc = c.lower()
        if lc in ('bleu','bleu_sacre','bleu_sacre_score'):
            rename_map[c] = 'bleu'
        if lc in ('rouge','rouge_l','rouge_l_f'):
            rename_map[c] = 'rouge_l'
        if 'chrf' in lc:
            rename_map[c] = 'chrf'
        if 'compliance' in lc or 'pass' in lc:
            rename_map[c] = 'compliance'
        if lc in ('model','model_name'):
            rename_map[c] = 'model'
        if lc in ('mode','group','condition'):
            rename_map[c] = 'mode'
    df = df.rename(columns=rename_map)

    df = to_numeric_col(df, ['bleu','chrf','rouge_l','compliance'])

    print("Columns after normalization:", df.columns.tolist())
    print("Row count:", len(df))
    print(df.head(5).to_string(index=False))

    mean_bar_by_mode(df, outdir)
    mean_bar_by_model_mode(df, outdir)
    bleu_boxplot_by_mode(df, outdir)
    bleu_vs_chrf_scatter(df, outdir)
    compliance_by_mode(df, outdir)

    if stats:
        metrics_summary_text(stats, outdir)

    print("Done. Figures in:", outdir)

if __name__ == "__main__":
    main()