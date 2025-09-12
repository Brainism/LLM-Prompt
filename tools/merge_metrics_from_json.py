import json, pandas as pd, os
from pathlib import Path

per_item = Path(r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv")
chrf_json = Path(r"C:\Project\LLM\LLM-clean\results\quantitative\chrf.json")
rouge_json = Path(r"C:\Project\LLM\LLM-clean\results\quantitative\rouge.json")
out = Path(r"C:\Project\LLM\figs\aggregated_metrics_fixed_with_chrf_rouge.csv")

df = pd.read_csv(per_item, dtype=str)
df['base'] = pd.to_numeric(df['base'], errors='coerce')
df['instr'] = pd.to_numeric(df['instr'], errors='coerce')

def load_score_json(p):
    if not p.exists(): 
        return {}
    with open(p, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    out = {}
    if isinstance(data, list):
        for rec in data:
            if 'id' in rec and 'score' in rec:
                out[rec['id']] = rec['score']
            elif len(rec)==1:
                k = list(rec.keys())[0]; out[k] = rec[k]
    elif isinstance(data, dict):
        for k,v in data.items():
            if isinstance(v, (int,float)):
                out[k] = v
            elif isinstance(v, dict) and 'score' in v:
                out[k] = v['score']
    return out

chrf_map = load_score_json(chrf_json)
rouge_map = load_score_json(rouge_json)

rows=[]
for _,r in df.iterrows():
    idd=str(r['id'])
    rows.append({'id':idd,'mode':'base','bleu':r['base'],
                 'chrf':chrf_map.get(idd, None),'rouge_l':rouge_map.get(idd,None)})
    rows.append({'id':idd,'mode':'instr','bleu':r['instr'],
                 'chrf':chrf_map.get(idd, None),'rouge_l':rouge_map.get(idd,None)})
outdf = pd.DataFrame(rows)
outdf.to_csv(out, index=False)
print("Wrote", out)