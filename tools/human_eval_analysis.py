import pandas as pd
import numpy as np
from scipy import stats
import json, argparse

def fleiss_kappa(table):
    n, k = table.shape
    n_annotators = table.sum(axis=1)[0]
    p = table.sum(axis=0) / (n * n_annotators)
    P = ( (table * table).sum(axis=1) - n_annotators ) / (n_annotators*(n_annotators-1))
    Pbar = P.mean()
    PbarE = (p * p).sum()
    kappa = (Pbar - PbarE) / (1 - PbarE)
    return kappa

def bootstrap_ci(data, func=np.mean, nboot=10000, seed=42):
    rng = np.random.default_rng(seed)
    boots = []
    arr = np.array(data)
    n = len(arr)
    for _ in range(nboot):
        idx = rng.integers(0,n,n)
        boots.append(func(arr[idx]))
    return np.percentile(boots, [2.5,97.5])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='annotation CSV path')
    parser.add_argument('--out', default='analysis_outputs/human_eval', help='output dir')
    args = parser.parse_args()

    df = pd.read_csv(args.csv, dtype=str)
    for col in ['fluency_base','fluency_instr','adequacy_base','adequacy_instr','compliance_base','compliance_instr']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    agg = df.groupby('item_id').agg({
        'fluency_base': 'mean',
        'fluency_instr': 'mean',
        'adequacy_base': 'mean',
        'adequacy_instr': 'mean',
        'compliance_base': 'sum',
        'compliance_instr': 'sum'
    }).reset_index()

    results = {}
    for metric in [('fluency_base','fluency_instr'), ('adequacy_base','adequacy_instr')]:
        a = agg[metric[0]].dropna().values
        b = agg[metric[1]].dropna().values
        n = min(len(a), len(b))
        if n>0:
            stat, p = stats.wilcoxon(b[:n], a[:n])
            results[metric[0]+'__vs__'+metric[1]] = {'n':n, 'wilcoxon_stat': float(stat), 'p': float(p)}
            lo, hi = bootstrap_ci(b[:n]-a[:n])
            results[metric[0]+'__vs__'+metric[1]]['bootstrap_ci'] = [float(lo), float(hi)]
        else:
            results[metric[0]+'__vs__'+metric[1]] = None

    comp = df[['item_id','compliance_base','compliance_instr']].dropna()
    if not comp.empty:
        comp_major = comp.groupby('item_id').agg({'compliance_base': 'sum', 'compliance_instr': 'sum'})
        n_ann = df['annotator_id'].nunique() if 'annotator_id' in df.columns else None
        if n_ann is None:
            comp_major['base_bin'] = (comp_major['compliance_base'] > 0).astype(int)
            comp_major['instr_bin'] = (comp_major['compliance_instr'] > 0).astype(int)
        else:
            majority_cut = n_ann / 2.0
            comp_major['base_bin'] = (comp_major['compliance_base'] > majority_cut).astype(int)
            comp_major['instr_bin'] = (comp_major['compliance_instr'] > majority_cut).astype(int)
        tb = pd.crosstab(comp_major['base_bin'], comp_major['instr_bin'])
        b_to_i = tb.loc[1,0] if (1 in tb.index and 0 in tb.columns) else 0
        i_to_b = tb.loc[0,1] if (0 in tb.index and 1 in tb.columns) else 0
        from math import sqrt
        n_pair = b_to_i + i_to_b
        if n_pair > 0:
            chi2 = (abs(b_to_i - i_to_b) - 1)**2 / n_pair
            p_mcnemar = 1 - stats.chi2.cdf(chi2, df=1)
        else:
            p_mcnemar = 1.0
        results['compliance_mcnemar'] = {'b_to_i': int(b_to_i), 'i_to_b': int(i_to_b), 'p': float(p_mcnemar)}
    else:
        results['compliance_mcnemar'] = None

    if 'compliance_instr' in df.columns:
        items = df['item_id'].unique()
        table = []
        for it in items:
            sub = df[df['item_id']==it]
            counts = [ (sub['compliance_instr'] == 0).sum(), (sub['compliance_instr'] == 1).sum() ]
            table.append(counts)
        table_np = np.array(table)
        kappa = fleiss_kappa(table_np)
        results['fleiss_kappa_compliance_instr'] = float(kappa)
    else:
        results['fleiss_kappa_compliance_instr'] = None

    summary = {
        'n_items': int(agg.shape[0]),
        'n_annotators': int(df['annotator_id'].nunique()) if 'annotator_id' in df.columns else None,
        'agg_means_sample': agg.head(5).to_dict(orient='records')
    }

    out = {'summary': summary, 'results': results}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    import os
    odir = os.path.dirname(args.out)
    if odir and not os.path.exists(odir):
        os.makedirs(odir)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("Wrote analysis to", args.out)

if __name__ == '__main__':
    main()