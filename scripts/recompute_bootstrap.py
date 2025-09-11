import json, random, csv, argparse, pathlib
from statistics import mean

METRICS = [
    ('bleu_sacre','results/quantitative/bleu_sacre.json'),
    ('rouge','results/quantitative/rouge.json'),
    ('chrf','results/quantitative/chrf.json'),
]

def load_pairs(path):
    j = json.load(open(path,encoding='utf-8'))
    pairs = [(it['id'], float(it['base']), float(it['instr'])) for it in j]
    return pairs

def bootstrap_ci(diffs, nboot=10000, alpha=0.05):
    n = len(diffs)
    boots=[]
    for _ in range(nboot):
        sample = [diffs[random.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    boots.sort()
    lo = boots[int((alpha/2)*nboot)]
    hi = boots[int((1-alpha/2)*nboot)]
    return lo, hi

def compute_for(metric, path, nboot):
    pairs = load_pairs(path)
    base = [p[1] for p in pairs]
    instr = [p[2] for p in pairs]
    diffs = [i-b for b,i in zip(base, instr)]
    mean_b = mean(base)
    mean_i = mean(instr)
    delta = mean(diffs)
    ci_lo, ci_hi = bootstrap_ci(diffs, nboot=nboot)
    return {
        'metric': metric, 'n': len(diffs), 'mean_base': mean_b, 'mean_instr': mean_i,
        'delta': delta, 'ci_lo': ci_lo, 'ci_hi': ci_hi
    }

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--nboot', type=int, default=10000)
    p.add_argument('--out', type=str, default='results/quantitative/stats_bootstrap.csv')
    args = p.parse_args()
    outp = pathlib.Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    rows=[]
    for name, path in METRICS:
        path = pathlib.Path(path)
        if not path.exists():
            print("[WARN] missing", path)
            continue
        rows.append(compute_for(name, path, args.nboot))
    with outp.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric','n','mean_base','mean_instr','delta','ci_lo','ci_hi'])
        for r in rows:
            w.writerow([r['metric'], r['n'], r['mean_base'], r['mean_instr'], r['delta'], r['ci_lo'], r['ci_hi']])
    print("[OK] wrote", outp, "(nboot=", args.nboot, ")")