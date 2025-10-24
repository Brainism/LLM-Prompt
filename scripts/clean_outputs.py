import sys, json, re, pathlib, codecs

def decode_unicode_escapes(s):
    if not isinstance(s, str):
        s = str(s)
    if '\\u' in s or '\\x' in s or '\\n' in s:
        try:
            return codecs.decode(s, 'unicode_escape')
        except Exception:
            return s
    return s

def extract_text(raw):
    if raw is None:
        return ""
    s = str(raw)
    s = decode_unicode_escapes(s)
    m = re.search(r'[\uAC00-\uD7A3][\s\S]*[\uAC00-\uD7A3]', s)
    if m:
        out = m.group(0)
    else:
        out = re.sub(r'[\{\}\[\]<>\\\/]', '', s)
    out = out.strip(' \t\n\r"\' :;')
    out = re.sub(r'\s{2,}', ' ', out)
    out = out.replace('이 용', '이용').replace('결연감', '결속감')
    return out

def main(inp, outp):
    inp = pathlib.Path(inp)
    outp = pathlib.Path(outp)
    if not inp.exists():
        print(f"Input not found: {inp}")
        sys.exit(2)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with inp.open('r', encoding='utf-8') as inf, outp.open('w', encoding='utf-8', newline='') as outf:
        outf.write('id,clean_output\n')
        for line in inf:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                try:
                    obj = json.loads(line.rstrip(',\n\r '))
                except Exception:
                    continue
            pid = obj.get('id') or obj.get('item_id') or ''
            raw = obj.get('output') or obj.get('response') or ''
            cleaned = extract_text(raw)
            cleaned_esc = '"' + cleaned.replace('"', '""') + '"'
            outf.write(f'{pid},{cleaned_esc}\n')
    print("[OK] cleaned ->", outp)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python scripts/clean_outputs.py <input.jsonl> <output.csv>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])