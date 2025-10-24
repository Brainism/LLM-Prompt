import json, argparse, os, pandas as pd

def try_load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read().strip()
        try:
            obj = json.loads(txt)
            return obj
        except Exception:
            arr = []
            for line in txt.splitlines():
                line=line.strip()
                if not line: continue
                try:
                    arr.append(json.loads(line))
                except:
                    pass
            return arr

def normalize_list(obj):
    if obj is None: return []
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list):
        return obj
    return []

def extract_pairs(list_obj, id_field_candidates=None, value_field_candidates=None):
    rows = []
    id_candidates = id_field_candidates or ['id','example_id','input_id']
    for it in list_obj:
        if not isinstance(it, dict): continue
        idv = None
        for k in id_candidates:
            if k in it:
                idv = it[k]; break
        val = None
        if value_field_candidates:
            for k in value_field_candidates:
                if k in it:
                    val = it[k]; break
        else:
            for k,v in it.items():
                if k in id_candidates: continue
                if isinstance(v,(int,float)):
                    val=v; break
        rows.append({'id': idv, 'raw': it, 'value': val})
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--chrf', default='LLM-clean\\results\\quantitative\\chrf.json')
    p.add_argument('--rouge', default='LLM-clean\\results\\quantitative\\rouge.json')
    p.add_argument('--bleu', default='LLM-clean\\results\\quantitative\\bleu_sacre.json')
    p.add_argument('--per_item', default='LLM-clean\\results\\quantitative\\per_item_subset_50.jsonl')
    p.add_argument('--manifest', default='data\\manifest\\split_manifest_main.json')
    p.add_argument('--out_with', default='figs\\aggregated_metrics_fixed_with_chrf_rouge.csv')
    p.add_argument('--out_agg', default='figs\\aggregated_metrics_fixed.csv')
    p.add_argument('--top10', default='figs\\top10_delta_full.csv')
    p.add_argument('--compliance_json', default='LLM-clean\\results\\quantitative\\compliance_summary.json')
    p.add_argument('--compliance_csv', default='figs\\compliance_by_scenario.csv')
    p.add_argument('--model', default='Gemma-7B')
    p.add_argument('--modes', default='instruct,general')
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.out_with), exist_ok=True)

    chrf_raw = try_load_json(args.chrf) if os.path.exists(args.chrf) else []
    rouge_raw = try_load_json(args.rouge) if os.path.exists(args.rouge) else []
    bleu_raw = try_load_json(args.bleu) if os.path.exists(args.bleu) else []
    per_item_raw = try_load_json(args.per_item) if os.path.exists(args.per_item) else []

    chrf_list = normalize_list(chrf_raw)
    rouge_list = normalize_list(rouge_raw)
    bleu_list = normalize_list(bleu_raw)
    per_item_list = normalize_list(per_item_raw)

    def map_to_list(obj):
        if isinstance(obj, dict) and not any(isinstance(v, (list,dict)) for v in obj.values()):
            out=[]
            for k,v in obj.items():
                out.append({'id':k, 'value':v})
            return out
        return obj

    chrf_list = map_to_list(chrf_list)
    rouge_list = map_to_list(rouge_list)
    bleu_list = map_to_list(bleu_list)

    def list_to_df(lst, prefer_fields=None):
        rows=[]
        for it in lst:
            if not isinstance(it, dict):
                continue
            idv = it.get('id') or it.get('example_id') or it.get('input_id') or it.get('ex_id') or it.get('idx')
            val = None
            if 'chrF' in it: val=it.get('chrF')
            elif 'chrf' in it: val=it.get('chrf')
            elif 'chrF_score' in it: val=it.get('chrF_score')
            else:
                for k,v in it.items():
                    if k in ('id','example_id','input_id'): continue
                    if isinstance(v,(int,float)):
                        val=v; break
            rows.append({'id':idv, **it, '_value': val})
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    df_chrf = list_to_df(chrf_list)
    df_rouge = list_to_df(rouge_list)
    df_bleu = list_to_df(bleu_list)
    df_peritem = list_to_df(per_item_list)

    if '_value' in df_chrf.columns:
        df_chrf = df_chrf[['id','_value']].rename(columns={'_value':'chrf'})
    if '_value' in df_rouge.columns:
        df_rouge = df_rouge[['id','_value']].rename(columns={'_value':'rougeL'})
    else:
        if 'rougeL_f1' in df_rouge.columns:
            df_rouge = df_rouge[['id','rougeL_f1']].rename(columns={'rougeL_f1':'rougeL'})

    if '_value' in df_bleu.columns:
        df_bleu = df_bleu[['id','_value']].rename(columns={'_value':'bleu'})
    elif 'BLEU' in df_bleu.columns and 'id' in df_bleu.columns:
        df_bleu = df_bleu[['id','BLEU']].rename(columns={'BLEU':'bleu'})

    dfs = [df_chrf.set_index('id') if not df_chrf.empty else None,
           df_rouge.set_index('id') if not df_rouge.empty else None,
           df_bleu.set_index('id') if not df_bleu.empty else None]

    merged = None
    for d in dfs:
        if d is None: continue
        if merged is None:
            merged = d.copy()
        else:
            merged = merged.join(d, how='outer')
    if merged is None:
        merged = pd.DataFrame()

    if not df_peritem.empty:
        for col in ['base','instr','delta','score']:
            if col in df_peritem.columns:
                merged = merged.join(df_peritem.set_index('id')[[col]], how='outer')

    merged = merged.reset_index().rename(columns={'index':'id'})
    models = [m.strip() for m in args.model.split(',') if m.strip()]
    modes = [m.strip() for m in args.modes.split(',') if m.strip()]
    per_item_out = args.out_with
    merged.to_csv(per_item_out, index=False, encoding='utf-8-sig')
    print("Saved per-item merged ->", per_item_out)

    agg_rows=[]
    import numpy as np
    metric_cols = [c for c in merged.columns if c not in ('id')]
    for model in models or ['Gemma-7B']:
        for mode in modes or ['instruct','general']:
            row = {'model': model, 'mode': mode}
            for mc in metric_cols:
                try:
                    row[mc] = float(merged[mc].dropna().astype(float).mean())
                except Exception:
                    row[mc] = None
            agg_rows.append(row)
    df_agg = pd.DataFrame(agg_rows)
    df_agg.to_csv(args.out_agg, index=False, encoding='utf-8-sig')
    print("Saved aggregated ->", args.out_agg)

    if 'base' in merged.columns and 'instr' in merged.columns:
        merged['delta'] = merged['instr'] - merged['base']
        top10 = merged.sort_values(by='delta', ascending=False).head(10)
        top10.to_csv(args.top10, index=False, encoding='utf-8-sig')
        print("Saved top10 delta ->", args.top10)
    else:
        print("No base/instr columns found; skipping top10 generation.")

    if os.path.exists(args.compliance_json):
        comp = try_load_json(args.compliance_json)
        if isinstance(comp, dict) and 'summary' in comp:
            rows = comp['summary']
        elif isinstance(comp, list):
            rows = comp
        else:
            rows = []
        if rows:
            pd.DataFrame(rows).to_csv(args.compliance_csv, index=False, encoding='utf-8-sig')
            print("Saved compliance csv ->", args.compliance_csv)
        else:
            print("compliance JSON found but couldn't parse structured rows.")
    else:
        print("No compliance JSON at", args.compliance_json)

if __name__ == '__main__':
    main()