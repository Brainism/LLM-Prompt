import json, math, pathlib, sys

files = [
    ("BLEU", "results/quantitative/bleu_sacre.json"),
    ("ROUGE", "results/quantitative/rouge.json"),
    ("CHR F", "results/quantitative/chrf.json"),
]

for name, path in files:
    p = pathlib.Path(path)
    if not p.exists():
        print(f"{name}: MISSING -> {path}")
        continue
    try:
        j = json.load(p.open(encoding="utf-8"))
    except Exception as e:
        print(f"{name}: ERROR loading {path} -> {e!r}")
        continue
    total = 0
    valid = 0
    sum_b = 0.0
    sum_i = 0.0
    sample = []
    for it in j:
        total += 1
        b = it.get("base") if isinstance(it, dict) else None
        i = it.get("instr") if isinstance(it, dict) else None
        ok = isinstance(b, (int,float)) and isinstance(i, (int,float)) and not (math.isnan(b) or math.isnan(i))
        if ok:
            valid += 1
            sum_b += float(b)
            sum_i += float(i)
            if len(sample) < 5:
                sample.append((it.get("id"), b, i))
    print(f"{name}: file={path} total_items={total} valid_pairs={valid} mean_base={sum_b/valid if valid else 'N/A'} mean_instr={sum_i/valid if valid else 'N/A'}")
    print(" sample (first up to 5 valid):", sample)
    print("-"*60)