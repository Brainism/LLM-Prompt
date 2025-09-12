import os, sys, glob, json
import pandas as pd
import numpy as np

ROOT = r"C:\Project\LLM"
AGG = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
OUT = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge_with_text.csv")
BACKUP = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv.bak")

USE_EVALUATE = False
USE_ROUGE_SCORE = False
try:
    import evaluate
    chrf_metric = evaluate.load("chrf")
    rouge_metric = evaluate.load("rouge")
    USE_EVALUATE = True
except Exception as e:
    print("evaluate not available or failed to load:", e)
    try:
        from rouge_score import rouge_scorer
        rouge_scorer_impl = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        USE_ROUGE_SCORE = True
    except Exception as e2:
        print("rouge_score not available:", e2)

def find_candidate_files(root):
    pats = [
        os.path.join(root, "per_item_*.csv"),
        os.path.join(root, "*.per_item*.csv"),
        os.path.join(root, "per_item*.csv"),
        os.path.join(root, "per_item_*.jsonl"),
        os.path.join(root, "per_item_*.tsv"),
    ]
    files = []
    for p in pats:
        files.extend(glob.glob(p))
    files = sorted(set(files))
    return files

def detect_text_columns(df):
    cols = [c.lower() for c in df.columns]
    ref_candidates = ['ref','reference','references','target','gold','refs','reference_text','refs_text']
    hyp_candidates = ['hyp','prediction','pred','output','candidate','system','response','answer','gen']
    id_candidates = ['id','item_id','example_id','ex_id']
    mode_candidates = ['mode','condition']

    ref_col = next((c for c in df.columns if c.lower() in ref_candidates), None)
    hyp_col = next((c for c in df.columns if c.lower() in hyp_candidates), None)
    id_col = next((c for c in df.columns if c.lower() in id_candidates), None)
    mode_col = next((c for c in df.columns if c.lower() in mode_candidates), None)

    if ref_col is None:
        for c in df.columns:
            if 'ref' in c.lower() or 'gold' in c.lower() or 'target' in c.lower():
                ref_col = c; break
    if hyp_col is None:
        for c in df.columns:
            if any(k in c.lower() for k in ['pred','hyp','out','gen','system','response','answer']):
                hyp_col = c; break
    if id_col is None:
        for c in df.columns:
            if 'id' == c.lower() or c.lower().endswith('id'):
                id_col = c; break

    return id_col, mode_col, ref_col, hyp_col

def load_per_item_rows(files):
    rows = []
    for f in files:
        try:
            if f.lower().endswith('.jsonl'):
                with open(f,'r',encoding='utf-8') as fh:
                    for line in fh:
                        try:
                            obj = json.loads(line)
                            rows.append((f,obj))
                        except:
                            continue
                continue
            df = pd.read_csv(f, encoding='utf-8-sig')
        except Exception:
            try:
                df = pd.read_csv(f, encoding='latin1')
            except Exception as e:
                print("Failed to read", f, e); continue
        id_col, mode_col, ref_col, hyp_col = detect_text_columns(df)
        if ref_col is None or hyp_col is None:
            print("Skipping", f, " — could not detect ref/hyp columns. columns:", df.columns.tolist())
            continue
        for _, r in df.iterrows():
            entry = {
                'src_file': os.path.basename(f),
                'id': r[id_col] if id_col and id_col in df.columns else None,
                'mode': r[mode_col] if mode_col and mode_col in df.columns else None,
                'ref': r[ref_col],
                'hyp': r[hyp_col]
            }
            rows.append(entry)
    return pd.DataFrame(rows)

def safe_text(x):
    if pd.isna(x):
        return ""
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            return ""
        return str(x[0])
    return str(x)

def compute_metrics(df_text):
    out_rows = []
    for i, row in df_text.iterrows():
        ref = safe_text(row['ref'])
        hyp = safe_text(row['hyp'])
        if ref == "" and hyp == "":
            chrf = np.nan; rougeL = np.nan
        else:
            chrf = np.nan; rougeL = np.nan
            if USE_EVALUATE:
                try:
                    chrf_res = chrf_metric.compute(predictions=[hyp], references=[[ref]])
                    chrf = float(chrf_res['score'])
                except Exception as e:
                    chrf = np.nan
                try:
                    rouge_res = rouge_metric.compute(predictions=[hyp], references=[ref])
                    rougeL = float(rouge_res.get('rougeL', np.nan))
                except Exception:
                    rougeL = np.nan
            if (not USE_EVALUATE or np.isnan(rougeL)) and USE_ROUGE_SCORE:
                try:
                    sc = rouge_scorer_impl.score(ref, hyp)
                    rougeL = float(sc['rougeL'].fmeasure * 100.0)
                except Exception:
                    pass
        out_rows.append({
            'id': row.get('id'),
            'mode': row.get('mode'),
            'chrf': chrf,
            'rouge_l': rougeL
        })
    return pd.DataFrame(out_rows)

def merge_into_aggregated(agg_path, computed_df):
    if not os.path.exists(agg_path):
        print("Aggregated file not found:", agg_path); return False
    agg = pd.read_csv(agg_path, encoding='utf-8-sig')
    if not os.path.exists(BACKUP):
        try:
            agg.to_csv(BACKUP, index=False, encoding='utf-8-sig')
            print("Backup written to", BACKUP)
        except Exception as e:
            print("Backup failed:", e)
    if 'mode' in agg.columns:
        merged = agg.merge(computed_df, on=['id','mode'], how='left', suffixes=('','_new'))
    else:
        merged = agg.merge(computed_df, on=['id'], how='left', suffixes=('','_new'))
    for col in ['chrf','rouge_l']:
        newcol = col + '_new'
        if newcol in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].fillna(merged[newcol])
            else:
                merged[col] = merged[newcol]
            merged = merged.drop(columns=[newcol])
    merged.to_csv(OUT, index=False, encoding='utf-8-sig')
    print("Saved merged file to", OUT)
    return True

def main():
    if not os.path.exists(AGG):
        print("Aggregated CSV not found:", AGG); sys.exit(1)
    cand_files = find_candidate_files(ROOT)
    print("Candidate per-item files:", cand_files)
    df_text = load_per_item_rows(cand_files)
    if df_text.empty:
        print("No per-item rows loaded. Cannot compute chrF/ROUGE.")
        print("Please ensure per-item CSVs with ref/hyp columns (e.g., per_item_*.csv) are in", ROOT)
        sys.exit(0)
    print("Loaded per-item text rows:", len(df_text))
    computed = compute_metrics(df_text)
    print("Computed metrics rows:", len(computed))
    if 'mode' in computed.columns:
        computed = computed.drop_duplicates(subset=['id','mode'])
    else:
        computed = computed.drop_duplicates(subset=['id'])
    ok = merge_into_aggregated(AGG, computed)
    if not ok:
        print("Merge failed.")
    else:
        print("Done. Please re-run scripts/build_chrf_rouge.py to regenerate mean-bar plots.")

if __name__ == "__main__":
    main()