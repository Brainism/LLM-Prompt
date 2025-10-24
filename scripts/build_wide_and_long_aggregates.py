import pandas as pd, os, sys, csv, statistics

BASE_PAIRS = "per_item_text_pairs.csv"
INSTR_PAIRS = "per_item_instruct_pairs.csv"
OUT_WIDE = "per_item_pairs_wide.csv"
OUT_BASE_MET = "per_item_pairs_base_with_metrics.csv"
OUT_INSTR_MET = "per_item_pairs_instr_with_metrics.csv"
OUT_AGG_WIDE = "aggregated_metrics_fixed_with_chrf_rouge.csv"
OUT_AGG_LONG = "aggregated_metrics_by_mode.csv"

from collections import Counter
def char_ngrams(s, n):
    s = s or ""
    return [s[i:i+n] for i in range(len(s)-n+1)] if len(s) >= n else []
def chrf_score(ref, hyp, max_n=6, beta=2.0):
    if (ref is None or ref == ""):
        return None
    if hyp is None: hyp = ""
    precisions = []; recalls = []
    for n in range(1, max_n+1):
        ref_ngrams = Counter(char_ngrams(ref, n))
        hyp_ngrams = Counter(char_ngrams(hyp, n))
        if not ref_ngrams and not hyp_ngrams:
            continue
        overlap = sum((ref_ngrams & hyp_ngrams).values())
        hyp_count = sum(hyp_ngrams.values())
        ref_count = sum(ref_ngrams.values())
        p = overlap / hyp_count if hyp_count > 0 else 0.0
        r = overlap / ref_count if ref_count > 0 else 0.0
        precisions.append(p); recalls.append(r)
    if not precisions:
        return 0.0
    avg_p = sum(precisions)/len(precisions)
    avg_r = sum(recalls)/len(recalls)
    if avg_p + avg_r == 0:
        return 0.0
    beta2 = beta*beta
    f = (1+beta2) * (avg_p*avg_r) / (beta2*avg_p + avg_r)
    return f*100.0

def lcs_len(a,b):
    if a is None: a = ""
    if b is None: b = ""
    A = a.split(); B = b.split()
    la, lb = len(A), len(B)
    if la==0 or lb==0:
        return 0
    dp = [[0]*(lb+1) for _ in range(la+1)]
    for i in range(1, la+1):
        for j in range(1, lb+1):
            if A[i-1]==B[j-1]:
                dp[i][j] = dp[i-1][j-1]+1
            else:
                dp[i][j] = dp[i-1][j] if dp[i-1][j]>=dp[i][j-1] else dp[i][j-1]
    return dp[la][lb]

def rouge_l_score(ref, hyp):
    if ref is None or ref=="":
        return None
    if hyp is None: hyp = ""
    lcs = lcs_len(ref,hyp)
    ref_tokens = len(ref.split()); hyp_tokens = len(hyp.split())
    if ref_tokens==0 or hyp_tokens==0 or lcs==0:
        return 0.0
    p = lcs / hyp_tokens; r = lcs / ref_tokens
    if p + r == 0:
        return 0.0
    f = 2 * p * r / (p + r)
    return f*100.0

if not os.path.exists(BASE_PAIRS):
    print("Missing", BASE_PAIRS); sys.exit(1)
base_df = pd.read_csv(BASE_PAIRS, encoding="utf-8-sig")
if 'id' not in base_df.columns:
    base_df = base_df.reset_index().rename(columns={'index':'id'})

if not os.path.exists(INSTR_PAIRS):
    print("Warning: instr pairs not found:", INSTR_PAIRS)
    instr_df = pd.DataFrame(columns=['id','prediction'])
else:
    instr_df = pd.read_csv(INSTR_PAIRS, encoding="utf-8-sig")
    if 'id' not in instr_df.columns:
        instr_df = instr_df.reset_index().rename(columns={'index':'id'})

base_df = base_df.rename(columns={c:c.strip() for c in base_df.columns})
if 'reference' not in base_df.columns:
    base_df['reference'] = ''

if 'prediction' not in base_df.columns:
    base_df['prediction'] = ''
base_df = base_df[['id','reference','prediction']]

base_df = base_df.rename(columns={'prediction':'base_prediction'})

instr_df = instr_df.rename(columns={'prediction':'instr_prediction'})
merged = base_df.merge(instr_df[['id','instr_prediction']], on='id', how='left')

