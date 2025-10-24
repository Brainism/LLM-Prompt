import argparse, json, os
import numpy as np, pandas as pd
from scipy import stats
from pathlib import Path

def bootstrap_ci(data, nboot=5000, alpha=0.05):
    boots = []
    n = len(data)
    for i in range(nboot):
        sample = np.random.choice(data, size=n, replace=True)
        boots.append(np.mean(sample))
    lo = np.percentile(boots, 100*alpha/2)
    hi = np.percentile(boots, 100*(1-alpha/2))
    return float(lo), float(hi), float(np.mean(boots))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--per_item", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv")
    p.add_argument("--out", default=r"C:\Project\LLM\analysis_outputs\recomputed_stats.json")
    p.add_argument("--nboot", type=int, default=5000)
    args = p.parse_args()
    df = pd.read_csv(args.per_item, dtype={"id":str})
    df["base"] = pd.to_numeric(df["base"], errors="coerce")
    df["instr"] = pd.to_numeric(df["instr"], errors="coerce")
    df_clean = df.dropna(subset=["base","instr"]).copy()
    n = len(df_clean)
    mean_base = float(df_clean["base"].mean())
    mean_instr = float(df_clean["instr"].mean())
    deltas = (df_clean["instr"] - df_clean["base"]).values
    mean_delta = float(np.mean(deltas))
    tstat, pval = stats.ttest_rel(df_clean["instr"], df_clean["base"], nan_policy='omit')
    lo, hi, boot_mean = bootstrap_ci(deltas, nboot=args.nboot)
    out = {
        "n": n,
        "mean_base": mean_base,
        "mean_instr": mean_instr,
        "mean_delta": mean_delta,
        "paired_t": {"tstat": float(tstat), "p": float(pval)},
        "bootstrap": {"nboot": args.nboot, "mean_boot": boot_mean, "ci95": [lo,hi]}
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("Wrote recomputed stats to", args.out)
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()