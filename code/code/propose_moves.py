from pathlib import Path
import csv, re

ROOT=Path(".").resolve()
OUT=Path("results/admin"); OUT.mkdir(parents=True, exist_ok=True)
proposals=[]

def target_for(p: Path) -> str:
    s=p.name.lower()
    if s.endswith(".ipynb"): return f"notebooks/{p.name}"
    if re.search(r"(stats_.*|.*_stats).*\.py", s): return f"code/{p.name}"
    if "sacre" in s and s.endswith(".py"): return f"code/metrics_sacre.py" if s=="sacre_eval.py" else f"code/{p.name}"
    if "align" in s and s.endswith(".py"): return f"code/prep_aligned.py" if s=="aligned_texts.py" else f"code/{p.name}"
    if s.endswith(".py"): return f"code/{p.name}"
    if s.endswith(".jsonl") and "reference" in str(p).lower(): return f"reference/{p.name}"
    if s.endswith(".jsonl") and "batch" in str(p).lower(): return f"results/batch_outputs/{p.name}"
    if s.endswith(".csv") and "diffs" in s: return f"results/quantitative/{p.name}"
    if s.endswith(".json") and any(k in s for k in ["bleu","chrf","rouge"]): return f"results/quantitative/{p.name}"
    if s.endswith((".png",".svg",".pdf")): return f"results/figures/{p.name}"
    if s.endswith((".md",".txt")): return f"docs/{p.name}"
    return str(p).replace(str(ROOT)+"\\","")  # default keep

for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    if any(seg in {".git",".venv","venv","__pycache__",".vscode",".idea","results\\admin"} for seg in p.parts):
        continue
    dst = Path(target_for(p))
    if str(dst).replace("\\","/") != str(p).replace(str(ROOT)+"\\","").replace("\\","/"):
        proposals.append([str(p), str(dst)])

with (OUT/"move_map.csv").open("w", newline="", encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["src","dst"])
    w.writerows(proposals)

print(f"[OK] wrote {OUT/'move_map.csv'} ({len(proposals)} proposals)")