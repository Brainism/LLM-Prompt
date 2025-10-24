import json
from pathlib import Path

def load(fn):
    p=Path(fn)
    return {j['id']: j.get('output','') for j in (json.loads(ln) for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip())}

g = load("results/raw/general.jsonl")
i = load("results/raw/instructed.jsonl")
ids = sorted(set(g.keys()) & set(i.keys()))
same = sum(1 for id_ in ids if (g.get(id_,"").strip() == i.get(id_,"").strip()))
print(f"n_ids: {len(ids)}, identical outputs: {same}, identical%: {same/len(ids)*100:.1f}%")
# optional: print a few diffs
for id_ in ids[:10]:
    if g.get(id_,"").strip() != i.get(id_,"").strip():
        print("DIFF:", id_)
        print(" G:", g.get(id_)[:200].replace('\\n','\\n'))
        print(" I:", i.get(id_)[:200].replace('\\n','\\n'))