from __future__ import annotations
import argparse, json, math, csv
from statistics import mean, pstdev
from scipy import stats

def load_metric(path: str, key: str) -> dict[str, float]:
    data = json.loads(open(path, "r", encoding="utf-8").read())
    per = data.get("per_item", [])
    out = {}
    for x in per:
        id_ = str(x["id"])
        out[id_] = float(x[key])
    return out

def pair_vectors(general: dict[str,float], instructed: dict[str,float]):
    ids = sorted(set(general.keys()) & set(instructed.keys()))
    g = [general[i] for i in ids]
    ins = [instructed[i] for i in ids]
    return ids, g, ins

def cohen_d_paired(g, i):
    import numpy as np
    diff = np.array(g) - np.array(i)
    sd = diff.std(ddof=1) if len(diff) > 1 else 0.0
    md = diff.mean() if len(diff) > 0 else 0.0
    return 0.0 if sd == 0 else md / sd

def run(rouge_path: str, codebleu_path: str, out_csv: str):
    rouge = json.loads(open(rouge_path, "r", encoding="utf-8").read())["per_item"]
    codeb = json.loads(open(codebleu_path, "r", encoding="utf-8").read())["per_item"]

    def split(per, key):
        g = {x["id"]: float(x[key]) for x in per if x["prompt_type"] == "general"}
        i = {x["id"]: float(x[key]) for x in per if x["prompt_type"] == "instructed"}
        return g, i

    r_g, r_i = split(rouge, "rougeL_f")
    b_g, b_i = split(codeb, "bleu4")

    import numpy as np
    rows = []

    for name, (g, i) in {
        "rougeL_f": (r_g, r_i),
        "bleu4": (b_g, b_i)
    }.items():
        ids, gv, iv = pair_vectors(g, i)
        if len(gv) == 0:
            continue
        t = stats.ttest_rel(gv, iv, nan_policy="omit")
        try:
            w = stats.wilcoxon(gv, iv, zero_method="wilcox", correction=False, alternative="two-sided")
        except Exception:
            w = type("obj",(object,),{"statistic": float("nan"), "pvalue": float("nan")})()
        d = cohen_d_paired(gv, iv)
        rows.append([name, "paired_t", t.statistic, t.pvalue, mean(gv), mean(iv), d, len(gv)])
        rows.append([name, "wilcoxon", w.statistic, w.pvalue, mean(gv), mean(iv), d, len(gv)])

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric","test","statistic","p_value","mean_general","mean_instructed","cohens_d","n"])
        w.writerows(rows)

    print(f"[OK] stats -> {out_csv}")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--rouge", required=True)
    p.add_argument("--codebleu", required=True)
    p.add_argument("--output", default="results/stats_summary.csv")
    return p.parse_args()

if __name__=="__main__":
    a = parse_args()
    run(a.rouge, a.codebleu, a.output)