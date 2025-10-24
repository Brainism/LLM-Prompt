import os, sys, json, glob
import pandas as pd, numpy as np

ROOT = r"C:\Project\LLM"
AGG_PATH = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv")
OUT_AGG = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge_with_text.csv")
BACKUP = os.path.join(ROOT, "aggregated_metrics_fixed_with_chrf_rouge.csv.bak")

USE_EVAL = False; USE_ROUGESCORE = False
try:
    import evaluate
    chrf_m = evaluate.load("chrf")
    rouge_m = evaluate.load("rouge")
    USE_EVAL = True
except Exception as e:
    print("evaluate not available:", e)
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        USE_ROUGESCORE = True
    except Exception as e2:
        print("rouge_score not available:", e2)

def load_references():
    cand = [
        os.path.join(ROOT, "data","raw","references","references.jsonl"),
        os.path.join(ROOT, "LLM-clean","data","raw","references","references.jsonl"),
        os.path.join(ROOT, "scripts","data","raw","references","references.jsonl"),
        os.path.join(ROOT,"data","raw","references.jsonl"),
    ]
    for p in cand:
        if os.path.exists(p):
            print("Using references:", p)
            d = {}
            with open(p, "r", encoding="utf-8") as fh:
                for line in fh:
                    line=line.strip()
                    if not line: continue
                    try:
                        obj=json.loads(line)
                        idx = obj.get("id") or obj.get("example_id") or obj.get("item_id")
                        ref = obj.get("reference") or obj.get("ref") or obj.get("references")
                        if isinstance(ref, list):
                            ref = ref[0] if ref else ""
                        if idx and ref is not None:
                            d[str(idx)] = str(ref)
                    except Exception:
                        continue
            return d
    for p in glob.glob(os.path.join(ROOT,"**","*.csv"), recursive=True):
        try:
            hdr = open(p,encoding='utf-8').readline()
        except Exception:
            continue
        if "reference" in hdr.lower() or "ref" in hdr.lower():
            try:
                df=pd.read_csv(p, encoding="utf-8-sig", nrows=200)
                if 'id' in df.columns and ('reference' in df.columns or 'ref' in df.columns):
                    print("Using references from csv:", p)
                    d = {}
                    refcol = 'reference' if 'reference' in df.columns else 'ref'
                    for _,r in df.iterrows():
                        d[str(r['id'])] = str(r[refcol])
                    return d
            except Exception:
                continue
    print("No references file automatically found.")
    return {}

def load_outputs_map():
    candidates = glob.glob(os.path.join(ROOT, "results","raw","outputs_*.jsonl")) + \
                 glob.glob(os.path.join(ROOT,"**","outputs_*.jsonl"), recursive=True) + \
                 glob.glob(os.path.join(ROOT,"**","outputs_*.csv"), recursive=True)
    candidates = [c for c in candidates if ROOT.replace("\\","/") in c.replace("\\","/")]
    print("Found candidate outputs files:", candidates)
    instr_files = [c for c in candidates if "instruct" in c.lower() or "instr" in c.lower()]
    base_files = [c for c in candidates if ("general" in c.lower() or "base" in c.lower() or "gemma" in c.lower() or "A.csv" in c or "B.csv" in c)]
    return candidates, base_files, instr_files

def read_jsonl_map(path, pred_keys=("prediction","pred","output","response","generated","text")):
    m = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line=line.strip()
            if not line: continue
            try:
                obj=json.loads(line)
            except Exception:
                continue
            idx = obj.get("id") or obj.get("example_id") or obj.get("item_id")
            pred = None
            for k in pred_keys:
                if k in obj and obj[k] is not None:
                    pred = obj[k]; break
            if idx:
                m[str(idx)] = "" if pred is None else str(pred)
    return m

def read_csv_map(path, id_col_candidates=('id','item_id','example_id'), pred_candidates=('prediction','pred','output','response','generated','hyp','system','base_output','instructed_output')):
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(path, encoding='latin1')
    id_col = next((c for c in df.columns if c.lower() in id_col_candidates), None)
    pred_col = next((c for c in df.columns if c.lower() in pred_candidates), None)
    if id_col is None:
        for c in df.columns:
            if c.lower().endswith('id'):
                id_col=c; break
    if pred_col is None:
        for c in df.columns:
            if any(k in c.lower() for k in pred_candidates):
                pred_col=c; break
    m={}
    if id_col and pred_col:
        for _,r in df.iterrows():
            m[str(r[id_col])] = "" if pd.isna(r[pred_col]) else str(r[pred_col])
    return m

def build_per_item(ref_map, base_map, instr_map):
    ids = set(ref_map.keys()) | set(base_map.keys()) | set(instr_map.keys())
    rows=[]
    for i in sorted(ids):
        rows.append({
            "id": i,
            "ref": ref_map.get(i, ""),
            "base_pred": base_map.get(i, ""),
            "instr_pred": instr_map.get(i, "")
        })
    return pd.DataFrame(rows)

