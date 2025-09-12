import argparse, pandas as pd
parser = argparse.ArgumentParser()
parser.add_argument("--csv", default="LLM-clean/results/quantitative/stats_summary.v2.csv")
parser.add_argument("--out", default="figs/table_metrics.tex")
args = parser.parse_args()

df = pd.read_csv(args.csv)
rows = []
for _,r in df.iterrows():
    metric = r["metric"]
    rows.append({
        "metric": metric,
        "n": int(r["n"]),
        "base": float(r["mean_base"]),
        "instr": float(r["mean_instr"]),
        "delta": float(r["delta"]),
        "p": r.get("p", "")
    })

with open(args.out, "w", encoding="utf-8") as f:
    f.write("\\begin{table}[t]\n\\centering\n\\caption{Summary statistics by metric (Base vs Instructed).}\n")
    f.write("\\begin{tabular}{lrrrrr}\n\\toprule\nMetric & n & Base mean & Instructed mean & $\\Delta$ & p-value \\\\\n\\midrule\n")
    for r in rows:
        f.write(f"{r['metric']} & {r['n']} & {r['base']:.4f} & {r['instr']:.4f} & {r['delta']:.4f} & {r['p']} \\\\\n")
    f.write("\\bottomrule\n\\end{tabular}\n\\label{tab:metrics_summary}\n\\end{table}\n")
print("Saved LaTeX table to", args.out)