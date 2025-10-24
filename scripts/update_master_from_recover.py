import sys
import pandas as pd
from pathlib import Path

def read_robust(p):
    encs = ['utf-8-sig','utf-8','cp949','latin1']
    for e in encs:
        try:
            return pd.read_csv(p, encoding=e)
        except Exception:
            continue
    return pd.read_csv(p, engine='python', encoding='utf-8', errors='replace')

if len(sys.argv) != 4:
    print("Usage: python scripts\\update_master_from_recover.py <master_csv> <recover_csv> <out_csv>")
    sys.exit(1)

master_p = Path(sys.argv[1])
recover_p = Path(sys.argv[2])
out_p = Path(sys.argv[3])

if not master_p.exists():
    print("Master file not found:", master_p); sys.exit(2)
if not recover_p.exists():
    print("Recover file not found:", recover_p); sys.exit(3)

master = read_robust(master_p)
recover = read_robust(recover_p)

if 'id' not in master.columns:
    master.columns = ['id','prediction']
if 'id' not in recover.columns:
    recover.columns = ['id','prediction']

master.set_index(master.columns[0].strip(), inplace=True)
recover.set_index(recover.columns[0].strip(), inplace=True)

for rid in recover.index:
    master.loc[rid] = recover.loc[rid]

master.reset_index(inplace=True)
master.columns = ['id','prediction']
master.to_csv(out_p, index=False, encoding='utf-8-sig')
print(f"Wrote updated master {out_p} (rows={len(master)})")