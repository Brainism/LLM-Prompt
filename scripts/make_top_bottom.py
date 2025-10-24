import argparse
import os
import pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--aggregated", required=True, help="Path to aggregated_metrics_fixed_with_chrf_rouge.csv")
    p.add_argument("--out_dir", required=True, help="Output dir for top/bottom CSVs")
    args = p.parse_args()

    agg_path = args.aggregated
    out_dir = args.out_dir

    if not os.path.exists(agg_path):
        raise SystemExit(f"ERROR: aggregated file not found: {agg_path}")

    df = pd.read_csv(agg_path)
    possible_base = [c for c in df.columns if c.lower().strip() in ("base","base_score","baseline")]
    possible_instr = [c for c in df.columns if c.lower().strip() in ("instr","instruct","instructed","instruction","model_instr")]
    if not possible_base or not possible_instr:
        for c in df.columns:
            if "base" in c.lower() and "mean" in c.lower(): possible_base.append(c)
            if "instr" in c.lower() and "mean" in c.lower(): possible_instr.append(c)

    if not possible_base or not possible_instr:
        raise SystemExit("ERROR: Could not auto-detect base/instr columns in aggregated CSV. Columns: " + ",".join(df.columns))

    base_col = possible_base[0]
    instr_col = possible_instr[0]

    df["delta"] = df[instr_col] - df[base_col]
    top10 = df.nlargest(10, "delta")
    bottom10 = df.nsmallest(10, "delta")

    os.makedirs(out_dir, exist_ok=True)
    top_path = os.path.join(out_dir, "top10_delta.csv")
    bot_path = os.path.join(out_dir, "bottom10_delta.csv")
    top10.to_csv(top_path, index=False)
    bottom10.to_csv(bot_path, index=False)
    print("Wrote:", top_path, bot_path)

if __name__ == "__main__":
    main()