import os, sys
import pandas as pd
ROOT = r"C:\Project\LLM"
SRC = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
if not os.path.exists(SRC):
    print("ERROR: missing", SRC); sys.exit(1)
df = pd.read_csv(SRC, encoding="utf-8-sig")
print("ROWS:", len(df))
print("COLUMNS:", df.columns.tolist())
print("\n-- dtypes and null counts --")
print(df.dtypes)
print(df.isna().sum())
print("\n-- unique modes and counts --")
if "mode" in df.columns:
    print(df["mode"].value_counts().to_string())
else:
    print("no 'mode' column")
print("\n-- sample rows (first 10) --")
print(df.head(10).to_string(index=False))
for col in ["chrf","rouge_l","rougeL","chrf_base","chrf_instr"]:
    if col in df.columns:
        s = pd.to_numeric(df[col], errors='coerce')
        print(f"\n{col}: mean={s.mean()}, non-null={s.count()}, nulls={s.isna().sum()}")