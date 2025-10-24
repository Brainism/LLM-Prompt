import csv, json, sys, re

def try_json_load(s):
    if s is None:
        return None
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r'(\{(?:.|\s)*\})', s)
    if m:
        inner = m.group(1)
        try:
            return json.loads(inner)
        except Exception:
            pass
    try:
        cand = s.encode('utf-8').decode('unicode_escape')
        return json.loads(cand)
    except Exception:
        pass
    return None

def normalize_prediction(raw):
    if raw is None:
        return ''
    r = raw.strip()
    if r in ['', '{}', '{ }', '""', "''"]:
        return ''
    parsed = try_json_load(r)
    if parsed is not None:
        try:
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return str(parsed)
        
    if (r.startswith('"') and r.endswith('"')) or (r.startswith("'") and r.endswith("'")):
        r = r[1:-1]
    r = r.replace('\\n', '\n').replace('\r\n', '\n').strip()
    r = re.sub(r'\s+\n\s+', '\n', r)
    return r

def main(inp, outp, out_prob=None):
    problematic = []
    pairs = []
    with open(inp, 'r', encoding='utf-8', errors='replace') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            id_ = row.get('id','').strip()
            raw = row.get('output','')
            pred = normalize_prediction(raw)
            pairs.append((id_, pred))
            if pred == '' or len(pred) < 3:
                problematic.append((id_, raw, pred))
    with open(outp, 'w', encoding='utf-8-sig', newline='') as ofh:
        w = csv.writer(ofh)
        w.writerow(['id','prediction'])
        for id_,pred in pairs:
            w.writerow([id_, pred])
    print(f"Wrote {len(pairs)} rows to {outp}")
    if out_prob:
        with open(out_prob, 'w', encoding='utf-8-sig', newline='') as pf:
            pw = csv.writer(pf)
            pw.writerow(['id','raw_output','normalized_prediction'])
            for t in problematic:
                pw.writerow(t)
        print(f"Wrote {len(problematic)} problematic rows to {out_prob}")
    else:
        print(f"Problematic rows (count): {len(problematic)}")
    return

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python scripts\\parsed_to_pairs.py <input_parsed.csv> <out_pairs.csv> [<out_problematic.csv>]")
        sys.exit(1)
    inp = sys.argv[1]
    outp = sys.argv[2]
    outp_prob = sys.argv[3] if len(sys.argv) >= 4 else None
    main(inp, outp, outp_prob)