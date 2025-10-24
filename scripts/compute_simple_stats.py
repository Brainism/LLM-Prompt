import json, random, math, pathlib
from statistics import mean
try:
    from scipy.stats import wilcoxon
    SCIPY = True
except Exception:
    SCIPY = False

def load_metric(path):
    j = json.load(open(path, encoding='utf-8'))
    pairs = [(it['id'], float(it['base']), float(it['instr'])) for it in j]
    return pairs

def bootstrap_ci(diffs, nboot=10000, alpha=0.05):
    n = len(diffs)
    boots = []
    for _ in range(nboot):
        sample = [diffs[random.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    boots.sort()
    lo = boots[int((alpha/2)*nboot)]
    hi = boots[int((1-alpha/2)*nboot)]
    return lo, hi

def compute(path):
    pairs = load_metric(path)
    ids = [p[0] for p in pairs]
    base = [p[1] for p in pairs]
    instr = [p[2] for p in pairs]
    diffs = [i - b for b, i in zip(base, instr)]
    n = len(diffs)
    mean_b = mean(base)
    mean_i = mean(instr)
    delta = mean(diffs)
    delta_pct = (delta / mean_b * 100) if mean_b != 0 else float('nan')
    sd_diff = (sum((d - delta)**2 for d in diffs) / (n-1))**0.5 if n > 1 else 0.0
    d = delta / sd_diff if sd_diff > 0 else float('nan')
    ci_lo, ci_hi = bootstrap_ci(diffs, nboot=10000)
    w_p = None
    if SCIPY:
        try:
            stat, p = wilcoxon(base, instr)
            w_p = p
        except Exception:
            w_p = None
    return {
        'n': n, 'mean_base': mean_b, 'mean_instr': mean_i, 'delta': delta,
        'delta_pct': delta_pct, 'sd_diff': sd_diff, 'd': d, 'ci_low': ci_lo, 'ci_high': ci_hi,
        'wilcoxon_p': w_p
    }

if __name__ == '__main__':
    metrics = [
        ('bleu_sacre', 'results/quantitative/bleu_sacre.json'),
        ('rouge', 'results/quantitative/rouge.json'),
        ('chrf', 'results/quantitative/chrf.json'),
    ]
    out = []
    for name, path in metrics:
        p = pathlib.Path(path)
        if not p.exists():
            print(f"[WARN] metric file not found: {path}")
            continue
        try:
            stat = compute(path)
            stat['metric'] = name
            out.append(stat)
        except Exception as e:
            print('[ERR]', name, e)
    import csv
    outp = pathlib.Path('results/quantitative/stats_simple_after_retry.csv')
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric','n','mean_base','mean_instr','delta','delta_pct','sd_diff','d','ci_low','ci_high','wilcoxon_p'])
        for s in out:
            w.writerow([s['metric'], s['n'], s['mean_base'], s['mean_instr'], s['delta'], s['delta_pct'], s['sd_diff'], s['d'], s['ci_low'], s['ci_high'], s['wilcoxon_p']])
    print('[OK] wrote', outp)
    if not SCIPY:
        print('[INFO] scipy not installed — Wilcoxon p-value omitted. Install scipy to enable it.')