import sys
import pandas as pd

if len(sys.argv) < 3:
    print("Usage: python scripts/compare_pairs.py <master.csv> <recover.csv>")
    sys.exit(1)

master_csv = sys.argv[1]
recover_csv = sys.argv[2]

m = pd.read_csv(master_csv, index_col='id', dtype=str).fillna('')
r = pd.read_csv(recover_csv, index_col='id', dtype=str).fillna('')

ids = sorted(set(m.index).union(r.index))
diffs = []
for i in ids:
    old = m.loc[i,'prediction'] if i in m.index else '<MISSING>'
    new = r.loc[i,'prediction'] if i in r.index else '<MISSING>'
    if old != new:
        diffs.append((i, old, new))

if not diffs:
    print("No differences found between", master_csv, "and", recover_csv)
else:
    print(f"Found {len(diffs)} differing ids:")
    for i, old, new in diffs:
        print("----")
        print(i)
        print("OLD (truncated 300 chars):")
        print(old[:300].replace("\n"," "))
        print("NEW (truncated 300 chars):")
        print(new[:300].replace("\n"," "))