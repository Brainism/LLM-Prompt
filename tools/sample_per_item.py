import argparse, pandas as pd, json
parser = argparse.ArgumentParser()
parser.add_argument("--infile", required=True)
parser.add_argument("--outfile", required=True)
parser.add_argument("--n", type=int, default=50)
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()
df = pd.read_csv(args.infile)
n = min(args.n, len(df))
sampled = df.sample(n=n, random_state=args.seed).reset_index(drop=True)
with open(args.outfile, "w", encoding="utf-8") as f:
    for _, row in sampled.iterrows():
        obj = row.dropna().to_dict()
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
print("Wrote", args.outfile, "rows:", n)