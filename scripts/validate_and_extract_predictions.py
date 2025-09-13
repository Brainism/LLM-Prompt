import sys, json, csv
import pandas as pd

def try_json(s):
    try:
        return json.loads(s)
    except Exception:
        try:
            return json.loads(s.replace("“",'"').replace("”",'"'))
        except Exception:
            return None

if len(sys.argv) < 2:
    print("Usage: python scripts/validate_and_extract_predictions.py <pairs.csv>")
    sys.exit(1)

fn = sys.argv[1]
df = pd.read_csv(fn, dtype=str).fillna('')
out_bad = []
out_rows = []
for idx,row in df.iterrows():
    idv = row['id']
    pred = row.get('prediction','')
    parsed = try_json(pred)
    if parsed is None:
        out_bad.append((idv, pred[:200].replace("\n"," ")))
    else:
        title = parsed.get('title') if isinstance(parsed, dict) else None
        tags = parsed.get('tags') if isinstance(parsed, dict) else None
        out_rows.append((idv, bool(title), bool(tags)))
print(f"Total rows {len(df)}  valid-json {len(out_rows)}  invalid-json {len(out_bad)}")
if out_bad:
    print("\nInvalid JSON samples (id,truncated_prediction):")
    for k,v in out_bad[:30]:
        print(k, "|", v)
else:
    print("All predictions parse as JSON (or no invalids).")