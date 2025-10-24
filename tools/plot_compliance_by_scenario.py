import os, argparse, json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--json", default="LLM-clean/results/quantitative/compliance_summary.json")
parser.add_argument("--out", default="figs")
args = parser.parse_args()

os.makedirs(args.out, exist_ok=True)

with open(args.json, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data.get("summary", None)
if summary is None:
    raise SystemExit("No 'summary' key found in compliance summary JSON.")

df = pd.DataFrame(summary)
pivot = df.pivot_table(index="scenario", columns="mode", values="acc")
pivot = pivot.fillna(0)

pivot["avg"] = pivot.mean(axis=1)
pivot = pivot.sort_values("avg", ascending=False)
pivot = pivot.drop(columns=["avg"])

scenarios = pivot.index.tolist()
modes = pivot.columns.tolist()
x = np.arange(len(scenarios))
width = 0.35 if len(modes)==2 else 0.8/len(modes)

plt.figure(figsize=(max(6, 0.5*len(scenarios)), 4))
for i,mode in enumerate(modes):
    vals = pivot[mode].values
    plt.bar(x + (i - (len(modes)-1)/2)*width, vals, width=width, label=mode)
plt.xticks(x, scenarios, rotation=45, ha="right")
plt.ylabel("Compliance (pass rate)")
plt.title("Compliance pass rate by scenario and mode")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(args.out, "compliance_by_scenario.png"), dpi=300)
plt.close()

pivot.to_csv(os.path.join(args.out, "compliance_by_scenario.csv"))

print("Saved compliance plot and CSV to", args.out)