merged.to_csv(OUT_WIDE,index=False,encoding='utf-8-sig')
print("Wrote wide pairs:", OUT_WIDE, "rows=", len(merged))

base_rows=[]; instr_rows=[]
for _, r in merged.iterrows():
    idv = r['id']
    ref = (r['reference'] if pd.notna(r['reference']) else "").strip()
    bp_raw = r['base_prediction'] if 'base_prediction' in r else ""
    ip_raw = r['instr_prediction'] if 'instr_prediction' in r else ""
    base_pred = "" if pd.isna(bp_raw) else str(bp_raw).strip()
    instr_pred = "" if pd.isna(ip_raw) else str(ip_raw).strip()

    if ref:
        base_chrf = chrf_score(ref, base_pred) if base_pred else None
        base_rouge = rouge_l_score(ref, base_pred) if base_pred else None
        base_rows.append({'id':idv,'mode':'base','reference':ref,'prediction':base_pred,
                          'chrf': base_chrf if base_chrf is not None else "NA",
                          'rouge_l': base_rouge if base_rouge is not None else "NA"})
        instr_chrf = chrf_score(ref, instr_pred) if instr_pred else None
        instr_rouge = rouge_l_score(ref, instr_pred) if instr_pred else None
        instr_rows.append({'id':idv,'mode':'instr','reference':ref,'prediction':instr_pred,
                          'chrf': instr_chrf if instr_chrf is not None else "NA",
                          'rouge_l': instr_rouge if instr_rouge is not None else "NA"})
    else:
        pass

pd.DataFrame(base_rows).to_csv(OUT_BASE_MET,index=False,encoding='utf-8-sig')
pd.DataFrame(instr_rows).to_csv(OUT_INSTR_MET,index=False,encoding='utf-8-sig')
print("Wrote per-mode item metrics:", OUT_BASE_MET, OUT_INSTR_MET)

def safe_mean(values):
    vals = [v for v in values if isinstance(v,(int,float))]
    return statistics.mean(vals) if vals else None

base_chrf_vals = [r['chrf'] for r in base_rows if isinstance(r['chrf'], (int,float))]
base_rouge_vals = [r['rouge_l'] for r in base_rows if isinstance(r['rouge_l'], (int,float))]
instr_chrf_vals = [r['chrf'] for r in instr_rows if isinstance(r['chrf'], (int,float))]
instr_rouge_vals = [r['rouge_l'] for r in instr_rows if isinstance(r['rouge_l'], (int,float))]

agg_wide = {
    'metric': ['n_items','base_chrf_mean','base_rouge_mean','instr_chrf_mean','instr_rouge_mean'],
    'value' : [ len(base_rows),
                f"{statistics.mean(base_chrf_vals):.3f}" if base_chrf_vals else "NA",
                f"{statistics.mean(base_rouge_vals):.3f}" if base_rouge_vals else "NA",
                f"{statistics.mean(instr_chrf_vals):.3f}" if instr_chrf_vals else "NA",
                f"{statistics.mean(instr_rouge_vals):.3f}" if instr_rouge_vals else "NA"]
}
dfw = pd.DataFrame(agg_wide)
dfw.to_csv(OUT_AGG_WIDE,index=False,encoding='utf-8-sig')
print("Wrote aggregated wide summary:", OUT_AGG_WIDE)

long_rows = []
if base_chrf_vals:
    long_rows.append({'mode':'base','n_items':len(base_rows),'chrf_mean':f"{statistics.mean(base_chrf_vals):.3f}", 'rouge_l_mean': f"{statistics.mean(base_rouge_vals):.3f}" if base_rouge_vals else "NA"})
else:
    long_rows.append({'mode':'base','n_items':len(base_rows),'chrf_mean':"NA",'rouge_l_mean':"NA"})
if instr_chrf_vals:
    long_rows.append({'mode':'instr','n_items':len(instr_rows),'chrf_mean':f"{statistics.mean(instr_chrf_vals):.3f}", 'rouge_l_mean': f"{statistics.mean(instr_rouge_vals):.3f}" if instr_rouge_vals else "NA"})
else:
    long_rows.append({'mode':'instr','n_items':len(instr_rows),'chrf_mean':"NA",'rouge_l_mean':"NA"})

pd.DataFrame(long_rows).to_csv(OUT_AGG_LONG,index=False,encoding='utf-8-sig')
print("Wrote aggregated long summary:", OUT_AGG_LONG)