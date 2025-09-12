import csv, sys, os
from collections import Counter

IN = "per_item_text_pairs.csv"
OUT_ITEMS = "per_item_text_pairs_with_metrics.csv"
OUT_AGG = "aggregated_metrics_fixed_with_chrf_rouge_with_text.csv"

if not os.path.exists(IN):
    print("Missing input:", IN)
    sys.exit(1)

def char_ngrams(s, n):
    s = s or ""
    return [s[i:i+n] for i in range(len(s)-n+1)] if len(s) >= n else []

def chrf_score(ref, hyp, max_n=6, beta=2.0):
    if (ref is None or ref == "") and (hyp is None or hyp == ""):
        return 100.0
    if ref is None: ref = ""
    if hyp is None: hyp = ""
    precisions = []
    recalls = []
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
        precisions.append(p)
        recalls.append(r)
    if not precisions:
        return 0.0
    avg_p = sum(precisions)/len(precisions)
    avg_r = sum(recalls)/len(recalls)
    if avg_p + avg_r == 0:
        return 0.0
    beta2 = beta*beta
    f = (1+beta2) * (avg_p*avg_r) / (beta2*avg_p + avg_r)
    return f*100.0

def lcs_len(a, b):
    if a is None: a = ""
    if b is None: b = ""
    A = a.split()
    B = b.split()
    la = len(A); lb = len(B)
    if la == 0 or lb == 0:
        return 0
    dp = [[0]*(lb+1) for _ in range(la+1)]
    for i in range(1, la+1):
        ai = A[i-1]
        for j in range(1, lb+1):
            if ai == B[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = dp[i-1][j] if dp[i-1][j] >= dp[i][j-1] else dp[i][j-1]
    return dp[la][lb]

def rouge_l_score(ref, hyp, beta=1.0):
    if (ref is None or ref=="") and (hyp is None or hyp==""):
        return 100.0
    if ref is None: ref = ""
    if hyp is None: hyp = ""
    lcs = lcs_len(ref, hyp)
    ref_tokens = len(ref.split())
    hyp_tokens = len(hyp.split())
    if ref_tokens == 0 or hyp_tokens == 0 or lcs == 0:
        return 0.0
    p = lcs / hyp_tokens
    r = lcs / ref_tokens
    beta2 = beta*beta
    if p + r == 0:
        return 0.0
    f = (1+beta2) * p * r / (r + beta2 * p)
    return f*100.0

items = []
with open(IN, newline='', encoding='utf-8-sig') as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        idv = row.get('id','')
        ref = row.get('reference','') or ""
        pred = row.get('prediction','') or ""
        ref = ref.strip()
        pred = pred.strip()
        chrf = chrf_score(ref, pred, max_n=6, beta=2.0)
        rouge_l = rouge_l_score(ref, pred, beta=1.0)
        items.append({'id': idv, 'reference': ref, 'prediction': pred, 'chrf': f"{chrf:.3f}", 'rouge_l': f"{rouge_l:.3f}"})

with open(OUT_ITEMS, 'w', newline='', encoding='utf-8-sig') as fh:
    fieldnames = ['id','reference','prediction','chrf','rouge_l']
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    for r in items:
        writer.writerow(r)

import statistics
chrf_vals = [float(x['chrf']) for x in items if x['prediction'].strip()!='']
rouge_vals = [float(x['rouge_l']) for x in items if x['prediction'].strip()!='']
n = len(items)
summary_rows = [
    {'metric':'n_items','value': n},
    {'metric':'chrf_mean','value': f"{statistics.mean(chrf_vals):.3f}" if chrf_vals else "NA"},
    {'metric':'chrf_median','value': f"{statistics.median(chrf_vals):.3f}" if chrf_vals else "NA"},
    {'metric':'rouge_l_mean','value': f"{statistics.mean(rouge_vals):.3f}" if rouge_vals else "NA"},
    {'metric':'rouge_l_median','value': f"{statistics.median(rouge_vals):.3f}" if rouge_vals else "NA"},
]
with open(OUT_AGG, 'w', newline='', encoding='utf-8-sig') as fh:
    writer = csv.DictWriter(fh, fieldnames=['metric','value'])
    writer.writeheader()
    for r in summary_rows:
        writer.writerow(r)

print("Wrote:", OUT_ITEMS, "and", OUT_AGG)