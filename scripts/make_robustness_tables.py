import os, csv, json, re, argparse
from collections import defaultdict

def sniff_csv(path, sample_bytes=4096):
    with open(path, 'rb') as fb: raw = fb.read(sample_bytes)
    text = raw.decode('utf-8-sig', errors='replace')
    try: dialect = csv.Sniffer().sniff(text)
    except Exception: dialect = csv.excel
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        r = csv.reader(f, dialect); headers = next(r, [])
    return dialect, [h.strip() for h in headers]

def best_header(headers, candidates, fuzzy=None):
    if not headers: return None
    for c in candidates:
        if c in headers: return c
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower: return lower[c.lower()]
    if fuzzy:
        pat = re.compile(fuzzy, re.I)
        for h in headers:
            if pat.search(h): return h
    return None

def load_items(qdir, name):
    path = os.path.join(qdir, f'{name}.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f'[ERR] metric file missing: {path}')
    obj = json.load(open(path, 'r', encoding='utf-8'))
    if isinstance(obj, dict) and isinstance(obj.get('items'), list): src = obj['items']
    elif isinstance(obj, list): src = obj
    else: raise ValueError(f'[ERR] Unsupported JSON shape in {path}')
    out = {}
    for x in src:
        if not isinstance(x, dict): continue
        rid = x.get('id')
        if rid is None: continue
        try:
            base = float(x.get('base', 0) or 0)
            instr = float(x.get('instr', 0) or 0)
        except Exception:
            continue
        out[str(rid)] = (base, instr)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompts', default='prompts/main.csv')
    ap.add_argument('--quant',   default='results/quantitative')
    ap.add_argument('--out',     default='tables/robustness.csv')
    ap.add_argument('--id-col',   default=None)
    ap.add_argument('--lang-col', default=None)
    ap.add_argument('--len-col',  default=None)
    ap.add_argument('--diff-col', default=None)
    ap.add_argument('--metrics',  default='bleu_sacre,chrf,rouge')
    args = ap.parse_args()

    metric_names = [m.strip() for m in args.metrics.split(',') if m.strip()]
    mdata = {m: load_items(args.quant, m) for m in metric_names}

    dialect, headers = sniff_csv(args.prompts)
    id_syn   = ['id','ID','Id','index','example_id','ex_id','sample_id','item_id','rid']
    lang_syn = ['lang','language','locale']
    len_syn  = ['len_bin','length_bin','len','length']
    diff_syn = ['diff_bin','difficulty','difficulty_bin','diff']

    id_col   = args.id_col   or best_header(headers, id_syn,   r'^id$|index|_id$')
    lang_col = args.lang_col or best_header(headers, lang_syn, r'lang|language|locale')
    len_col  = args.len_col  or best_header(headers, len_syn,  r'len|length')
    diff_col = args.diff_col or best_header(headers, diff_syn, r'diff')
    if not id_col: raise ValueError(f'[ERR] Cannot detect id column. headers={headers}')
    if not (lang_col and len_col and diff_col):
        raise ValueError(f'[ERR] Need lang/len_bin/diff_bin columns. detected: lang={lang_col}, len={len_col}, diff={diff_col}')

    groups = defaultdict(list)
    with open(args.prompts, 'r', encoding='utf-8-sig', newline='') as f:
        R = csv.DictReader(f, dialect=dialect)
        for r in R:
            rid = (r.get(id_col) or '').strip()
            if not rid: continue
            if not all(str(rid) in mdata[m] for m in metric_names): continue
            lang = (r.get(lang_col) or '').strip() or 'NA'
            lbin = (r.get(len_col)  or '').strip() or 'NA'
            dbin = (r.get(diff_col) or '').strip() or 'NA'
            groups[(lang, lbin, dbin)].append(str(rid))
    if not groups:
        raise RuntimeError('[ERR] No overlapping ids across prompts and metric files.')

    def avg_delta(metric_map, ids):
        vals = [(metric_map[i][1] - metric_map[i][0]) for i in ids]
        return sum(vals)/len(vals) if vals else 0.0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    label_map = {'bleu_sacre':'BLEUΔ','chrf':'chrFΔ','rouge':'ROUGEΔ'}
    header = ['lang','len_bin','diff_bin','n'] + [label_map.get(m,f'{m}Δ') for m in metric_names]
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        W = csv.writer(f); W.writerow(header)
        for (lang,lbin,dbin), ids in sorted(groups.items()):
            row = [lang,lbin,dbin,len(ids)]
            for m in metric_names: row.append(avg_delta(mdata[m], ids))
            W.writerow(row)
    print(f'[OK] wrote {args.out} (groups={len(groups)}, metrics={metric_names})')

if __name__ == '__main__':
    main()