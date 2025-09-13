import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def try_numeric(s):
    try:
        return pd.to_numeric(s, errors='coerce')
    except:
        return s

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--comp_csv", required=True, help="Path to compliance CSV")
    p.add_argument("--out_png", default="figs/compliance_by_scenario.png", help="Output PNG path")
    p.add_argument("--dpi", type=int, default=150, help="DPI for saved figure")
    args = p.parse_args()

    df = pd.read_csv(args.comp_csv)
    if df.shape[1] < 2:
        raise SystemExit("ERROR: compliance CSV must have >=2 columns (category, value). Got columns: " + ",".join(df.columns))

    xcol = None
    for c in df.columns:
        if c.lower() in ("scenario","name","id","category","label"):
            xcol = c
            break
    if xcol is None:
        xcol = df.columns[0]

    ycol = None
    for c in df.columns:
        if c.lower() in ("compliance","rate","value","score","percent"):
            ycol = c
            break
    if ycol is None:
        ycol = df.columns[1]

    x = df[xcol].astype(str).fillna("")
    y = pd.to_numeric(df[ycol], errors='coerce')

    if y.isna().sum() > (0.5 * len(y)):
        def parse_percent(v):
            try:
                if isinstance(v, str) and '%' in v:
                    return float(v.replace('%',''))/100.0
                return float(v)
            except:
                return np.nan
        y = df[ycol].apply(parse_percent)

    if y.isna().sum() > (0.5 * len(y)):
        numeric_cols = []
        for c in df.columns:
            tmp = pd.to_numeric(df[c], errors='coerce')
            if tmp.notna().sum() > 0:
                numeric_cols.append((c, tmp.notna().sum()))
        if numeric_cols:
            numeric_cols.sort(key=lambda t: -t[1])
            ycol = numeric_cols[0][0]
            y = pd.to_numeric(df[ycol], errors='coerce')
            print("INFO: selected numeric column:", ycol)

    if y.isna().all():
        raise SystemExit("ERROR: Could not find numeric column in compliance CSV. Columns: " + ",".join(df.columns))
    plt.figure(figsize=(8, max(4, 0.4*len(x))))
    try:
        vals = y.fillna(0.0)
        if vals.max() <= 1.01:
            display_vals = vals * 100.0
            ylabel = "Compliance (%)"
        else:
            display_vals = vals
            ylabel = "Compliance (raw)"
        bars = plt.barh(range(len(x)), display_vals, align='center')
        plt.yticks(range(len(x)), x)
        plt.xlabel(ylabel)
        plt.title("Compliance by scenario")
        for i, b in enumerate(bars):
            v = display_vals.iloc[i]
            plt.text(b.get_width() + (0.01*display_vals.max() if display_vals.max()!=0 else 0.1),
                     b.get_y() + b.get_height()/2,
                     f"{v:.2f}", va="center", fontsize=9)
        plt.tight_layout()
        outdir = os.path.dirname(args.out_png)
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        plt.savefig(args.out_png, dpi=args.dpi)
        print("Saved compliance plot to", args.out_png)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise SystemExit("Failed to plot compliance CSV: " + str(e))

if __name__ == "__main__":
    main()