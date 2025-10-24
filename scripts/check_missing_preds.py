import pandas as pd, os, sys

SRC = "per_item_text_pairs.csv"
if not os.path.exists(SRC):
    print("Missing", SRC); sys.exit(1)

df = pd.read_csv(SRC, encoding="utf-8-sig")
total = len(df)
nonempty_pred = df['prediction'].astype(str).apply(lambda x: x.strip()!='').sum() if 'prediction' in df.columns else 0
print("rows=", total, "nonempty_pred=", nonempty_pred)
if 'id' not in df.columns:
    print("No id column found; first 5 rows:")
    print(df.head(5).to_string())
    sys.exit(0)

missing = df[df['prediction'].astype(str).apply(lambda x: x.strip()=='')]['id'].tolist()
print("missing count:", len(missing))
if len(missing) <= 50:
    for i in missing:
        print(i)
else:
    print("(too many to list; first 50)")
    for i in missing[:50]:
        print(i)