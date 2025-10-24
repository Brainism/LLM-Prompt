import json, pathlib, sys
files = [
    "results/quantitative/bleu_sacre.json",
    "results/quantitative/rouge.json",
    "results/quantitative/chrf.json"
]
for f in files:
    p = pathlib.Path(f)
    if not p.exists():
        print(f, "MISSING")
        continue
    try:
        j = json.load(p.open(encoding='utf-8'))
    except Exception as e:
        print(f, "ERROR loading {f} -> {e!r}")
        continue
    print("FILE:", f, "TYPE:", type(j).__name__, "LEN:", len(j) if hasattr(j,'__len__') else "n/a")
    sample = j[:3] if isinstance(j, (list,tuple)) else list(j.items())[:3]
    import json as js
    print("SAMPLE =>")
    print(js.dumps(sample, ensure_ascii=False, indent=2))
    print("-"*60)
