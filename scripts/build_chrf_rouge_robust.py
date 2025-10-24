import os, sys, math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = r"C:\Project\LLM"
SRC = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
OUT = os.path.join(ROOT, "docs", "paper", "figs")
os.makedirs(OUT, exist_ok=True)

def safe_read(path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(path, encoding="latin1")

if not os.path.exists(SRC):
    print("ERROR: missing", SRC); sys.exit(1)

df = safe_read(SRC)
print("Loaded", SRC, "rows=", len(df))
print("Columns:", df.columns.tolist())

for col in ["chrf","rouge_l","rougeL"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "base" in df.columns and "instr" in df.columns:
    chrf_available = "chrf" in df.columns and df["chrf"].notna().any()
    rouge_available = "rouge_l" in df.columns and df["rouge_l"].notna().any()
    print("Wide-mode detected. chrf_available:", chrf_available, "rouge_available:", rouge_available)
    if chrf_available:
        base_chrf = df.loc[:, "chrf"].mean()
        instr_chrf = base_chrf
    if rouge_available:
        base_r = df.loc[:, "rouge_l"].mean()
        instr_r = base_r
else:
    if "mode" not in df.columns:
        print("ERROR: no 'mode' column and no 'base'/'instr' columns. Cannot pivot."); sys.exit(1)
    def pivot_metric(m):
        if m not in df.columns:
            return None
        piv = df.groupby(['id','mode'], dropna=False)[m].mean().reset_index().pivot(index='id', columns='mode', values=m)
        return piv

    chrf_piv = pivot_metric('chrf')
    rouge_piv = pivot_metric('rouge_l')

    modes = None
    if chrf_piv is not None:
        modes = list(chrf_piv.columns)
    elif rouge_piv is not None:
        modes = list(rouge_piv.columns)
    else:
        modes = list(df['mode'].unique())[:2] if 'mode' in df.columns else []

    print("Detected modes (for mapping):", modes)
    if len(modes) < 2:
        print("Not enough modes detected to compare. modes:", modes)
    instr_keywords = ['instr','instruct']
    base_idx = 0; instr_idx = 1 if len(modes)>1 else 0
    for i,m in enumerate(modes):
        low = m.lower()
        if any(k in low for k in instr_keywords):
            instr_idx = i
            base_idx = 1-i
            break
    m_base = modes[base_idx] if modes else None
    m_instr = modes[instr_idx] if modes else None
    print("Mapping:", m_base, "-> base,", m_instr, "-> instr")

    def safe_mean_from_piv(piv, col):
        if piv is None or col not in piv.columns:
            return np.nan
        s = pd.to_numeric(piv[col], errors='coerce')
        if s.dropna().empty:
            return np.nan
        return float(s.mean())

    base_chrf = safe_mean_from_piv(chrf_piv, m_base) if chrf_piv is not None else np.nan
    instr_chrf = safe_mean_from_piv(chrf_piv, m_instr) if chrf_piv is not None else np.nan
    base_r = safe_mean_from_piv(rouge_piv, m_base) if rouge_piv is not None else np.nan
    instr_r = safe_mean_from_piv(rouge_piv, m_instr) if rouge_piv is not None else np.nan

print("chrF means -> base:", base_chrf, " instr:", instr_chrf)
print("ROUGE-L means -> base:", base_r, " instr:", instr_r)

summary = {
    'metric':['chrF','ROUGE-L'],
    'base_mean':[None if math.isnan(base_chrf) else base_chrf, None if math.isnan(base_r) else base_r],
    'instr_mean':[None if math.isnan(instr_chrf) else instr_chrf, None if math.isnan(instr_r) else instr_r]
}
summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(OUT, 'chrF_rouge_summary.csv'), index=False, encoding='utf-8-sig')

if not (math.isnan(base_chrf) and math.isnan(instr_chrf)):
    plt.figure(figsize=(6,4))
    plt.bar(['Base','Instructed'], [0 if math.isnan(base_chrf) else base_chrf, 0 if math.isnan(instr_chrf) else instr_chrf])
    plt.ylabel('chrF (mean)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'chrf_mean_bar_300dpi.png'), dpi=300)
    print("Saved chrf_mean_bar_300dpi.png")
else:
    print("chrF unavailable: skipped plotting")

if not (math.isnan(base_r) and math.isnan(instr_r)):
    plt.figure(figsize=(6,4))
    plt.bar(['Base','Instructed'], [0 if math.isnan(base_r) else base_r, 0 if math.isnan(instr_r) else instr_r])
    plt.ylabel('ROUGE-L (mean)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'rouge_mean_bar_300dpi.png'), dpi=300)
    print("Saved rouge_mean_bar_300dpi.png")
else:
    print("ROUGE-L unavailable: skipped plotting")