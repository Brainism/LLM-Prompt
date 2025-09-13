import pandas as pd
import json
import sys

inp = sys.argv[1]
out = sys.argv[2]

df = pd.read_csv(inp, dtype=str).fillna('')
with open(out, 'w', encoding='utf-8') as fh:
    for _, row in df.iterrows():
        rid = row['id']
        pred = row['prediction']
        if not pred:
            obj = {"id": rid, "prediction": None}
        else:
            try:
                parsed = json.loads(pred)
            except Exception:
                parsed = {"raw": pred}
            obj = {"id": rid, "prediction": parsed}
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
print("Wrote", out)