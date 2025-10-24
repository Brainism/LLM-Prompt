import sys, json, re
import pandas as pd

def extract_balanced(raw, start_idx):
    if start_idx >= len(raw):
        return None, start_idx
    ch = raw[start_idx]
    if ch != '{':
        i = raw.find('{', start_idx)
        if i == -1:
            return None, start_idx
        start_idx = i
    depth = 0
    i = start_idx
    while i < len(raw):
        c = raw[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return raw[start_idx:i+1], i+1
        elif c == '"':
            j = i+1
            while j < len(raw):
                if raw[j] == '\\':
                    j += 2
                    continue
                if raw[j] == '"':
                    break
                j += 1
            i = j
        i += 1
    return None, i

def find_first_json(raw):
    if not isinstance(raw, str):
        return None
    idx = 0
    while True:
        pos = raw.find('{', idx)
        if pos == -1:
            return None
        cand, nxt = extract_balanced(raw, pos)
        if cand:
            try:
                return json.loads(cand)
            except Exception:
                s = cand
                s2 = s.replace('""', '"').replace("“", '"').replace("”", '"')
                try:
                    return json.loads(s2)
                except Exception:
                    s3 = re.sub(r'[\x00-\x1f]', '', s2)
                    try:
                        return json.loads(s3)
                    except Exception:
                        idx = pos + 1
                        continue
        else:
            break
    return None

def is_json(s):
    try:
        json.loads(s)
        return True
    except:
        return False

def main(infile, outfile, *target_ids):
    df = pd.read_csv(infile, dtype=str).fillna('')
    changed = 0
    wrapped = 0
    failed = []
    targets = set(target_ids) if target_ids else None
    for i, row in df.iterrows():
        rid = str(row.get('id','')).strip()
        if targets and rid not in targets:
            continue
        pred = row.get('prediction','')
        if pred is None:
            pred = ''
        pred = str(pred)
        if pred.strip() == '':
            failed.append((rid,'empty'))
            continue
        if is_json(pred):
            continue
        j = find_first_json(pred)
        if j is not None:
            df.at[i,'prediction'] = json.dumps(j, ensure_ascii=False)
            changed += 1
            continue
        df.at[i,'prediction'] = json.dumps({"text": pred.strip()}, ensure_ascii=False)
        wrapped += 1

    df.to_csv(outfile, index=False, encoding='utf-8-sig')
    print(f"Wrote {outfile}; changed_json={changed}, wrapped_raw_to_json={wrapped}, failed_count={len(failed)}")
    if failed:
        print("Failed samples (id,reason):")
        for f in failed:
            print(f)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python scripts\\extract_json_from_prediction.py <in.csv> <out.csv> [id1 id2 ...]")
        sys.exit(1)
    infile = sys.argv[1]; outfile = sys.argv[2]
    ids = sys.argv[3:]
    main(infile, outfile, *ids)