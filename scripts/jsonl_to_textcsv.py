import json, csv, sys

def extract_text(pred):
    if pred is None:
        return ''
    if isinstance(pred, str):
        try:
            p = json.loads(pred)
            return extract_text(p)
        except Exception:
            return pred
    if isinstance(pred, dict):
        if 'text' in pred and isinstance(pred['text'], str):
            return pred['text']
        if 'raw' in pred and isinstance(pred['raw'], str):
            return pred['raw']
        if 'title' in pred and isinstance(pred['title'], str):
            return pred['title']
        for k,v in pred.items():
            if isinstance(v, str) and v.strip():
                return v
        try:
            return json.dumps(pred, ensure_ascii=False)
        except Exception:
            return str(pred)
    if isinstance(pred, list):
        strs = [str(x) for x in pred if isinstance(x, (str,int,float))]
        return " ".join(strs) if strs else json.dumps(pred, ensure_ascii=False)
    return str(pred)

def main(inp_jsonl, out_csv):
    out_rows = 0
    with open(inp_jsonl, 'r', encoding='utf-8') as inf, \
         open(out_csv, 'w', encoding='utf-8-sig', newline='') as outf:
        writer = csv.writer(outf)
        writer.writerow(['id','text'])
        for line in inf:
            line=line.strip()
            if not line: 
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            rid = obj.get('id','')
            pred = obj.get('prediction', obj.get('output', None))
            text = extract_text(pred)
            writer.writerow([rid, text])
            out_rows += 1
    print(f"Wrote {out_rows} rows to {out_csv}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python scripts/jsonl_to_textcsv.py <in.jsonl> <out.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
