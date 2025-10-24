import os, json, glob, csv
OUT = r"per_item_text_pairs.csv"
paths = glob.glob(os.path.join("results","raw","outputs_*.jsonl")) + glob.glob(os.path.join("results","raw","*.jsonl"))

pairs = {}
for p in paths:
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip(): continue
                try:
                    j = json.loads(line)
                except:
                    continue
                key = None
                for k in ("id","example_id","example","idx","index"):
                    if k in j:
                        key = j[k]; break
                pred = None
                for pc in ('prediction','pred','output','response','generated','text','system','hyp','prediction_text'):
                    if pc in j and j[pc] not in (None,''):
                        pred = j[pc]; break
                ref = None
                for rc in ('reference','ref','references','target','gold'):
                    if rc in j and j[rc] not in (None,'','[]'):
                        ref = j[rc] if not isinstance(j[rc], list) else (j[rc][0] if j[rc] else "")
                        break
                if key is None:
                    key = "row_"+str(len(pairs)+1)
                if key not in pairs:
                    pairs[key] = {"id": key, "prediction": pred or "", "reference": ref or ""}
                else:
                    if pred:
                        pairs[key]["prediction"] = pred
                    if ref:
                        pairs[key]["reference"] = ref
    except Exception as e:
        print("Error reading", p, e)

import pandas as pd
if os.path.exists(OUT):
    base_df = pd.read_csv(OUT, encoding="utf-8-sig")
    base = {str(r['id']): r for r in base_df.to_dict(orient='records')}
    for k,v in pairs.items():
        if k in base:
            if not base[k].get('prediction') and v.get('prediction'):
                base[k]['prediction'] = v['prediction']
            if not base[k].get('reference') and v.get('reference'):
                base[k]['reference'] = v['reference']
        else:
            base[k] = v
    out_rows = list(base.values())
else:
    out_rows = list(pairs.values())

import csv
with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
    writer = csv.DictWriter(fh, fieldnames=["id","reference","prediction"])
    writer.writeheader()
    for r in out_rows:
        writer.writerow(r)

print("Wrote", OUT, "rows=", len(out_rows))