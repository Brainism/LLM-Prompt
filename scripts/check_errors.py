import json
from pathlib import Path

def check(path):
    p = Path(path)
    if not p.exists():
        print(f"NOT FOUND: {path}")
        return
    n=0
    ids=[]
    for ln in p.read_text(encoding='utf-8').splitlines():
        if not ln.strip(): continue
        j=json.loads(ln)
        if j.get("error"):
            n+=1
            ids.append((j.get("id"), j.get("error")))
    print(path, "errors:", n)
    if n:
        for i,e in ids[:50]:
            print(i, ":", e)

if __name__ == '__main__':
    check("results/raw/general.jsonl")
    check("results/raw/instructed.jsonl")