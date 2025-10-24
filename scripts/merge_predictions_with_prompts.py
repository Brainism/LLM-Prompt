import sys, json, csv

def load_predictions(jsonl_path):
    d = {}
    with open(jsonl_path, 'r', encoding='utf-8') as fh:
        for ln in fh:
            if not ln.strip(): continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            rid = obj.get('id','')
            pred = obj.get('prediction')
            text = ''
            if isinstance(pred, dict):
                text = pred.get('text','')
            elif isinstance(pred, str):
                try:
                    p = json.loads(pred)
                    text = p.get('text','') if isinstance(p, dict) else str(p)
                except Exception:
                    text = pred
            d[rid] = text
    return d

def main(pred_jsonl, prompts_csv, out_csv):
    preds = load_predictions(pred_jsonl)
    with open(prompts_csv, 'r', encoding='utf-8') as inf, \
         open(out_csv, 'w', encoding='utf-8-sig', newline='') as outf:
        reader = csv.DictReader(inf)
        fieldnames = ['id','input','reference','prediction_text']
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            rid = row.get('id','')
            inp = row.get('input','')
            ref = row.get('reference','')
            pred_text = preds.get(rid, '')
            writer.writerow({'id':rid,'input':inp,'reference':ref,'prediction_text':pred_text})
    print(f"Wrote merged CSV to {out_csv}")

if __name__ == '__main__':
    if len(sys.argv)!=4:
        print("Usage: python scripts/merge_predictions_with_prompts.py <pred.normalized.jsonl> <prompts.csv> <out.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])