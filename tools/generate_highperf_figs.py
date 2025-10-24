import os
import argparse
import json
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

plt.switch_backend('agg')

def ensure_out(dirpath):
    os.makedirs(dirpath, exist_ok=True)

def savefig(fig, path, dpi=600):
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    print("Saved:", path)

def plot_metric_bars(df_stats, outdir):
    metrics = df_stats['metric'].tolist()
    for _, row in df_stats.iterrows():
        metric = str(row['metric'])
        n = int(row['n']) if not math.isnan(row['n']) else None
        base = float(row['mean_base'])
        instr = float(row['mean_instr'])
        pval = row.get('p', None)
        ci_low = row.get('CI95_low', None)
        ci_high = row.get('CI95_high', None)

        fig, ax = plt.subplots(figsize=(5,4))
        ax.bar([0,1], [base, instr], tick_label=["Base","Instructed"], alpha=0.92)
        ax.set_ylabel(metric)
        title = f"{metric} (n={n})" if n else f"{metric}"
        ax.set_title(title)
        for i, v in enumerate([base, instr]):
            ax.text(i, v + max(0.01, 0.01 * max(base, instr)), f"{v:.3f}", ha='center', va='bottom', fontsize=9)
        if (ci_low is not None) and (ci_high is not None):
            ann = f"Δ 95% CI = [{ci_low:.3f}, {ci_high:.3f}]"
            ax.text(0.5, -0.16, ann, transform=ax.transAxes, ha='center', fontsize=9)
        if pval is not None and str(pval) != "":
            ax.text(0.95, 0.95, f"p={float(pval):.3g}", transform=ax.transAxes, ha='right', va='top', fontsize=9)
        fig.tight_layout()
        fname = os.path.join(outdir, f"{metric}_mean_bar.png")
        savefig(fig, fname)
        plt.close(fig)

