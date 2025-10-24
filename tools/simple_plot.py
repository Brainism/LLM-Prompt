import os, argparse, json
import pandas as pd
import matplotlib.pyplot as plt
from glob import glob

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="results/raw/fake_outputs.jsonl")
parser.add_argument("--out", default="figs")
args = parser.parse_args()
os.makedirs(args.out, exist_ok=True)

rows = []
if args.input.endswith(".jsonl"):
    with open(args.input, "r", encoding="utf-8") as f:
        for l in f:
            rows.append(json.loads(l))
elif args.input.endswith(".json"):
    rows = json.load(open(args.input, "r", encoding="utf-8"))

df = pd.DataFrame(rows)
if df.empty:
    print("No rows to plot")
    raise SystemExit(1)

metrics = ["bleu","rouge_l","chrf","compliance"]
for m in metrics:
    if m in df.columns:
        grp = df.groupby("model")[m].agg(["mean","std","count"]).dropna()
        if grp.empty: continue
        plt.figure(figsize=(8,4))
        plt.errorbar(grp.index, grp["mean"], yerr=grp["std"], fmt='o', capsize=5)
        plt.title(f"{m} (mean ± std) by model")
        plt.ylabel(m)
        plt.tight_layout()
        plt.savefig(os.path.join(args.out, f"{m}_by_model.png"))
        plt.close()

print("Saved plots to", args.out)