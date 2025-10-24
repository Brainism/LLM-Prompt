import json, csv, os, sys, glob

in_path = sys.argv[1] if len(sys.argv) > 1 else "results/raw/outputs_gemma_instruct.jsonl"
out_csv = sys.argv[2] if len(sys.argv) > 2 else "per_item_instruct_pairs.csv"
mode_tag = sys.argv[3] if len(sys.argv) > 3 else "instr"

def detect_fields(d):
    id_fields = ['id','example_id','example','idx','index']
    pred_fields = ['prediction','pred','output','response','generated','text','system','hyp','prediction_text','answer']
    idf = None; pdf = None
    for f in id_fields:
        if f in d:
            idf = f; break
    for f in pred_fields:
        if f in d:
            pdf = f; break
    if pdf is None:
        for k,v in d.items():
            if isinstance(v,str) and len(v) > 0:
                pdf = k; break
    return idf, pdf

rows = []
if not os.path.exists(in_path):
    print("Missing", in_path); sys.exit(1)

with open(in_path,'r',encoding='utf-8',errors='replace') as fh:
    first = True
    id_field = None; pred_field = None
    for line in fh:
        line=line.strip()
        if not line: continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        if first:
            id_field, pred_field = detect_fields(j)
            first = False
        key = j.get(id_field) if id_field in j else j.get('id') if 'id' in j else None
        if key is None:
            for k in ('meta','example','item'):
                if k in j and isinstance(j[k], dict) and 'id' in j[k]:
                    key = j[k]['id']; break
        pred = None
        if pred_field and pred_field in j:
            pred = j[pred_field]
        else:
            for k in ('response','output','text'):
                if k in j and isinstance(j[k], str):
                    pred = j[k]; break
            if pred is None:
                for k,v in j.items():
                    if isinstance(v,str) and len(v)>0:
                        pred=v; break
        if key is None:
            key = f"row_{len(rows)+1}"
        rows.append({'id': str(key), 'prediction': pred if pred is not None else ""})

with open(out_csv,'w',newline='',encoding='utf-8-sig') as fh:
    writer = csv.DictWriter(fh, fieldnames=['id','prediction'])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
print("Wrote", out_csv, "rows=", len(rows))