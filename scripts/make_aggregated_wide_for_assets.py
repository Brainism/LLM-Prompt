import pandas as pd, os, sys, csv

SRC = "aggregated_metrics_by_mode.csv"
OUT = "aggregated_metrics_fixed_with_chrf_rouge.csv"
BACKUP = OUT + ".auto.bak"

if not os.path.exists(SRC):
    print("Missing", SRC); sys.exit(1)

df = pd.read_csv(SRC, encoding="utf-8-sig")
modes = df['mode'].tolist()
if not set(['base','instr']).intersection(set(modes)):
    pass

metrics = {}
for _, r in df.iterrows():
    mode = str(r['mode'])
    for col in df.columns:
        if col == 'mode': continue
        metric = col
        val = r[col]
        metrics.setdefault(metric, {})[mode] = val

rows = []
modes_all = sorted(list(set(df['mode'])))
for metric, d in metrics.items():
    row = {'metric': metric}
    for m in modes_all:
        row[m] = d.get(m, "NA")
    rows.append(row)

out_df = pd.DataFrame(rows)
if os.path.exists(OUT):
    try:
        os.replace(OUT, BACKUP)
        print("Backed up existing", OUT, "->", BACKUP)
    except Exception as e:
        print("Backup failed:", e)
out_df.to_csv(OUT, index=False, encoding="utf-8-sig")
print("Wrote", OUT, "with columns:", out_df.columns.tolist())
print(out_df.to_string(index=False))