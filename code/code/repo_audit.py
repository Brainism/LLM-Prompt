from pathlib import Path
import hashlib, csv, sys, os

ROOT = Path(".").resolve()
IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".vscode", ".idea"}
TEXT_EXT = {".py", ".md", ".txt", ".csv", ".json", ".jsonl", ".yml", ".yaml", ".ipynb"}
OUT = Path("results/admin"); OUT.mkdir(parents=True, exist_ok=True)

def sha256(p: Path, chunk=1024*1024):
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def is_text(p: Path):
    try:
        if p.suffix.lower() in TEXT_EXT: return True
        with p.open("rb") as f: f.read(4096).decode("utf-8")
        return True
    except Exception:
        return False

rows=[]
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    if any(seg in IGNORE_DIRS for seg in p.parts): continue
    try:
        size = p.stat().st_size
        h = sha256(p)
        kind = "text" if is_text(p) else "bin"
        rows.append([str(p), size, h, kind])
    except Exception as e:
        print("[warn]", p, e, file=sys.stderr)

# CSV 저장
audit_csv = OUT / "repo_audit.csv"
with audit_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["path","bytes","sha256","kind"])
    w.writerows(rows)

# 요약(중복/대용량)
from collections import defaultdict
by_hash=defaultdict(list)
for path,size,h,kind in rows: by_hash[h].append((path,int(size),kind))
dups=[(h,v) for h,v in by_hash.items() if len(v)>1]
dups.sort(key=lambda x: -sum(s for _,s,_ in x[1]))

large=[r for r in rows if int(r[1])>=5_000_000]  # 5MB+
large.sort(key=lambda r: -int(r[1]))

dup_csv = OUT / "duplicates.csv"
with dup_csv.open("w", newline="", encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["sha256","n","total_bytes","paths"])
    for h,items in dups:
        total=sum(s for _,s,_ in items)
        w.writerow([h,len(items),total," | ".join(p for p,_,_ in items)])

large_csv = OUT / "large_files.csv"
with large_csv.open("w", newline="", encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["path","bytes","kind"])
    w.writerows(large)

print(f"[OK] wrote {audit_csv}, {dup_csv}, {large_csv}")