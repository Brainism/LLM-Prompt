import sys, re, os

def find_balanced_from(s, start_pos):
    depth = 0
    i = start_pos
    if s[i] != '{':
        return None, i
    while i < len(s):
        ch = s[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return s[start_pos:i+1], i+1
        elif ch == '"':
            j = i+1
            while j < len(s):
                if s[j] == '\\\\':
                    j += 2
                    continue
                if s[j] == '"':
                    break
                j += 1
            i = j
        i += 1
    return None, i

def extract_objects_for_id(path, target_id):
    results = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        data = fh.read()
    pattern = re.compile(r'\"id\"\s*:\s*\"' + re.escape(target_id) + r'\"')
    for m in pattern.finditer(data):
        start = data.rfind('{', 0, m.start())
        if start == -1:
            continue
        obj, endpos = find_balanced_from(data, start)
        if obj:
            results.append(obj)
    return results

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts\\extract_raw_by_id.py <input.jsonl> id1 id2 ...")
        sys.exit(1)
    path = sys.argv[1]
    ids = sys.argv[2:]
    for tid in ids:
        objs = extract_objects_for_id(path, tid)
        if not objs:
            print(f"{tid}: NOT FOUND in {path}")
            continue
        for idx, o in enumerate(objs, start=1):
            fn = f"{os.path.splitext(os.path.basename(path))[0]}_{tid}_{idx}.raw.json"
            outpath = os.path.join(os.path.dirname(path), fn)
            with open(outpath, 'w', encoding='utf-8') as of:
                of.write(o)
            print(f"WROTE {outpath} (length {len(o)})")
        print(f"{tid}: found {len(objs)} object(s)")

if __name__ == '__main__':
    main()