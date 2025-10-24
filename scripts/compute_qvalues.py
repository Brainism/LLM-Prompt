import csv, pathlib

IN_CSV = pathlib.Path('results/quantitative/p_values_input.csv')
OUT_CSV = pathlib.Path('results/quantitative/p_q_values.csv')

def bh_qvalues(pvals):
    m = len(pvals)
    indexed = sorted(enumerate(pvals), key=lambda x: x[1])
    bh = [0.0]*m
    for rank, (idx, p) in enumerate(indexed, start=1):
        bh_val = p * m / rank
        bh[rank-1] = bh_val
    for i in range(m-2, -1, -1):
        if bh[i] > bh[i+1]:
            bh[i] = bh[i+1]
    q = [None]*m
    for (rank, (idx, p)), qv in zip(enumerate(indexed, start=1), bh):
        orig_idx = indexed[rank-1][0]
        q[orig_idx] = min(qv, 1.0)
    return q

def read_input(path):
    if not path.exists():
        raise FileNotFoundError(f"Provide {path} with rows 'metric,p'")
    rows = []
    with path.open(encoding='utf-8') as f:
        r = csv.reader(f)
        next(r)  # header
        for row in r:
            if not row: continue
            metric = row[0].strip()
            p = float(row[1])
            rows.append((metric, p))
    return rows

def write_output(rows, qs):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric','p','q_bh'])
        for (metric, p), q in zip(rows, qs):
            w.writerow([metric, p, q])
    print(f"[OK] wrote {OUT_CSV}")

if __name__ == '__main__':
    rows = read_input(IN_CSV)
    pvals = [r[1] for r in rows]
    qs = bh_qvalues(pvals)
    write_output(rows, qs)