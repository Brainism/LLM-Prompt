import os, json, argparse
import pandas as pd
import numpy as np
from scipy import stats

def read_jsonl(path):
    rows=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line: continue
            rows.append(json.loads(line))
    return pd.DataFrame(rows)

def bootstrap_ci_mean_diff(a,b,nboot=10000,seed=42):
    rng = np.random.default_rng(seed)
    n = min(len(a), len(b))
    diffs=[]
    for _ in range(nboot):
        idx = rng.integers(0, n, n)
        diffs.append(np.mean(b[idx] - a[idx]))
    diffs = np.array(diffs)
    return np.percentile(diffs, [2.5,97.5])

def safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except:
        return None

def to_py(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, list):
        return [to_py(x) for x in obj]
    return obj

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full60', required=True)
    parser.add_argument('--subset50', required=True)
    parser.add_argument('--outdir', default='C:\\Project\\LLM\\analysis_outputs')
    parser.add_argument('--nboot', type=int, default=10000)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    full = pd.read_csv(args.full60)
    if args.subset50.endswith('.jsonl') or args.subset50.endswith('.ndjson'):
        subset = read_jsonl(args.subset50)
    else:
        subset = pd.read_csv(args.subset50)

    full['id'] = full['id'].astype(str)
    subset['id'] = subset['id'].astype(str)

    merged = full.merge(subset, on='id', how='outer', suffixes=('_full','_sub'))
    merged.to_csv(os.path.join(args.outdir,'per_item_table.csv'), index=False)

    ids_full = set(full['id'].tolist())
    ids_sub = set(subset['id'].tolist())
    only_in_full = sorted(list(ids_full - ids_sub))
    only_in_sub = sorted(list(ids_sub - ids_full))
    in_both = sorted(list(ids_full & ids_sub))
    pd.DataFrame({'id':only_in_full}).to_csv(os.path.join(args.outdir,'only_in_A.csv'), index=False)
    pd.DataFrame({'id':only_in_sub}).to_csv(os.path.join(args.outdir,'only_in_B.csv'), index=False)
    pd.DataFrame({'id':in_both}).to_csv(os.path.join(args.outdir,'in_both.csv'), index=False)

    full_base = pd.to_numeric(full['base'], errors='coerce').dropna().values
    full_instr = pd.to_numeric(full['instr'], errors='coerce').dropna().values
    sub_base = pd.to_numeric(subset['base'], errors='coerce').dropna().values
    sub_instr = pd.to_numeric(subset['instr'], errors='coerce').dropna().values

    summary = {}
    summary['full_n'] = int(len(full))
    summary['full_mean_base'] = float(np.mean(full_base)) if len(full_base)>0 else None
    summary['full_mean_instr'] = float(np.mean(full_instr)) if len(full_instr)>0 else None
    summary['full_mean_diff'] = float(np.mean(full_instr - full_base)) if len(full_base)>0 and len(full_instr)>0 else None

    summary['sub_n'] = int(len(subset))
    summary['sub_mean_base'] = float(np.mean(sub_base)) if len(sub_base)>0 else None
    summary['sub_mean_instr'] = float(np.mean(sub_instr)) if len(sub_instr)>0 else None
    summary['sub_mean_diff'] = float(np.mean(sub_instr - sub_base)) if len(sub_base)>0 and len(sub_instr)>0 else None

    nA = min(len(full_base), len(full_instr))
    if nA > 0:
        tA = stats.ttest_rel(full_instr[:nA], full_base[:nA])
        ciA = bootstrap_ci_mean_diff(full_base[:nA], full_instr[:nA], nboot=args.nboot)
        dA = np.mean(full_instr[:nA]-full_base[:nA]) / (np.std(full_instr[:nA]-full_base[:nA], ddof=1) if np.std(full_instr[:nA]-full_base[:nA], ddof=1)!=0 else np.nan)
    else:
        tA = None; ciA = [None,None]; dA = None

    merged_xy = merged.dropna(subset=['base_full','instr_sub'])
    if not merged_xy.empty:
        bvals = pd.to_numeric(merged_xy['base_full'], errors='coerce').values
        ivals = pd.to_numeric(merged_xy['instr_sub'], errors='coerce').values
        tB = stats.ttest_rel(ivals, bvals)
        ciB = bootstrap_ci_mean_diff(bvals, ivals, nboot=args.nboot)
        dB = np.mean(ivals-bvals) / (np.std(ivals-bvals, ddof=1) if np.std(ivals-bvals, ddof=1)!=0 else np.nan)
    else:
        tB = None; ciB = [None,None]; dB = None

    out_stats = {
        'summary': summary,
        'paired_full': {
            'n': int(nA),
            't_stat': safe_float(tA.statistic) if tA is not None else None,
            't_p': safe_float(tA.pvalue) if tA is not None else None,
            'bootstrap_ci': to_py(ciA),
            'cohen_d': safe_float(dA)
        },
        'paired_intersection': {
            'n': int(len(merged_xy)),
            't_stat': safe_float(tB.statistic) if tB is not None else None,
            't_p': safe_float(tB.pvalue) if tB is not None else None,
            'bootstrap_ci': to_py(ciB),
            'cohen_d': safe_float(dB)
        }
    }

    with open(os.path.join(args.outdir,'stats_tests_output.txt'),'w',encoding='utf-8') as fh:
        fh.write(json.dumps(out_stats, indent=2, ensure_ascii=False))

    full['delta_full'] = pd.to_numeric(full['instr'], errors='coerce') - pd.to_numeric(full['base'], errors='coerce')
    full = full.sort_values(by='delta_full', ascending=False)
    full[['id','base','instr','delta_full']].to_csv(os.path.join(args.outdir,'top_deltas_full.csv'), index=False)

    deltas = full[['id','delta_full']].dropna()
    deltas['abs_delta'] = deltas['delta_full'].abs()
    deltas = deltas.sort_values(by='delta_full', ascending=False)
    deltas['cum_mean_contrib'] = deltas['delta_full'].cumsum() / len(full)
    deltas.to_csv(os.path.join(args.outdir,'top_contributors.csv'), index=False)

    print("Wrote outputs to", args.outdir)
    print("Full mean diff:", summary['full_mean_diff'])
    print("Subset mean diff:", summary['sub_mean_diff'])
    print("Paired (full) t p-value:", out_stats['paired_full']['t_p'])
    print("Paired (intersection) t p-value:", out_stats['paired_intersection']['t_p'])

if __name__ == '__main__':
    main()