def compute_metrics_df(df_text):
    res=[]
    for _,r in df_text.iterrows():
        ref = r['ref'] if pd.notna(r['ref']) else ""
        base = r['base_pred'] if pd.notna(r['base_pred']) else ""
        instr = r['instr_pred'] if pd.notna(r['instr_pred']) else ""
        b_chrf = np.nan; i_chrf = np.nan; b_rouge = np.nan; i_rouge = np.nan
        try:
            if USE_EVAL:
                if ref.strip() or base.strip():
                    c = chrf_m.compute(predictions=[base], references=[[ref]])
                    b_chrf = float(c['score'])
                if ref.strip() or instr.strip():
                    c = chrf_m.compute(predictions=[instr], references=[[ref]])
                    i_chrf = float(c['score'])
                if ref.strip() or base.strip():
                    rres = rouge_m.compute(predictions=[base], references=[ref])
                    b_rouge = float(rres.get('rougeL', np.nan))
                if ref.strip() or instr.strip():
                    rres = rouge_m.compute(predictions=[instr], references=[ref])
                    i_rouge = float(rres.get('rougeL', np.nan))
            elif USE_ROUGESCORE:
                if ref.strip() or base.strip():
                    try:
                        pass
                    except:
                        pass
                if ref.strip() or base.strip():
                    sc = scorer.score(ref, base)
                    b_rouge = float(sc['rougeL'].fmeasure * 100.0)
                if ref.strip() or instr.strip():
                    sc = scorer.score(ref, instr)
                    i_rouge = float(sc['rougeL'].fmeasure * 100.0)
        except Exception as e:
            print("Metric compute error:", e)
        res.append({
            "id": r['id'],
            "chrf_base": b_chrf,
            "chrf_instr": i_chrf,
            "rougeL_base": b_rouge,
            "rougeL_instr": i_rouge
        })
    return pd.DataFrame(res)

def merge_into_agg(agg_path, metrics_df):
    if not os.path.exists(agg_path):
        print("Aggregated file not found:", agg_path); return False
    agg = pd.read_csv(agg_path, encoding='utf-8-sig')
    if not os.path.exists(BACKUP):
        agg.to_csv(BACKUP, index=False, encoding='utf-8-sig')
        print("Backup written to", BACKUP)
    long_rows = []
    for _,r in metrics_df.iterrows():
        long_rows.append({"id": r['id'], "mode": "base", "chrf": r['chrf_base'], "rouge_l": r['rougeL_base']})
        long_rows.append({"id": r['id'], "mode": "instr", "chrf": r['chrf_instr'], "rouge_l": r['rougeL_instr']})
    mdf = pd.DataFrame(long_rows)
    merged = agg.merge(mdf, on=['id','mode'], how='left', suffixes=('','_new'))
    for col in ['chrf','rouge_l']:
        newc = col + '_new'
        if newc in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].fillna(merged[newc])
            else:
                merged[col] = merged[newc]
            merged = merged.drop(columns=[newc])
    merged.to_csv(OUT_AGG, index=False, encoding='utf-8-sig')
    print("Saved merged aggregated file to", OUT_AGG)
    return True

def main():
    if not os.path.exists(AGG_PATH):
        print("Aggregated metrics CSV missing:", AGG_PATH); sys.exit(1)
    refs = load_references()
    candidates, base_files, instr_files = load_outputs_map()
    if not candidates:
        print("No candidate outputs files found. Please place system outputs under results/raw or results.")
        sys.exit(1)
    print("instr candidates:", instr_files)
    print("base candidates:", base_files)
    instr_path = instr_files[0] if instr_files else (candidates[0] if candidates else None)
    base_path = None
    for c in candidates:
        if c != instr_path and ('general' in c.lower() or 'base' in c.lower() or 'gemma' in c.lower() or 'A.csv' in c or 'B.csv' in c):
            base_path = c; break
    if base_path is None:
        for c in candidates:
            if 'a' in os.path.basename(c).lower() and 'instr' not in c.lower():
                base_path = c; break
    print("Chosen instr_path:", instr_path, " base_path:", base_path)
    base_map = {}
    instr_map = {}
    if base_path:
        if base_path.endswith(".jsonl"):
            base_map = read_jsonl_map(base_path)
        else:
            base_map = read_csv_map(base_path)
    if instr_path:
        if instr_path.endswith(".jsonl"):
            instr_map = read_jsonl_map(instr_path)
        else:
            instr_map = read_csv_map(instr_path)
    if not refs:
        cand_csv = os.path.join(ROOT,"data","candidates.csv")
        if not os.path.exists(cand_csv):
            cand_csv = os.path.join(ROOT,"LLM-clean","data","candidates.csv")
        if os.path.exists(cand_csv):
            try:
                dfc = pd.read_csv(cand_csv, encoding='utf-8-sig')
                if 'id' in dfc.columns and ('reference' in dfc.columns or 'ref' in dfc.columns):
                    rc = 'reference' if 'reference' in dfc.columns else 'ref'
                    refs = {str(r['id']): str(r[rc]) for _,r in dfc.iterrows()}
                    print("Loaded references from", cand_csv)
            except Exception as e:
                print("Failed to load candidates.csv:", e)
    if not refs:
        print("Warning: no reference texts found. chrF/ROUGE require references; results will be NaN.")
    per_df = build_per_item(refs, base_map, instr_map)
    print("Built per-item table rows:", len(per_df))
    per_out = os.path.join(ROOT,"per_item_text_pairs.csv")
    per_df.to_csv(per_out, index=False, encoding='utf-8-sig')
    print("Wrote per-item text pairs to", per_out)
    metrics_df = compute_metrics_df(per_df)
    print("Computed metrics rows:", len(metrics_df))
    ok = merge_into_agg(AGG_PATH, metrics_df)
    if not ok:
        print("Merge failed.")
    else:
        print("Done. Please re-run scripts\\build_chrf_rouge.py and scripts\\build_paper_assets.py to regenerate figures.")

if __name__ == "__main__":
    main()