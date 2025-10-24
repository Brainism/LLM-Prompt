import os, json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import trim_mean

per_item_path = r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv"
subset_path = r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_subset_50.jsonl"
agg_with_scores = r"C:\Project\LLM\figs\aggregated_metrics_fixed_with_chrf_rouge.csv"
outdir = r"C:\Project\LLM\figs\generated"
os.makedirs(outdir, exist_ok=True)

df = pd.read_csv(per_item_path)
df['base'] = pd.to_numeric(df['base'], errors='coerce')
df['instr'] = pd.to_numeric(df['instr'], errors='coerce')
df = df.dropna(subset=['base','instr']).copy()
df['delta'] = df['instr'] - df['base']

n = len(df)
mean_delta = float(df['delta'].mean())
median_delta = float(df['delta'].median())
trim10 = float(trim_mean(df['delta'], 0.1))
t_res = stats.ttest_rel(df['instr'], df['base'], nan_policy='omit')
wil_res = stats.wilcoxon(df['instr'], df['base']) if n>0 else (np.nan,np.nan)

print("n", n)
print("mean delta", mean_delta)
print("median delta", median_delta)
print("trimmed mean (10%)", trim10)
print("paired t:", t_res)
print("wilcoxon:", wil_res)

rng = np.random.default_rng(12345)
nboot = 10000
boots = []
arr = df['delta'].values
for _ in range(nboot):
    samp = rng.choice(arr, size=len(arr), replace=True)
    boots.append(samp.mean())
boots = np.array(boots)
ci_low, ci_high = np.percentile(boots, [2.5,97.5])
print("bootstrap mean", boots.mean(), "95% CI =", (ci_low, ci_high))

df_sorted = df.sort_values('delta', ascending=False).reset_index(drop=True)
topk_stats = []
for k in [0,1,2,3,5,10]:
    d = df_sorted['delta'].iloc[k:]
    topk_stats.append((k, float(d.mean()), len(d)))
print("mean delta after removing top-k:", topk_stats)

out_inf = os.path.join(outdir, "influence_sorted.csv")
df_sorted.to_csv(out_inf, index=False)
print("Wrote", out_inf)

plt.rcParams.update({'figure.dpi':150, 'font.size':12})

fig, ax = plt.subplots(figsize=(6,6))
base = df['base'].values
instr = df['instr'].values
ax.boxplot([base, instr], labels=["Base","Instructed"], showmeans=True)
ax.set_ylabel("BLEU (sacre)")
ax.set_title(f"Paired BLEU (n={n}) Δ={mean_delta:.3f}")
ax.grid(axis='y', linestyle=':', alpha=0.4)
fig.savefig(os.path.join(outdir,"bleu_boxplot.png"), bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(8,5))
ax.hist(boots, bins=60)
ax.axvline(0, color='k', linestyle='--', linewidth=1)
ax.axvline(boots.mean(), color='r', linewidth=2)
ax.set_xlabel("Δ BLEU (Instructed - Base)")
ax.set_title(f"Bootstrap Δ BLEU (mean={boots.mean():.3f}, 95% CI=[{ci_low:.3f},{ci_high:.3f}])")
fig.savefig(os.path.join(outdir,"bleu_bootstrap_delta.png"), bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(10,4))
deltas = df_sorted['delta'].values
ids = df_sorted['id'].values
ax.bar(range(len(deltas)), deltas, color='tab:blue')
ax.bar(range(10), deltas[:10], color='tab:red')
ax.set_xlabel("items (sorted by Δ desc)")
ax.set_ylabel("Δ BLEU")
ax.set_title("Deltas sorted (top10 highlighted red)")
fig.savefig(os.path.join(outdir,"delta_sorted_bar.png"), bbox_inches='tight')
plt.close(fig)

def table_from_df(df_sub, fname, title=""):
    fig, ax = plt.subplots(figsize=(10,2.5))
    ax.axis('off')
    ax.set_title(title)
    tbl = ax.table(cellText=df_sub.values, colLabels=df_sub.columns, loc='center', cellLoc='center')
    tbl.scale(1,1.5)
    fig.savefig(fname, bbox_inches='tight')
    plt.close(fig)

top10 = df_sorted.head(10)[['id','base','instr','delta']]
bot10 = df_sorted.tail(10)[['id','base','instr','delta']].sort_values('delta')
table_from_df(top10, os.path.join(outdir,"top10_delta_table.png"), "Top 10 ΔBLEU")
table_from_df(bot10, os.path.join(outdir,"bot10_delta_table.png"), "Bottom 10 ΔBLEU")

print("Saved plots to", outdir)
if os.path.exists(agg_with_scores):
    try:
        agg = pd.read_csv(agg_with_scores)
        if {'bleu','chrf','mode'}.issubset(agg.columns):
            s = agg.dropna(subset=['bleu','chrf'])
            fig,ax = plt.subplots(figsize=(6,6))
            ax.scatter(s['bleu'], s['chrf'])
            ax.set_xlabel("BLEU")
            ax.set_ylabel("chrF")
            ax.set_title("Per-row BLEU vs chrF")
            fig.savefig(os.path.join(outdir,"bleu_vs_chrf_scatter.png"), bbox_inches='tight')
            plt.close(fig)
            print("Saved scatter")
    except Exception as e:
        print("Could not plot BLEU vs chrF:", e)