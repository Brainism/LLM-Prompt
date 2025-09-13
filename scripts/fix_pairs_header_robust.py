import csv, sys, re, json

ID_PATTERN = re.compile(r'(EX-\d{4,6})', re.IGNORECASE)

def find_key_by_candidates(keys, candidates):
    for c in candidates:
        for k in keys:
            if k is None:
                continue
            if k.strip().lower() == c:
                return k
    return None

def find_key_by_contains(keys, substrs):
    for k in keys:
        if k is None:
            continue
        kl = k.strip().lower()
        for s in substrs:
            if s in kl:
                return k
    return None

def extract_id_from_row(row):
    for v in row.values():
        if not v:
            continue
        if isinstance(v, bytes):
            try:
                v = v.decode('utf-8', errors='ignore')
            except:
                v = str(v)
        s = str(v)
        m = ID_PATTERN.search(s)
        if m:
            return m.group(1)
    return None

def normalize_prediction(raw):
    if raw is None:
        return ''
    s = str(raw).strip()
    if s in ['', '{}', '{ }', '""', "''"]:
        return ''
    try:
        parsed = json.loads(s)
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    m = re.search(r'(\{[\s\S]*\})', s)
    if m:
        candidate = m.group(1)
        try:
            parsed = json.loads(candidate)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            cand = candidate.replace('\r\n','\n').strip()
            return cand
    s = s.replace('{"";}', '').replace('{""; }', '')
    s = s.replace('{/}', '').replace('/}', '').replace('{/}','')
    s = re.sub(r'\s+\n\s+', '\n', s)
    s = re.sub(r'\s{2,}', ' ', s)
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s

def main(inp, outp, outprob):
    pairs = []
    problems = []
    with open(inp, 'r', encoding='utf-8', errors='replace', newline='') as fh:
        reader = csv.DictReader(fh)
        header_keys = reader.fieldnames or []
        id_key = find_key_by_candidates(header_keys, ['id'])
        if id_key is None:
            id_key = find_key_by_contains(header_keys, ['id', 'identifier'])
        out_key = find_key_by_contains(header_keys, ['out', 'pred', 'output'])
        if out_key is None:
            out_key = find_key_by_candidates(header_keys, ['output','prediction'])
        for i, row in enumerate(reader):
            id_val = ''
            if id_key and row.get(id_key) not in (None, ''):
                id_val = str(row.get(id_key)).strip()
            else:
                for k in header_keys:
                    if k and k.strip().lower() == 'id':
                        id_val = str(row.get(k,'' )).strip()
                        break
            if not id_val:
                id_val = extract_id_from_row(row) or ''
            raw_out = ''
            if out_key and row.get(out_key) not in (None, ''):
                raw_out = row.get(out_key)
            else:
                for k in header_keys:
                    if k and ('out' in k.lower() or 'pred' in k.lower()):
                        raw_out = row.get(k,'')
                        break
                if not raw_out:
                    cand = ''
                    for v in row.values():
                        if v and len(str(v)) > len(str(cand)):
                            cand = v
                    raw_out = cand
            norm = normalize_prediction(raw_out)
            pairs.append((id_val, norm))
            if id_val == '' or norm == '':
                problems.append((id_val, raw_out, norm, i+2))
    with open(outp, 'w', encoding='utf-8-sig', newline='') as ofh:
        w = csv.writer(ofh)
        w.writerow(['id','prediction'])
        for idv, pred in pairs:
            w.writerow([idv, pred])
    with open(outprob, 'w', encoding='utf-8-sig', newline='') as pf:
        pw = csv.writer(pf)
        pw.writerow(['id','raw_output','normalized_prediction','row_number'])
        for p in problems:
            pw.writerow(p)
    print(f"Wrote {len(pairs)} rows to {outp}")
    print(f"Wrote {len(problems)} problematic rows to {outprob}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python scripts\\fix_pairs_header_robust.py <input_parsed.csv> <out_pairs.csv> <out_problematic.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])