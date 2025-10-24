import sys
import pandas as pd
from pathlib import Path

def read_csv_robust(path):
    encs = ['utf-8', 'utf-8-sig', 'cp949', 'latin1']
    for e in encs:
        try:
            return pd.read_csv(path, encoding=e)
        except Exception:
            continue
    return pd.read_csv(path, engine='python', encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts\\create_prompt_subset_cmd.py <input_csv> <output_csv> <ID1> [ID2 ...]")
        sys.exit(1)
    in_csv = Path(sys.argv[1])
    out_csv = Path(sys.argv[2])
    ids = sys.argv[3:]

    if not in_csv.exists():
        print(f"Input file not found: {in_csv}")
        sys.exit(2)

    df = read_csv_robust(in_csv)
    id_col = None
    for c in ['id','ID','Id']:
        if c in df.columns:
            id_col = c
            break
    if id_col is None:
        id_col = df.columns[0]
        print(f"No explicit 'id' column found; using first column '{id_col}' as id.")

    # 필터
    subset = df[df[id_col].astype(str).isin(ids)]
    if subset.empty:
        print("No matching IDs found in input CSV. IDs provided:", ids)
    else:
        subset.to_csv(out_csv, index=False, encoding='utf-8-sig')
        print(f"Wrote {len(subset)} rows to {out_csv}")

if __name__ == '__main__':
    main()