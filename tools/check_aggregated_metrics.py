import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

def try_read_csv(path):
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        raise RuntimeError(f"Could not read CSV {path}: {e}")

def try_read_jsonl(path):
    try:
        df = pd.read_json(path, lines=True)
        return df
    except Exception as e:
        raise RuntimeError(f"Could not read JSONL {path}: {e}")

def to_numeric_safe(s):
    return pd.to_numeric(s, errors='coerce')

def ensure_outdir(p):
    os.makedirs(p, exist_ok=True)
    return p

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agg", default=r"C:\Project\LLM\figs\aggregated_metrics.csv", help="aggregated metrics csv")
    p.add_argument("--full", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv", help="per-item full csv")
    p.add_argument("--sub", default=r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_subset_50.jsonl", help="per-item subset jsonl")
    p.add_argument("--stats", default=r"C:\Project\LLM\LLM-clean\results\quantitative\stats_summary.v2.csv", help="stats summary csv")
    p.add_argument("--out", default=r"C:\Project\LLM\figs\generated", help="output directory for debug artifacts")
    args = p.parse_args()

    outdir = ensure_outdir(args.out)
    report = {"files": {}}

    print("\n=== Checking aggregated metrics ===")
    if os.path.exists(args.agg):
        try:
            df_agg = try_read_csv(args.agg)
            print("Loaded:", args.agg)
            print("Columns:", df_agg.columns.tolist())
            print("Shape:", df_agg.shape)
            print("NaN counts:\n", df_agg.isna().sum())
            for col in ["bleu","rouge_l","chrf","compliance"]:
                if col in df_agg.columns:
                    df_agg[col] = to_numeric_safe(df_agg[col])
            preview_csv = os.path.join(outdir, "aggregated_metrics_preview.csv")
            df_agg.head(200).to_csv(preview_csv, index=False, encoding="utf-8")
            print("Wrote preview to:", preview_csv)
            report["files"]["aggregated_metrics"] = {"path": args.agg, "shape": df_agg.shape, "nan_counts": df_agg.isna().sum().to_dict()}
        except Exception as e:
            print("ERROR reading aggregated metrics:", e)
    else:
        print("Missing aggregated metrics file:", args.agg)

    df_full = None
    df_sub = None
    print("\n=== Checking per-item files ===")
    if os.path.exists(args.full):
        try:
            df_full = try_read_csv(args.full)
            print("Loaded full:", args.full, "shape=", df_full.shape)
            print("Columns:", df_full.columns.tolist())
            for c in ["base","instr","bleu","bleu_sacre","chrf","rouge"]:
                if c in df_full.columns:
                    df_full[c] = to_numeric_safe(df_full[c])
            report["files"]["full"] = {"path": args.full, "shape": df_full.shape, "cols": df_full.columns.tolist()}
        except Exception as e:
            print("ERROR reading full file:", e)
    else:
        print("Full file missing:", args.full)

    if os.path.exists(args.sub):
        try:
            df_sub = try_read_jsonl(args.sub)
            print("Loaded subset:", args.sub, "shape=", df_sub.shape)
            print("Columns:", df_sub.columns.tolist())
            for c in ["base","instr","bleu","bleu_sacre","chrf","rouge"]:
                if c in df_sub.columns:
                    df_sub[c] = to_numeric_safe(df_sub[c])
            report["files"]["subset"] = {"path": args.sub, "shape": df_sub.shape, "cols": df_sub.columns.tolist()}
        except Exception as e:
            print("ERROR reading subset file:", e)
    else:
        print("Subset file missing:", args.sub)

    def get_ids(df):
        for possible in ("id","item_id","example_id"):
            if df is not None and possible in df.columns:
                return df[possible].astype(str).tolist()
        return None

    ids_full = get_ids(df_full)
    ids_sub = get_ids(df_sub)
    if ids_full is not None and ids_sub is not None:
        set_full = set(ids_full)
        set_sub = set(ids_sub)
        inter = sorted(list(set_full & set_sub))
        onlyA = sorted(list(set_full - set_sub))
        onlyB = sorted(list(set_sub - set_full))
        print(f"full ids: {len(set_full)}, sub ids: {len(set_sub)}, intersection: {len(inter)}")
        print("only in full (count):", len(onlyA), "sample:", onlyA[:10])
        print("only in sub (count):", len(onlyB), "sample:", onlyB[:10])
        pd.DataFrame({"id": inter}).to_csv(os.path.join(outdir, "in_both.csv"), index=False)
        pd.DataFrame({"id": onlyA}).to_csv(os.path.join(outdir, "only_in_full.csv"), index=False)
        pd.DataFrame({"id": onlyB}).to_csv(os.path.join(outdir, "only_in_sub.csv"), index=False)
    else:
        print("Could not compute intersection: missing id column in one or both per-item files.")

    if df_full is not None and all(c in df_full.columns for c in ("base","instr")):
        d = df_full.copy()
        d["delta_full"] = to_numeric_safe(d["instr"]) - to_numeric_safe(d["base"])
        d_valid = d.dropna(subset=["delta_full"])
        d_valid_sorted = d_valid.sort_values("delta_full", ascending=False)
        top10 = d_valid_sorted.head(10)
        bot10 = d_valid_sorted.tail(10)
        top10_csv = os.path.join(outdir, "top10_delta_full.csv")
        bot10_csv = os.path.join(outdir, "bottom10_delta_full.csv")
        top10.to_csv(top10_csv, index=False)
        bot10.to_csv(bot10_csv, index=False)
        print("Wrote top/bottom 10 deltas to:", top10_csv, bot10_csv)
        try:
            plt.figure(figsize=(8,4))
            plt.hist(d_valid["delta_full"].values, bins=60)
            plt.title("Distribution of delta (instr - base) [full]")
            plt.xlabel("delta")
            plt.ylabel("count")
            fn = os.path.join(outdir, "delta_full_hist.png")
            plt.savefig(fn, dpi=300, bbox_inches="tight")
            plt.close()
            print("Saved histogram:", fn)

            def save_table_image(df_table, outpath, title=""):
                fig, ax = plt.subplots(figsize=(12, max(1, 0.35*len(df_table))))
                ax.axis('off')
                table = ax.table(cellText=df_table.round(3).values,
                                 colLabels=df_table.columns,
                                 loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1,1.2)
                if title:
                    plt.suptitle(title)
                fig.savefig(outpath, dpi=200, bbox_inches="tight")
                plt.close(fig)

            cols_for_table = [c for c in ["id","base","instr","delta_full","chrf","rouge"] if c in d_valid.columns]
            save_table_image(top10[cols_for_table], os.path.join(outdir, "top10_table.png"), title="Top 10 ΔBLEU (instr - base)")
            save_table_image(bot10[cols_for_table], os.path.join(outdir, "bot10_table.png"), title="Bottom 10 ΔBLEU (instr - base)")
            print("Saved top/bottom table images.")
        except Exception as e:
            print("Plotting error (delta):", e)
    else:
        print("Cannot compute delta: 'base' and 'instr' columns not both present in full per-item file.")

    if 'bleu' in locals().get('df_agg', pd.DataFrame()).columns and 'chrf' in df_agg.columns:
        try:
            d = df_agg.dropna(subset=['bleu','chrf'])
            if len(d) > 0:
                plt.figure(figsize=(6,6))
                plt.scatter(d['bleu'], d['chrf'], alpha=0.7)
                if len(d) > 1:
                    m,b = np.polyfit(d['bleu'], d['chrf'], 1)
                    xs = np.linspace(d['bleu'].min(), d['bleu'].max(), 100)
                    plt.plot(xs, m*xs+b, linestyle='--')
                plt.xlabel("BLEU (sacre)")
                plt.ylabel("chrF")
                plt.title("Per-row BLEU vs chrF")
                fn = os.path.join(outdir, "bleu_vs_chrf_scatter.png")
                plt.savefig(fn, dpi=300, bbox_inches="tight")
                plt.close()
                print("Saved scatter:", fn)
            else:
                print("No non-NaN rows for BLEU/chrF scatter.")
        except Exception as e:
            print("Plotting error (bleu vs chrf):", e)
    else:
        print("Cannot make BLEU vs chrF scatter: missing columns in aggregated metrics.")

    print("\n=== Checking stats_summary ===")
    if os.path.exists(args.stats):
        try:
            df_stats = try_read_csv(args.stats)
            print("Loaded stats summary:", args.stats)
            print(df_stats.head(50).to_string(index=False))
            df_stats.to_csv(os.path.join(outdir, "stats_summary_copy.csv"), index=False)
            print("Saved a copy to outdir.")
        except Exception as e:
            print("ERROR reading stats summary:", e)
    else:
        print("stats_summary file not found:", args.stats)

    rpt_path = os.path.join(outdir, "check_report.json")
    try:
        with open(rpt_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print("\nWrote check report JSON to:", rpt_path)
    except Exception as e:
        print("Could not write report JSON:", e)

    print("\n=== DONE ===\nPlease inspect the saved files in:", outdir)
    return 0

if __name__ == "__main__":
    exit(main())