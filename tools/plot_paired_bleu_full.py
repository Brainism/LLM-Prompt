import os, argparse, json, numpy as np
import matplotlib.pyplot as plt
from scipy import stats

parser = argparse.ArgumentParser()
parser.add_argument("--json", default="LLM-clean/results/quantitative/bleu_sacre.json")
parser.add_argument("--out", default="figs")
parser.add_argument("--nboot", type=int, default=5000)
args = parser.parse_args()

os.makedirs(args.out, exist_ok=True)

with open(args.json, "r", encoding="utf-8") as f:
    data = json.load(f)

base = np.array([d.get("base", np.nan) for d in data], dtype=float)
instr = np.array([d.get("instr", np.nan) for d in data], dtype=float)

mask = ~np.isnan(base) & ~np.isnan(instr)
base = base[mask]; instr = instr[mask]
n = len(base)

if n == 0:
    raise SystemExit("No paired BLEU scores found in JSON.")

mean_base = np.mean(base); mean_instr = np.mean(instr)
delta = mean_instr - mean_base

plt.figure(figsize=(6,4))
plt.boxplot([base, instr], notch=False, patch_artist=True, boxprops=dict(alpha=0.6), labels=None)
plt.xticks([1,2], ["Base","Instructed"])
plt.title(f"BLEU (paired) n={n}, Δ={delta:.3f}")
plt.ylabel("BLEU")
plt.tight_layout()
plt.savefig(os.path.join(args.out, "bleu_boxplot.png"), dpi=300)
plt.close()

rng = np.random.default_rng()
diffs = []
for _ in range(args.nboot):
    idx = rng.integers(0, n, n)
    diffs.append(np.mean(instr[idx]) - np.mean(base[idx]))
diffs = np.array(diffs)
ci_low, ci_high = np.percentile(diffs, [2.5,97.5])
mean_diff = diffs.mean()

plt.figure(figsize=(6,3))
plt.hist(diffs, bins=60, edgecolor='black', linewidth=0.3)
plt.axvline(0, color='k', linestyle='--', label='0')
plt.axvline(mean_diff, color='r', linestyle='-', label=f'mean Δ={mean_diff:.3f}')
plt.xlabel("Δ BLEU (Instructed - Base)")
plt.title(f"Bootstrap Δ BLEU (n={n}) 95% CI [{ci_low:.3f}, {ci_high:.3f}]")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(args.out, "bleu_bootstrap_delta.png"), dpi=300)
plt.close()

plt.figure(figsize=(5,5))
plt.scatter(base, instr, alpha=0.7)
lims = [min(base.min(), instr.min()), max(base.max(), instr.max())]
plt.plot(lims, lims, linestyle='--', color='gray')
plt.xlabel("Base BLEU")
plt.ylabel("Instructed BLEU")
plt.title("Per-item BLEU (Base vs Instructed)")
plt.tight_layout()
plt.savefig(os.path.join(args.out, "bleu_scatter.png"), dpi=300)
plt.close()

try:
    wilcox = stats.wilcoxon(instr, base)
    w_stat, w_p = wilcox.statistic, wilcox.pvalue
except Exception:
    w_stat, w_p = None, None

diff = instr - base
cohen_d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) != 0 else np.nan

summary = {
    "n": int(n),
    "mean_base": float(mean_base),
    "mean_instr": float(mean_instr),
    "delta": float(delta),
    "bootstrap_mean_diff": float(mean_diff),
    "bootstrap_ci_low": float(ci_low),
    "bootstrap_ci_high": float(ci_high),
    "wilcoxon_stat": float(w_stat) if w_stat is not None else None,
    "wilcoxon_p": float(w_p) if w_p is not None else None,
    "cohen_d_paired": float(cohen_d)
}
with open(os.path.join(args.out, "bleu_paired_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("Saved paired BLEU plots and summary to", args.out)