import json, csv, pathlib

METRIC_FILES = {
    'bleu_sacre': pathlib.Path('results/quantitative/bleu_sacre.json'),
    'rouge': pathlib.Path('results/quantitative/rouge.json'),
    'chrf': pathlib.Path('results/quantitative/chrf.json'),
}

OUT_CSV = pathlib.Path('results/quantitative/per_item_diffs.csv')

def load_metrics():
    data = {}
    for name, path in METRIC_FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"Metric file not found: {path}")
        arr = json.load(path.open(encoding='utf-8'))
        for it in arr:
            iid = it.get('id')
            if iid is None:
                continue
            data.setdefault(iid, {})[name] = (it.get('base'), it.get('instr'))
    return data

def write_csv(data):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    headers = ['id']
    for m in METRIC_FILES.keys():
        headers += [f'{m}_base', f'{m}_instr', f'{m}_diff']
    with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for iid in sorted(data.keys()):
            row = [iid]
            for m in METRIC_FILES.keys():
                b_i = data[iid].get(m, (None, None))
                b, i = b_i
                diff = None
                try:
                    if b is not None and i is not None:
                        diff = float(i) - float(b)
                except Exception:
                    diff = None
                row += [b, i, diff]
            w.writerow(row)
    print(f"[OK] wrote {OUT_CSV}")

if __name__ == '__main__':
    d = load_metrics()
    write_csv(d)