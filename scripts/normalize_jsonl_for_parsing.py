import sys

def extract_json_objects_stream(f):
    buf = []
    depth = 0
    in_string = False
    escape = False

    while True:
        chunk = f.read(4096)
        if not chunk:
            break
        for ch in chunk:
            buf.append(ch)
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\\\':
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        s = ''.join(buf).strip()
                        first = s.find('{')
                        last = s.rfind('}')
                        if first != -1 and last != -1 and last >= first:
                            yield s[first:last+1]
                        buf = []

    rem = ''.join(buf).strip()
    if rem:
        # attempt to extract { ... } blocks in rem
        i = 0
        n = len(rem)
        while i < n:
            if rem[i] == '{':
                depth = 0
                j = i
                in_string = False
                escape = False
                while j < n:
                    ch = rem[j]
                    if in_string:
                        if escape:
                            escape = False
                        elif ch == '\\\\':
                            escape = True
                        elif ch == '"':
                            in_string = False
                    else:
                        if ch == '"':
                            in_string = True
                        elif ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                yield rem[i:j+1]
                                i = j+1
                                break
                    j += 1
                else:
                    break
            else:
                i += 1

def main(inp, outp):
    n = 0
    with open(inp, 'r', encoding='utf-8', errors='replace') as fh, \
         open(outp, 'w', encoding='utf-8') as ofh:
        for obj in extract_json_objects_stream(fh):
            # write each object as a single line
            line = obj.replace('\\r','').replace('\\n','\\n')
            ofh.write(line + "\\n")
            n += 1
    print(f"Wrote {n} JSON objects to {outp}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/normalize_jsonl_for_parsing.py <input.jsonl> <output_clean.jsonl>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])