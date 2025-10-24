import re, json, csv, sys

def try_load_json(s):
    try:
        return json.loads(s)
    except Exception as e:
        return None

def split_by_newline_id(text):
    parts = re.split(r'\n(?=\s*\{\s*\"id\"\s*:)', text)
    return parts

def split_by_id_marker(text):
    matches = list(re.finditer(r'(?=\{\s*\"id\"\s*:)', text))
    parts = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        parts.append(text[start:end])
    return parts

def salvage_object(chunk):
    # try direct load
    obj = try_load_json(chunk)
    if obj is not None:
        return obj
    first = chunk.find('{')
    last = chunk.rfind('}')
    if first != -1 and last != -1 and last > first:
        candidate = chunk[first:last+1]
        obj = try_load_json(candidate)
        if obj is not None:
            return obj
    candidate2 = chunk.replace('\\n', '\n')
    obj = try_load_json(candidate2)
    if obj is not None:
        return obj
    # last resort: try to extract id field and output manually
    m = re.search(r'\"id\"\s*:\s*\"([^\"]+)\"', chunk)
    if m:
        return {'id': m.group(1), 'raw': chunk}
    return None

def parse_text(text):
    parts = split_by_newline_id(text)
    objs = []
    # try parse parts; if most fail, fallback to split_by_id_marker
    success = 0
    for p in parts:
        o = salvage_object(p)
        if o is not None:
            objs.append(o)
            success += 1
    if success < max(1, len(parts)//2):
        # try alternative splitting
        parts2 = split_by_id_marker(text)
        objs = []
        for p in parts2:
            o = salvage_object(p)
            if o is not None:
                objs.append(o)
    return objs

def to_row(obj):
    # normalize fields we expect
    return {
        'id': obj.get('id',''),
        'model': obj.get('model',''),
        'mode': obj.get('mode',''),
        'prompt': obj.get('prompt',''),
        'output': obj.get('output','') if not isinstance(obj.get('output',''), (dict,list)) else json.dumps(obj.get('output',''), ensure_ascii=False),
        'latency_ms': obj.get('latency_ms',''),
        'lang': obj.get('lang',''),
        'len_bin': obj.get('len_bin',''),
        'diff_bin': obj.get('diff_bin','')
    }

def main(inp, outp):
    with open(inp, 'r', encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    objs = parse_text(text)
    # Write CSV
    with open(outp, 'w', newline='', encoding='utf-8-sig') as ofh:
        writer = csv.DictWriter(ofh, fieldnames=['id','model','mode','prompt','output','latency_ms','lang','len_bin','diff_bin'])
        writer.writeheader()
        n = 0
        for o in objs:
            row = to_row(o) if isinstance(o, dict) else {'id': str(o)}
            writer.writerow(row)
            n += 1
    print(f"Parsed {n} objects -> {outp}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/parse_by_id_boundaries.py <input_raw.jsonl> <output_parsed.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])