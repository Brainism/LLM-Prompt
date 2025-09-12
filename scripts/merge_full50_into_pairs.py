import pandas as pd, os, sys

pairs_file = "per_item_text_pairs.csv"
full50 = "per_item_full_50_utf8.csv"
out = "per_item_text_pairs_merged.csv"

if not os.path.exists(pairs_file):
    print("Missing", pairs_file); sys.exit(1)

pairs = pd.read_csv(pairs_file, encoding="utf-8-sig")
if os.path.exists(full50):
    try:
        full = pd.read_csv(full50, encoding="utf-8-sig")
    except Exception as e:
        print("Failed to read", full50, e); sys.exit(1)
else:
    print(full50, "not found; abort")
    sys.exit(1)

cols = list(full.columns)
id_col = None
ref_col = None
for c in cols:
    if c.lower() in ('id','example_id','example','idx','index'):
        id_col = c; break
for c in cols:
    if c.lower() in ('reference','ref','references','target','gold'):
        ref_col = c; break

if id_col is None:
    print("No id-like column in", full50, "columns:", cols)
else:
    print("Found id column:", id_col)
if ref_col is None:
    print("No ref-like column in", full50, "columns:", cols)
else:
    print("Found ref column:", ref_col)

full_map = {}
if id_col and ref_col:
    for _, r in full.iterrows():
        k = r[id_col]
        v = r[ref_col]
        full_map[str(k)] = v

if 'id' not in pairs.columns:
    pairs.insert(0,'id', [f"row-{i}" for i in range(len(pairs))])

if 'reference' not in pairs.columns:
    pairs['reference'] = ''
if 'prediction' not in pairs.columns:
    pairs['prediction'] = ''

for i,row in pairs.iterrows():
    key = str(row['id'])
    if (not str(row['reference']).strip()) and key in full_map:
        pairs.at[i,'reference'] = full_map[key]

pairs.to_csv(out, index=False, encoding="utf-8-sig")
print("Wrote", out, "rows=", len(pairs))