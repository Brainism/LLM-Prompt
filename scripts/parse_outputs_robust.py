# scripts/parse_outputs_robust.py
import re, json, csv, sys

def extract_balanced(raw, start_idx):
    if start_idx >= len(raw):
        return None, start_idx
    start_ch = raw[start_idx]
    if start_ch == '"':
        i = start_idx + 1
        while i < len(raw):
            if raw[i] == '"' and (i == 0 or raw[i-1] != '\\'):
                return raw[start_idx:i+1], i+1
            i += 1
        return None, i
    if start_ch == '{':
        depth = 0
        i = start_idx
        while i < len(raw):
            ch = raw[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return raw[start_idx:i+1], i+1
            elif ch == '"' :
                # skip over string
                j = i+1
                while j < len(raw):
                    if raw[j] == '"' and raw[j-1] != '\\':
                        break
                    j += 1
                i = j
            i += 1
        return None, i
    # bare token
    m = re.match(r'[^\s,}]+', raw[start_idx:])
    if m:
        return m.group(0), start_idx + len(m.group(0))
    return None, start_idx

def parse_line(line):
    try:
        obj = json.loads(line)
        return {
            'id': obj.get('id',''),
            'model': obj.get('model',''),
            'mode': obj.get('mode',''),
            'prompt': obj.get('prompt',''),
            'output': obj.get('output',''),
            'latency_ms': obj.get('latency_ms',''),
            'lang': obj.get('lang',''),
            'len_bin': obj.get('len_bin',''),
            'diff_bin': obj.get('diff_bin','')
        }
    except Exception:
        res = {'id':'','model':'','mode':'','prompt':'','output':'','latency_ms':'','lang':'','len_bin':'','diff_bin':''}
        m = re.search(r'"id"\s*:\s*"([^"]+)"', line)
        if m: res['id'] = m.group(1)
        m = re.search(r'"model"\s*:\s*"([^"]+)"', line)
        if m: res['model'] = m.group(1)
        m = re.search(r'"mode"\s*:\s*"([^"]+)"', line)
        if m: res['mode'] = m.group(1)
        m = re.search(r'"latency_ms"\s*:\s*([0-9]+)', line)
        if m: res['latency_ms'] = m.group(1)
        m = re.search(r'"lang"\s*:\s*"([^"]+)"', line)
        if m: res['lang'] = m.group(1)
        m = re.search(r'"len_bin"\s*:\s*"([^"]+)"', line)
        if m: res['len_bin'] = m.group(1)
        m = re.search(r'"diff_bin"\s*:\s*"([^"]+)"', line)
        if m: res['diff_bin'] = m.group(1)
        m = re.search(r'"output"\s*:\s*', line)
        if m:
            idx = m.end()
            while idx < len(line) and line[idx].isspace():
                idx += 1
            val, _ = extract_balanced(line, idx)
            if val is not None:
                # if it's a quoted string or object, keep raw text (we'll not try heavy unescaping)
                res['output'] = val
        return res

def main(inp, out):
    with open(inp, 'r', encoding='utf-8', errors='ignore') as fh, open(out, 'w', newline='', encoding='utf-8-sig') as outfh:
        writer = csv.DictWriter(outfh, fieldnames=['id','model','mode','prompt','output','latency_ms','lang','len_bin','diff_bin'])
        writer.writeheader()
        n = 0
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parsed = parse_line(line)
            if not parsed.get('id') and not parsed.get('output'):
                continue
            writer.writerow({k: parsed.get(k, '') for k in writer.fieldnames})
            n += 1
        print("Wrote {} rows to {}".format(n, out))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/parse_outputs_robust.py <input.jsonl> <out.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])