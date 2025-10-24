import os, json
import pandas as pd
import numpy as np
from scipy import stats

OUT = r"C:\Project\LLM\analysis_outputs"
os.makedirs(OUT, exist_ok=True)
PT = r"C:\Project\LLM\analysis_outputs\per_item_table.csv"

def normalize_cols(df):
    newcols = []
    for c in df.columns:
        if isinstance(c, str):
            c2 = c.strip().replace('\ufeff','').lower()
        else:
            c2 = str(c)
        newcols.append(c2)
    df.columns = newcols
    return df

def find_col(df, candidates):
    for cand in candidates:
        cand2 = cand.lower()
        if cand2 in df.columns:
            return cand2
    return None

df = pd.read_csv(PT, dtype=str)
df = normalize_cols(df)

base_a_col = find_col(df, ['base_a','base_full','base','base_full_a','base_a.'])
instr_a_col = find_col(df, ['instr_a','instr_full','instr','instr_a.'])
base_b_col = find_col(df, ['base_b','base_sub','base_b.','base_sub_b'])
instr_b_col = find_col(df, ['instr_b','instr_sub','instr_b.','instr_sub_b'])

if base_a_col is None or instr_a_col is None:
    numeric_cols = [c for c in df.columns if all(x.replace('.','',1).replace('-','',1).isdigit() or x.strip()=='' for x in df[c].dropna().astype(str).head(5))]

def to_num(col):
    try:
        return pd.to_numeric(df[col], errors='coerce')
    except:
        return None

if base_a_col and instr_a_col:
    base_a = to_num(base_a_col)
    instr_a = to_num(instr_a_col)
else:
    raise RuntimeError("Could not find base/instr columns for A. Available columns: " + ", ".join(df.columns))

mask = base_a.notna() & instr_a.notna()
base_vals = base_a[mask].astype(float).values
instr_vals = instr_a[mask].astype(float).values
n = min(len(base_vals), len(instr_vals))
mean_diff = float(np.nanmean(instr_vals - base_vals)) if n>0 else float('nan')

rng = np.random.default_rng(42)
boots = []
if n>0:
    for _ in range(20000):
        idx = rng.integers(0,n,n)
        boots.append(np.mean(instr_vals[idx] - base_vals[idx]))
    lo, hi = np.percentile(boots, [2.5,97.5])
else:
    lo, hi = None, None

if n>0:
    tstat, tp = stats.ttest_rel(instr_vals[:n], base_vals[:n])
else:
    tstat, tp = None, None

df['delta_full'] = instr_a.astype(float) - base_a.astype(float)
top = df[['id','delta_full']].dropna().sort_values('delta_full', ascending=False)
top['abs_delta'] = top['delta_full'].abs()
top['cum_mean_contrib'] = top['delta_full'].cumsum() / len(df)

top.to_csv(os.path.join(OUT,'top_contributors.csv'), index=False)
df[['id', base_a_col, instr_a_col, 'delta_full']].to_csv(os.path.join(OUT,'top_deltas_full.csv'), index=False)

stats_summary = {
    "mean_diff": mean_diff,
    "n": int(n),
    "t_stat": float(tstat) if tstat is not None else None,
    "t_p": float(tp) if tp is not None else None,
    "bootstrap_ci": [float(lo), float(hi)] if lo is not None else [None,None]
}
with open(os.path.join(OUT,'final_report_summary.json'),'w',encoding='utf-8') as f:
    json.dump(stats_summary, f, indent=2, ensure_ascii=False)

top10 = top.head(10).copy().reset_index(drop=True)
overall_mean = mean_diff
top10['mean_contrib'] = top10['delta_full'] / len(df)
top10['pct_of_mean'] = top10['mean_contrib'] / overall_mean * 100 if overall_mean!=0 else np.nan
top10.to_csv(os.path.join(OUT,'top10_for_latex.csv'), index=False)

tex_lines = []
tex_lines.append("\\begin{table}[t]")
tex_lines.append("\\centering")
tex_lines.append("\\caption{Top 10 per-item contributors to mean difference (Instructed - Base).}")
tex_lines.append("\\label{tab:top10}")
tex_lines.append("\\begin{tabular}{lrrr}")
tex_lines.append("\\toprule")
tex_lines.append("ID & $\\Delta$ & Mean contrib & \\% of mean \\\\")
tex_lines.append("\\midrule")
for _, row in top10.iterrows():
    tex_lines.append(f"{row['id']} & {row['delta_full']:.6f} & {row['mean_contrib']:.6f} & {row['pct_of_mean']:.2f}\\% \\\\")
tex_lines.append("\\bottomrule")
tex_lines.append("\\end{tabular}")
tex_lines.append("\\end{table}")
with open(os.path.join(OUT,'top10_for_latex.tex'),'w',encoding='utf-8') as f:
    f.write("\n".join(tex_lines))

print("Wrote final report summary and top10 files to", OUT)
print(json.dumps(stats_summary, indent=2, ensure_ascii=False))