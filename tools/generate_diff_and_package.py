import os, argparse, json, csv, zipfile
import pandas as pd
import numpy as np
from scipy import stats

def read_items(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv',):
        df = pd.read_csv(path)
    elif ext in ('.json',):
        with open(path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        if isinstance(j, list):
            df = pd.DataFrame(j)
        elif isinstance(j, dict) and 'items' in j and isinstance(j['items'], list):
            df = pd.DataFrame(j['items'])
        else:
            df = pd.DataFrame([j])
    elif ext in ('.jsonl', '.ndjson'):
        rows=[]
        with open(path,'r',encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if not line: continue
                rows.append(json.loads(line))
        df = pd.DataFrame(rows)
    else:
        raise RuntimeError("Unsupported file extension: "+ext)
    cols = {c.lower():c for c in df.columns}
    id_col = None
    for cand in ('id','item','example'):
        if cand in cols:
            id_col = cols[cand]
            break
    base_col = None; instr_col = None
    for c in df.columns:
        low = c.lower()
        if 'base' in low and 'bleu' in low:
            base_col = c
        if 'instr' in low and 'bleu' in low:
            instr_col = c
    if base_col is None:
        for c in df.columns:
            if 'base'==c.lower():
                base_col = c
    if instr_col is None:
        for c in df.columns:
            if 'instr'==c.lower():
                instr_col = c
    if base_col is None or instr_col is None:
        bleu_cols = [c for c in df.columns if 'bleu' in c.lower()]
        if len(bleu_cols) >= 2:
            if base_col is None: base_col = bleu_cols[0]
            if instr_col is None: instr_col = bleu_cols[1]
    if base_col is None or instr_col is None:
        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric) >= 2:
            if base_col is None: base_col = numeric[0]
            if instr_col is None: instr_col = numeric[1]
    if id_col is None:
        df = df.reset_index().rename(columns={'index':'_tmp_index'})
        df['_tmp_index'] = df['_tmp_index'].apply(lambda x: f"EX-{x+1:04d}")
        id_col = '_tmp_index'
    use_cols = []
    for c in (id_col, base_col, instr_col):
        if c is not None:
            use_cols.append(c)
    df2 = df[use_cols].copy()
    rename_map = {}
    rename_map[id_col] = 'id'
    if base_col is not None: rename_map[base_col] = 'base'
    if instr_col is not None: rename_map[instr_col] = 'instr'
    df2 = df2.rename(columns=rename_map)
    return df2

def paired_tests_and_bootstrap(base_arr, instr_arr, nboot=5000, seed=42):
    n = min(len(base_arr), len(instr_arr))
    base = np.array(base_arr[:n], dtype=float)
    instr = np.array(instr_arr[:n], dtype=float)
    t_res = stats.ttest_rel(instr, base)
    try:
        wil = stats.wilcoxon(instr, base)
        wil_p = float(wil.pvalue)
    except Exception:
        wil = None; wil_p = None
    rng = np.random.default_rng(seed)
    diffs=[]
    for _ in range(nboot):
        idx = rng.integers(0,n,n)
        diffs.append(np.mean(instr[idx]) - np.mean(base[idx]))
    diffs = np.array(diffs)
    ci_low, ci_high = np.percentile(diffs,[2.5,97.5])
    cohend = np.mean(instr-base) / (np.std(instr-base, ddof=1) if np.std(instr-base, ddof=1)!=0 else np.nan)
    return {
        'n': n,
        'mean_base': float(base.mean()),
        'mean_instr': float(instr.mean()),
        'mean_diff': float(instr.mean()-base.mean()),
        't_stat': float(t_res.statistic),
        't_p': float(t_res.pvalue),
        'wil_stat': None if wil is None else float(wil.statistic),
        'wil_p': wil_p,
        'bootstrap_ci': [float(ci_low), float(ci_high)],
        'cohen_d': float(cohend)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fileA', required=True, help='path to first per-item file (CSV/JSON/JSONL)')
    parser.add_argument('--fileB', required=True, help='path to second per-item file (CSV/JSON/JSONL)')
    parser.add_argument('--figs', required=False, help='path to figs dir to include', default='figs')
    parser.add_argument('--outdir', required=False, help='output directory', default='output_package')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    dfA = read_items(args.fileA)
    dfB = read_items(args.fileB)
    dfA['id'] = dfA['id'].astype(str)
    dfB['id'] = dfB['id'].astype(str)
    dfA.to_csv(os.path.join(args.outdir, 'per_item_A.csv'), index=False)
    dfB.to_csv(os.path.join(args.outdir, 'per_item_B.csv'), index=False)

    idsA = set(dfA['id'].tolist())
    idsB = set(dfB['id'].tolist())
    onlyA = sorted(list(idsA - idsB))
    onlyB = sorted(list(idsB - idsA))
    both = sorted(list(idsA & idsB))

    pd.DataFrame({'id':onlyA}).to_csv(os.path.join(args.outdir,'only_in_A.csv'), index=False)
    pd.DataFrame({'id':onlyB}).to_csv(os.path.join(args.outdir,'only_in_B.csv'), index=False)
    pd.DataFrame({'id':both}).to_csv(os.path.join(args.outdir,'in_both.csv'), index=False)

    merged = pd.merge(dfA, dfB, on='id', how='outer', suffixes=('_A','_B'))
    merged.to_csv(os.path.join(args.outdir,'per_item_table.csv'), index=False)

    inter = merged.dropna(subset=['base_A','base_B','instr_A','instr_B'], how='any')
    if 'base_A' in inter.columns and 'instr_B' in inter.columns:
        base_vals = pd.to_numeric(inter['base_A'], errors='coerce')
        instr_vals = pd.to_numeric(inter['instr_B'], errors='coerce')
        stats_res = paired_tests_and_bootstrap(base_vals.values, instr_vals.values, nboot=10000, seed=42)
        with open(os.path.join(args.outdir,'stats_tests_output.txt'),'w', encoding='utf-8') as fh:
            fh.write(json.dumps(stats_res, indent=2))
    else:
        if 'base' in dfA.columns and 'instr' in dfA.columns:
            stats_res = paired_tests_and_bootstrap(dfA['base'].values, dfA['instr'].values, nboot=10000, seed=42)
            with open(os.path.join(args.outdir,'stats_tests_output.txt'),'w', encoding='utf-8') as fh:
                fh.write(json.dumps(stats_res, indent=2))
        else:
            with open(os.path.join(args.outdir,'stats_tests_output.txt'),'w', encoding='utf-8') as fh:
                fh.write('No paired numeric base/instr columns found to run tests.')

    with open(os.path.join(args.outdir,'README_repro.md'),'w', encoding='utf-8') as fh:
        fh.write('# Repro README\\nProvide the venv and run instructions here.')
    with open(os.path.join(args.outdir,'human_eval_plan.md'),'w', encoding='utf-8') as fh:
        fh.write('Human eval plan placeholder. See main script for details.')

    zipname = os.path.abspath(os.path.join(args.outdir, '..', 'final_package.zip'))
    with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root,dirs,files in os.walk(args.outdir):
            for f in files:
                zf.write(os.path.join(root,f), arcname=os.path.join(os.path.relpath(root,args.outdir),f))
        if os.path.exists(args.figs):
            for root,dirs,files in os.walk(args.figs):
                for f in files:
                    arc = os.path.join('figs', os.path.relpath(os.path.join(root,f), args.figs))
                    zf.write(os.path.join(root,f), arcname=arc)
    print('Wrote package to', zipname)

if __name__ == '__main__':
    main()