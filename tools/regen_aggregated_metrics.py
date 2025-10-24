import os, argparse, json
import pandas as pd
import numpy as np
from pathlib import Path

def read_maybe_json(json_path):
    with open(json_path, "r", encoding="utf-8") as fh:
        j = json.load(fh)
    if isinstance(j, list):
        return pd.DataFrame(j)
    try:
        recs = []
        for k,v in j.items():
            if isinstance(v, dict):
                v2 = v.copy(); v2.setdefault("id", k); recs.append(v2)
        return pd.DataFrame(recs)
    except Exception:
        return pd.DataFrame()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bleu_json", default=r"C:\Project\LLM\LLM-clean\results\quantitative\bleu_sacre.json")
    p.add_argument("--per_item_csv", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv")
    p.add_argument("--out", default=r"C:\Project\LLM\figs\aggregated_metrics_fixed.csv")
    args = p.parse_args()

    if os.path.exists(args.per_item_csv):
        df = pd.read_csv(args.per_item_csv, dtype={"id":str})
    else:
        if os.path.exists(args.bleu_json):
            df = read_maybe_json(args.bleu_json)
        else:
            raise SystemExit("No per-item CSV or bleu JSON found.")

    for col in ["id","base","instr","bleu","bleu_sacre","chrf","rouge","rouge_l"]:
        if col in df.columns:
            pass
    if "base" in df.columns and "instr" in df.columns:
        rows = []
        for _,r in df.iterrows():
            item_id = str(r["id"])
            rows.append({"id":item_id,"model":"your_model","mode":"base","bleu":r.get("base", np.nan),"chrf":r.get("chrf", np.nan),"rouge_l":r.get("rouge", np.nan)})
            rows.append({"id":item_id,"model":"your_model","mode":"instr","bleu":r.get("instr", np.nan),"chrf":r.get("chrf", np.nan),"rouge_l":r.get("rouge", np.nan)})
        outdf = pd.DataFrame(rows)
    else:
        outdf = df.copy()
        if "mode" not in outdf.columns:
            outdf["mode"] = outdf.get("mode", "unknown")

    outdf.to_csv(args.out, index=False, encoding="utf-8")
    print("Wrote aggregated metrics with rows:", len(outdf), "to", args.out)
    print("Unique ids:", outdf["id"].nunique())
    print("Rows per mode:\n", outdf.groupby("mode").size())
    print("NaN counts:\n", outdf.isna().sum())

if __name__ == "__main__":
    main()