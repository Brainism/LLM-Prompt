import json, sys, os
import pandas as pd

CSV_PATH = "figs/aggregated_metrics_fixed_with_chrf_rouge.csv"
MANIFEST_PATH = "data/manifest/split_manifest_main.json"
TOP10_PATH = "figs/top10_delta_full.csv"
COMPLIANCE_PATH = "figs/compliance_by_scenario.csv"

def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()
        try:
            obj = json.loads(txt)
        except Exception:
            lines = [l for l in txt.splitlines() if l.strip()]
            obj = [json.loads(l) for l in lines]
    if isinstance(obj, dict) and "items" in obj:
        items = obj["items"]
    elif isinstance(obj, list):
        items = obj
    else:
        items = []
    ids = [it.get("id") for it in items if isinstance(it, dict) and it.get("id") is not None]
    return ids

def main():
    print("== Basic existence checks ==")
    for p in [CSV_PATH, MANIFEST_PATH, TOP10_PATH, COMPLIANCE_PATH]:
        print(p, "exists:", os.path.exists(p))
    if not os.path.exists(CSV_PATH):
        print("ERROR: aggregated CSV not found at", CSV_PATH); sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    print("\n== CSV head (first 5 rows) ==")
    print(df.head(5).to_string(index=False))

    total = len(df)
    print(f"\nTotal rows in CSV: {total}")

    cols_to_check = ["chrf","rougeL","bleu","delta","base","instr"]
    print("\n== NaN ratios and numeric stats ==")
    for c in cols_to_check:
        if c in df.columns:
            na = df[c].isna().sum()
            numeric = pd.to_numeric(df[c], errors="coerce")
            nnum = numeric.dropna().shape[0]
            mn = numeric.min(); mx = numeric.max(); mean = numeric.mean()
            print(f"{c}: NaN {na}/{total} ({na/total:.2%}), numeric_count={nnum}, min={mn}, max={mx}, mean={mean}")
            if c=="chrf" and nnum>0:
                if numeric.max()>1.5:
                    print("  -> chrf appears to be in 0-100 scale (percent).")
                else:
                    print("  -> chrf appears to be in 0-1 scale.")
        else:
            print(f"{c}: (column not found)")

    if os.path.exists(MANIFEST_PATH):
        manifest_ids = load_manifest(MANIFEST_PATH)
        print(f"\nManifest ids count: {len(manifest_ids)}")
        csv_ids = set(df['id'].dropna().astype(str))
        print("CSV ids count (unique):", len(csv_ids))
        missing = [i for i in manifest_ids if str(i) not in csv_ids]
        extra = [i for i in csv_ids if i not in set(map(str, manifest_ids))]
        print("Missing from CSV (in manifest but not in CSV):", len(missing))
        print("Extra in CSV (not in manifest):", len(extra))
        if missing:
            print("  Sample missing (up to 20):", missing[:20])
        if extra:
            print("  Sample extra (up to 20):", list(extra)[:20])
    else:
        print("\nManifest not found, cannot check id coverage.")

    if os.path.exists(TOP10_PATH):
        top = pd.read_csv(TOP10_PATH)
        print("\nTop10 file rows:", len(top))
        print(top.head(10).to_string(index=False))
    else:
        print("\nNo top10 file found.")

    if os.path.exists(COMPLIANCE_PATH):
        comp = pd.read_csv(COMPLIANCE_PATH)
        print("\nCompliance rows:", len(comp))
        print(comp.head(10).to_string(index=False))
    else:
        print("\nNo compliance CSV found.")

if __name__ == "__main__":
    main()