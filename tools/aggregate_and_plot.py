import os, json, argparse, math
import pandas as pd
import matplotlib.pyplot as plt
from glob import glob
from collections import defaultdict
import random
parser = argparse.ArgumentParser()
parser.add_argument("--results", default="results")
parser.add_argument("--out", default="figs")
args = parser.parse_args()
os.makedirs(args.out, exist_ok=True)

KEY_MAP = {
    "bleu": ["bleu", "BLEU", "sacre_bleu"],
    "rouge_l": ["rouge_l", "ROUGE_L", "rouge-l"],
    "chrf": ["chrf", "chrF"],
    "compliance": ["compliance", "compliance_rate", "compliant_ratio"]
}

def find_key(d, candidates):
    for k in candidates:
        if k in d: return k
    for k in d.keys():
        if k.lower() in [c.lower() for c in candidates]:
            return k
    return None

rows = []
for path in glob(os.path.join(args.results, "**/*.*"), recursive=True):
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    rows.append(obj)
                except:
                    pass
    elif path.endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, list):
                    rows.extend(obj)
                elif isinstance(obj, dict):
                    if "items" in obj and isinstance(obj["items"], list):
                        rows.extend(obj["items"])
                    else:
                        rows.append(obj)
        except:
            pass
    elif path.endswith(".csv"):
        try:
            df = pd.read_csv(path)
            rows.extend(df.to_dict(orient="records"))
        except:
            pass

if len(rows)==0:
    print("No parsable result rows found under", args.results)
    raise SystemExit(1)

normed = []
for r in rows:
    rec = {}
    rec["model"] = r.get("model") or r.get("Model") or r.get("model_name") or r.get("modelId") or r.get("engine")
    rec["mode"] = r.get("mode") or r.get("Mode") or r.get("run_mode")
    for metric, candidates in KEY_MAP.items():
        k = find_key(r, candidates)
        rec[metric] = float(r[k]) if (k and r[k] not in [None, "NA", "nan"]) else None
    normed.append(rec)

df = pd.DataFrame(normed)
print("Loaded rows:", len(df))
df = df.dropna(subset=["bleu","rouge_l","chrf","compliance"], how="all")
df.to_csv(os.path.join(args.out,"aggregated_metrics.csv"), index=False)

metrics = ["bleu","rouge_l","chrf","compliance"]
for m in metrics:
    g = df.groupby("model")[m].agg(["mean","count","std"]).reset_index().dropna()
    if g.shape[0]==0: continue
    plt.figure(figsize=(8,4))
    plt.errorbar(g["model"], g["mean"], yerr=g["std"], fmt='o', capsize=5)
    plt.title(f"{m} by model (mean ± std)")
    plt.ylabel(m)
    plt.xlabel("model")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(args.out, f"{m}_by_model.png"))
    plt.close()

models = df["model"].dropna().unique().tolist()
if len(models)>=2:
    a = df[df["model"]==models[0]]["bleu"].dropna().values
    b = df[df["model"]==models[1]]["bleu"].dropna().values
    if len(a)>0 and len(b)>0:
        niter=2000
        diffs=[]
        for _ in range(niter):
            sa = [random.choice(a) for _ in range(len(a))]
            sb = [random.choice(b) for _ in range(len(b))]
            diffs.append(sum(sa)/len(sa) - sum(sb)/len(sb))
        plt.figure(figsize=(6,3))
        plt.hist(diffs, bins=50)
        plt.title(f"Bootstrap Δ BLEU: {models[0]} - {models[1]}")
        plt.axvline(0, color='k', linestyle='--')
        plt.tight_layout()
        plt.savefig(os.path.join(args.out,"bootstrap_delta_bleu.png"))
        plt.close()

print("Saved aggregated CSV and plots into", args.out)