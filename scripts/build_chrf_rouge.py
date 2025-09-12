import os, sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = r"C:\Project\LLM"
SRC = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
OUT = os.path.join(ROOT, "docs", "paper", "figs")
os.makedirs(OUT, exist_ok=True)

def safe_read(p):
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(p, encoding="latin1")

if not os.path.exists(SRC):
    print("ERROR: source not found:", SRC); sys.exit(1)
df = safe_read(SRC)
print("Loaded", SRC, "rows=", len(df))
if "base" in df.columns and "instr" in df.columns:
    base_chrf = df.loc[df['mode']==df['mode'].unique()[0], 'chrf'].mean() if 'chrf' in df.columns else np.nan
    instr_chrf = df.loc[df['mode']==df['mode'].unique()[-1], 'chrf'].mean() if 'chrf' in df.columns else np.nan
    base_r = df.loc[df['mode']==df['mode'].unique()[0], 'rouge_l'].mean() if 'rouge_l' in df.columns else np.nan
    instr_r = df.loc[df['mode']==df['mode'].unique()[-1], 'rouge_l'].mean() if 'rouge_l' in df.columns else np.nan
else:
    if 'mode' not in df.columns:
        print("ERROR: no 'mode' column found for pivot"); sys.exit(1)
    def pivot_metric(m):
        if m not in df.columns:
            return None
        piv = df.groupby(['id','mode'], dropna=False)[m].mean().reset_index().pivot(index='id', columns='mode', values=m)
        return piv
    chrf_piv = pivot_metric('chrf')
    rouge_piv = pivot_metric('rouge_l')
    modes = None
    if chrf_piv is not None:
        modes = [c for c in chrf_piv.columns]
    elif rouge_piv is not None:
        modes = [c for c in rouge_piv.columns]
    if not modes or len(modes) < 2:
        uniq = list(df['mode'].unique())
        if len(uniq) < 2:
            print("ERROR: not enough modes to compare:", uniq); sys.exit(1)
        modes = uniq[:2]
    low = [m.lower() for m in modes]
    instr_keywords = ['instr','instruct']
    base_idx = 0
    instr_idx = 1
    for i,m in enumerate(low):
        if any(k in m for k in instr_keywords):
            instr_idx = i
            base_idx = 1-i
            break
    m_base, m_instr = modes[base_idx], modes[instr_idx]
    print("Mapping modes:", m_base, "-> base,", m_instr, "-> instr")
    if chrf_piv is not None:
        base_chrf = chrf_piv[m_base].mean()
        instr_chrf = chrf_piv[m_instr].mean()
    else:
        base_chrf = instr_chrf = np.nan
    if rouge_piv is not None:
        base_r = rouge_piv[m_base].mean()
        instr_r = rouge_piv[m_instr].mean()
    else:
        base_r = instr_r = np.nan

if not np.isnan(base_chrf) or not np.isnan(instr_chrf):
    plt.figure(figsize=(6,4))
    plt.bar(['Base','Instructed'], [base_chrf, instr_chrf])
    plt.ylabel('chrF (mean)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'chrf_mean_bar_300dpi.png'), dpi=300)
    print("Saved chrf_mean_bar_300dpi.png")
else:
    print("chrF not available")

if not np.isnan(base_r) or not np.isnan(instr_r):
    plt.figure(figsize=(6,4))
    plt.bar(['Base','Instructed'], [base_r, instr_r])
    plt.ylabel('ROUGE-L (mean)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'rouge_mean_bar_300dpi.png'), dpi=300)
    print("Saved rouge_mean_bar_300dpi.png")
else:
    print("ROUGE-L not available")