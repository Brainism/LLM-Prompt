import json, sys

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
        strs = [str(x) for x in pred if isinstance(x,(str,int,float))]
        return " ".join(strs) if strs else json.dumps(pred, ensure_ascii=False)
    return str(pred)

def main(inp_jsonl, out_jsonl):
    n=0
    with open(inp_jsonl, 'r', encoding='utf-8') as inf, open(out_jsonl, 'w', encoding='utf-8') as outf:
        for line in inf:
            line=line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            pred = obj.get('prediction', obj.get('output', None))
            text = extract_text(pred)
            obj['prediction'] = {"text": text}
            outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n+=1
    print(f"Wrote {n} lines to {out_jsonl}")

if __name__ == '__main__':
    if len(sys.argv)!=3:
        print("Usage: python scripts/normalize_prediction_to_text_jsonl.py <in.jsonl> <out.jsonl>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])