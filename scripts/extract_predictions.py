import csv, os, sys, pandas as pd

SRC = r"human_eval_annotation_template_filled.csv"
OUT = r"per_item_text_pairs.csv"

ref_candidates = ['reference','ref','references','target','gold','answer','label']
pred_candidates = ['prediction','pred','output','response','generated','text','system','hyp','base_output','instructed_output']

def find_column(cols, candidates):
    cols_low = [c.lower() for c in cols]
    for c in candidates:
        for i, col in enumerate(cols_low):
            if c in col:
                return cols[i]
    return None

if not os.path.exists(SRC):
    print("ERROR: source not found:", SRC)
    sys.exit(1)

for enc in ["utf-8-sig","utf-8","cp949","euc-kr","latin1"]:
    try:
        df = pd.read_csv(SRC, encoding=enc)
        print("Loaded", SRC, "with encoding", enc)
        break
    except Exception as e:
        # try next
        last_e = e
else:
    print("Failed to read", SRC, ":", last_e)
    sys.exit(2)

cols = df.columns.tolist()
ref_col = find_column(cols, ref_candidates)
pred_col = find_column(cols, pred_candidates)
id_col = None
for c in ['id','ID','example_id','example','idx','index']:
    if c in cols:
        id_col = c; break

if ref_col is None:
    print("Could not find reference column. Available columns:", cols)
    sys.exit(1)

if pred_col is None:
    print("Could not find prediction column automatically. Available columns:", cols)
    print("If predictions are stored under a different name, edit pred_candidates in the script.")
    sys.exit(1)

print("Mapping: id->", id_col, ", ref->", ref_col, ", pred->", pred_col)

out_rows = []
for i,row in df.iterrows():
    key = row[id_col] if id_col else f"row-{i}"
    ref = row.get(ref_col, "")
    pred = row.get(pred_col, "")
    if pd.isna(ref): ref = ""
    if pd.isna(pred): pred = ""
    out_rows.append({"id": key, "reference": ref, "prediction": pred})

out_df = pd.DataFrame(out_rows)
out_df.to_csv(OUT, index=False, encoding="utf-8-sig")
print("Wrote", OUT, "rows=", len(out_df))