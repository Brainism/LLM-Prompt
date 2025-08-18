from pathlib import Path
import csv, shutil

MAP=Path("results/admin/move_map.csv")
ROOT=Path(".").resolve()

with MAP.open(encoding="utf-8") as f:
    for i,row in enumerate(csv.DictReader(f)):
        src=ROOT/row["src"]; dst=ROOT/row["dst"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not src.exists(): 
            print(f"[skip] missing: {src}"); continue
        if dst.exists():
            print(f"[keep] exists: {dst} (skip {src})"); continue
        print(f"[move] {src} -> {dst}")
        shutil.move(str(src), str(dst))
print("[OK] done.")
