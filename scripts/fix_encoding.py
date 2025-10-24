import sys
import io
import os
import pandas as pd

SRC = r"per_item_full_50.csv"
OUT = r"per_item_full_50_utf8.csv"
encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr", "latin1", "iso-8859-1"]

def try_load(enc):
    try:
        df = pd.read_csv(SRC, encoding=enc)
        return df, enc
    except Exception as e:
        return None, e

if not os.path.exists(SRC):
    print("ERROR: source not found:", SRC)
    sys.exit(1)

for enc in encodings:
    print("Trying encoding:", enc)
    df, info = try_load(enc)
    if df is not None:
        print("Success with encoding:", enc, "rows=", len(df))
        df.to_csv(OUT, index=False, encoding="utf-8-sig")
        print("Saved UTF-8 file:", OUT)
        sys.exit(0)
    else:
        print("Failed:", info)

print("All encodings failed. Please open the file and inspect encoding manually.")
sys.exit(2)