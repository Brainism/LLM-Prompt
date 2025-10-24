import csv, json, ast, re
from pathlib import Path

def try_parse_json(s):
    if not s or str(s).strip()=="":
        return ""
    s0 = s.strip()
    try:
        return json.dumps(json.loads(s0), ensure_ascii=False, indent=2)
    except Exception:
        pass
    s1 = s0.replace('“','"').replace('”','"').replace("‘","'").replace("’","'")
    try:
        v = ast.literal_eval(s1)
        return json.dumps(v, ensure_ascii=False, indent=2)
    except Exception:
        pass
    m = re.search(r'(\{.*\}|\[.*\])', s1, flags=re.S)
    if m:
        j = m.group(1)
        try:
            return json.dumps(json.loads(j), ensure_ascii=False, indent=2)
        except Exception:
            try:
                v = ast.literal_eval(j)
                return json.dumps(v, ensure_ascii=False, indent=2)
            except Exception:
                return j.strip()
    s_clean = s1.strip().replace('\n',' \\n ')
    if len(s_clean) > 500:
        return s_clean[:500] + ' ...'
    return s_clean

def main():
    inp = Path('per_item_instruct_pairs.csv')
    out = Path('per_item_instruct_pairs_pretty.csv')
    if not inp.exists():
        print('Missing', inp)
        return
    rows = []
    with inp.open(encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for rec in r:
            pred = rec.get('prediction','')
            pretty = try_parse_json(pred)
            rows.append({'id': rec.get('id',''), 'prediction_raw': pred, 'prediction_pretty': pretty})
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id','prediction_raw','prediction_pretty'])
        w.writeheader()
        for rr in rows:
            w.writerow(rr)
    print('Wrote', out, 'rows=', len(rows))

if __name__ == '__main__':
    main()
