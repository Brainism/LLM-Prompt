from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [
    root / "results" / "aligned" / "refs.txt",
    root / "results" / "aligned" / "hyps_general.txt",
    root / "results" / "aligned" / "hyps_instructed.txt",
]

for p in files:
    if not p.exists():
        print(f"{p} MISSING")
        continue
    t = p.read_text(encoding="utf-8").splitlines()
    nonempty = sum(1 for x in t if x.strip())
    print(str(p), "lines=", len(t), "nonempty=", nonempty)
    print("sample:", (t[0][:120] if t else "<empty>"))