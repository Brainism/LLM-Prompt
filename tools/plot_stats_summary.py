import os, argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--csv", default="LLM-clean/results/quantitative/stats_summary.v2.csv")
parser.add_argument("--out", default="figs")
args = parser.parse_args()

os.makedirs(args.out, exist_ok=True)

df = pd.read_csv(args.csv)

metrics_order = ["bleu_sacre", "rouge", "chrf"]
label_map = {"bleu_sacre":"BLEU (sacre)", "rouge":"ROUGE-L", "chrf":"chrF"}

for metric in metrics_order:
    row = df[df["metric"] == metric]
    if row.empty:
        continue
    r = row.iloc[0]
    mean_base = float(r["mean_base"])
    mean_instr = float(r["mean_instr"])
    pval = r.get("p", None)
    n = int(r["n"])

    plt.figure(figsize=(5,4))
    plt.bar([0,1], [mean_base, mean_instr], tick_label=["Base","Instructed"], alpha=0.9)
    plt.title(f"{label_map.get(metric, metric)} (n={n})")
    plt.ylabel("Score")
    for i,v in enumerate([mean_base, mean_instr]):
        plt.text(i, v + (0.01*max(mean_base, mean_instr)), f"{v:.3f}", ha='center', va='bottom', fontsize=9)
    if pval is not None:
        plt.text(0.5, 0.05, f"p = {float(pval):.3g}", transform=plt.gca().transAxes, ha='center', fontsize=9)
    plt.tight_layout()
    fname = os.path.join(args.out, f"{metric}_mean_bar.png")
    plt.savefig(fname, dpi=300)
    plt.close()

lines = []
for _,r in df.iterrows():
    metric = r["metric"]
    n = int(r["n"])
    mb = float(r["mean_base"])
    mi = float(r["mean_instr"])
    delta = float(r["delta"])
    pval = r.get("p", "")
    lines.append(f"{metric:12} | n={n:2d} | base={mb:8.3f} | instr={mi:8.3f} | Δ={delta:8.3f} | p={pval}")
txt = "\n".join(lines)

plt.figure(figsize=(8, max(2, 0.3*len(lines))))
plt.text(0.01, 0.99, txt, fontfamily="monospace", fontsize=10, va="top")
plt.axis("off")
plt.tight_layout()
plt.savefig(os.path.join(args.out, "metrics_summary_text.png"), dpi=300)
plt.close()

print("Saved summary plots to", args.out)