def plot_paired_bleu(bleu_json_path, outdir, nboot=5000, seed=42):
    with open(bleu_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    base = np.array([d.get("base", np.nan) for d in data], dtype=float)
    instr = np.array([d.get("instr", np.nan) for d in data], dtype=float)
    mask = (~np.isnan(base)) & (~np.isnan(instr))
    base = base[mask]
    instr = instr[mask]
    n = len(base)
    if n == 0:
        print("No paired BLEU scores found; skipping BLEU plots.")
        return
    mean_base = base.mean()
    mean_instr = instr.mean()
    delta = mean_instr - mean_base

    fig, ax = plt.subplots(figsize=(6,4))
    ax.boxplot([base, instr], showmeans=True, patch_artist=False)
    ax.set_xticklabels(["Base", "Instructed"])
    ax.set_ylabel("BLEU (sacre)")
    ax.set_title(f"Paired BLEU (n={n}) Δ={delta:.3f}")
    savefig(fig, os.path.join(outdir, "bleu_boxplot.png"))
    plt.close(fig)

    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(nboot):
        idx = rng.integers(0, n, n)
        diffs.append(np.mean(instr[idx]) - np.mean(base[idx]))
    diffs = np.array(diffs)
    ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])
    fig, ax = plt.subplots(figsize=(6,3))
    ax.hist(diffs, bins=60, edgecolor='black', linewidth=0.3)
    ax.axvline(0, color='k', linestyle='--', linewidth=1)
    ax.axvline(diffs.mean(), color='r', linestyle='-', linewidth=1)
    ax.set_xlabel("Δ BLEU (Instructed - Base)")
    ax.set_title(f"Bootstrap Δ BLEU (mean={diffs.mean():.3f}, 95% CI=[{ci_low:.3f},{ci_high:.3f}])")
    savefig(fig, os.path.join(outdir, "bleu_bootstrap_delta.png"))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5,5))
    ax.scatter(base, instr, alpha=0.7)
    mn = min(base.min(), instr.min()); mx = max(base.max(), instr.max())
    ax.plot([mn, mx], [mn, mx], linestyle='--', linewidth=0.8)
    ax.set_xlabel("Base BLEU")
    ax.set_ylabel("Instructed BLEU")
    ax.set_title("Per-item BLEU (Base vs Instructed)")
    savefig(fig, os.path.join(outdir, "bleu_scatter.png"))
    plt.close(fig)

    try:
        w = stats.wilcoxon(instr, base)
        wilcoxon_p = float(w.pvalue)
    except Exception:
        wilcoxon_p = None
    d = instr - base
    cohen_d = np.mean(d) / (np.std(d, ddof=1) if np.std(d, ddof=1) != 0 else float('nan'))

    summary = {
        "n": int(n),
        "mean_base": float(mean_base),
        "mean_instr": float(mean_instr),
        "delta": float(delta),
        "bootstrap_mean": float(diffs.mean()),
        "bootstrap_ci_low": float(ci_low),
        "bootstrap_ci_high": float(ci_high),
        "wilcoxon_p": wilcoxon_p,
        "cohen_d": float(cohen_d)
    }
    with open(os.path.join(outdir, "bleu_paired_summary_generated.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Saved BLEU summary JSON.")

def plot_compliance_csv(comp_csv_path, outdir):
    df = pd.read_csv(comp_csv_path)
    if df.shape[1] < 2:
        print("Compliance CSV has insufficient columns. Need at least scenario + one mode.")
        return
    scenario_col = df.columns[0]
    mode_cols = [c for c in df.columns if c != scenario_col]
    df_plot = df.set_index(scenario_col)[mode_cols].fillna(0.0)
    df_plot['avg'] = df_plot.mean(axis=1)
    df_plot = df_plot.sort_values('avg', ascending=False)
    df_plot = df_plot.drop(columns=['avg'])
    scenarios = df_plot.index.astype(str).tolist()
    modes = df_plot.columns.tolist()
    x = np.arange(len(scenarios))
    width = 0.8 / max(1, len(modes))

    fig, ax = plt.subplots(figsize=(max(8, 0.5*len(scenarios)), 5))
    for i, mode in enumerate(modes):
        vals = df_plot[mode].values
        ax.bar(x + (i - (len(modes)-1)/2)*width, vals, width=width, label=str(mode))
    ax.set_xticks(x)
    ax.set_xticklabels([s if len(s) <= 25 else s[:22] + '...' for s in scenarios], rotation=45, ha='right')
    ax.set_ylabel("Compliance (pass rate)")
    ax.set_title("Compliance by scenario")
    ax.legend(fontsize=9)
    fig.tight_layout()
    savefig(fig, os.path.join(outdir, "compliance_by_scenario_grouped.png"))
    df_plot.to_csv(os.path.join(outdir, "compliance_by_scenario_used.csv"))

def render_error_html_tables(error_html_path, outdir):
    try:
        tables = pd.read_html(error_html_path)
    except Exception as e:
        print("Could not parse error HTML:", e)
        return
    for i, tbl in enumerate(tables[:2]):
        fig, ax = plt.subplots(figsize=(10, max(2, 0.4*len(tbl))))
        ax.axis('off')
        ax.set_title(("Top 10 ΔBLEU" if i == 0 else "Bottom 10 ΔBLEU"))
        table = ax.table(cellText=tbl.values, colLabels=tbl.columns, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)
        savefig(fig, os.path.join(outdir, f"error_table_{i+1}.png"))
        plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats_csv", default=None, help="stats_summary CSV path")
    parser.add_argument("--bleu_json", default=None, help="paired bleu json path")
    parser.add_argument("--comp_csv", default=None, help="compliance csv path")
    parser.add_argument("--error_html", default=None, help="error board html path")
    parser.add_argument("--out", default="figs", help="output directory for PNGs")
    parser.add_argument("--nboot", type=int, default=5000, help="bootstrap iterations for BLEU")
    args = parser.parse_args()

    outdir = args.out
    ensure_out(outdir)

    if args.stats_csv and os.path.exists(args.stats_csv):
        try:
            df_stats = pd.read_csv(args.stats_csv)
            colmap = {c: c for c in df_stats.columns}
            needed = ['metric','n','mean_base','mean_instr','delta']
            if not all(any(x == c.lower() for c in map(str.lower, df_stats.columns)) for x in needed):
                print("Warning: stats CSV missing some standard columns; still attempting to plot available metrics.")
            plot_metric_bars(df_stats, outdir)
        except Exception as e:
            print("Failed plotting stats CSV:", e)
    else:
        print("No stats CSV provided or file does not exist:", args.stats_csv)

    if args.bleu_json and os.path.exists(args.bleu_json):
        try:
            plot_paired_bleu(args.bleu_json, outdir, nboot=args.nboot)
        except Exception as e:
            print("Failed plotting BLEU JSON:", e)
    else:
        print("No BLEU JSON provided or file does not exist:", args.bleu_json)

    if args.comp_csv and os.path.exists(args.comp_csv):
        try:
            plot_compliance_csv(args.comp_csv, outdir)
        except Exception as e:
            print("Failed plotting compliance CSV:", e)
    else:
        print("No compliance CSV provided or file does not exist:", args.comp_csv)

    if args.error_html and os.path.exists(args.error_html):
        try:
            render_error_html_tables(args.error_html, outdir)
        except Exception as e:
            print("Failed rendering error HTML:", e)
    else:
        print("No error HTML provided or file does not exist:", args.error_html)

if __name__ == "__main__":
    main()