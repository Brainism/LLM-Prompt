import json, pathlib
files = [
    "results/quantitative/bleu_sacre.json",
    "results/quantitative/bleu.json",
    "results/quantitative/rouge.json",
    "results/quantitative/chrf.json"
]
for f in files:
    p = pathlib.Path(f)
    if not p.exists():
        print(f, "MISSING")
        continue
    try:
        j = json.load(p.open(encoding="utf-8"))
        try:
            n = len(j)
        except Exception:
            n = "n/a"
        print(f, "type", type(j).__name__, "len", n)
    except Exception as e:
        print(f, "ERROR loading", f, "->", repr(e))
