import sys, re, json, csv
import pandas as pd

def extract_balanced(raw, start_idx):
    if start_idx >= len(raw):
        return None, start_idx
    ch = raw[start_idx]
    if ch == '"':
        i = start_idx+1
        res = []
        while i < len(raw):
            if raw[i] == '\\':
                if i+1 < len(raw):
                    res.append(raw[i:i+2]); i += 2; continue
            if raw[i] == '"':
                return '"' + ''.join(res) + '"', i+1
            res.append(raw[i]); i += 1
        return None, i
    if ch == '{':
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
                        j += 2; continue
                    if raw[j] == '"':
                        break
                    j += 1
                i = j
            i += 1
        return None, i
    if ch == '[':
        depth = 0
        i = start_idx
        while i < len(raw):
            c = raw[i]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    return raw[start_idx:i+1], i+1
            elif c == '"':
                j = i+1
                while j < len(raw):
                    if raw[j] == '\\':
                        j += 2; continue
                    if raw[j] == '"':
                        break
                    j += 1
                i = j
            i += 1
        return None, i
    m = re.match(r'[^,\s}]+', raw[start_idx:])
    if m:
        return m.group(0), start_idx + len(m.group(0))
    return None, start_idx

def try_load_json(s):
    if not isinstance(s, str):
        return None
    s0 = s.strip()
    if not s0:
        return None
    try:
        return json.loads(s0)
    except Exception:
        pass
    s1 = s0.replace('“','"').replace('”','"').replace('`','"').replace('’',"'").replace('“','"')
    s1 = s1.replace('\r\n','\n')
    s1 = re.sub(r'</?[^>]+>', '', s1)
    s1 = s1.replace('""","', '","').replace('""', '"')
    try:
        return json.loads(s1)
    except Exception:
        pass
    for i,ch in enumerate(s1):
        if ch in '{[':
            sub, _ = extract_balanced(s1, i)
            if sub:
                try:
                    return json.loads(sub)
                except Exception:
                    sub2 = re.sub(r'(\}|\])\s*[:=]\s*-?\d+(\.\d+)?\s*$', r'\1', sub)
                    try:
                        return json.loads(sub2)
                    except Exception:
                        if sub2 and sub2[0] == '{' and sub2[-1] != '}':
                            try:
                                return json.loads(sub2 + '}')
                            except Exception:
                                pass
    m = re.match(r'^\s*\{(.+?)\}[:\s]*-?\d+(\.\d+)?\s*$', s1, flags=re.S)
    if m:
        candidate = '{' + m.group(1) + '}'
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return None

def repair_row_prediction(raw_pred):
    if raw_pred is None:
        return None, 'empty', 'empty input'
    s = str(raw_pred)
    s_strip = s.strip()
    if not s_strip:
        return None, 'empty', 'empty input'
    if re.fullmatch(r'[A-Z]{2}-\d{4}|[A-Z]{2}-\d{3,4}', s_strip):
        return None, 'echo_id', 'cell contains id only (no output)'
    parsed = try_load_json(s)
    if parsed is not None:
        return json.dumps(parsed, ensure_ascii=False), 'ok', ''
    if '다음 주제' in s or '다음 영어 문장' in s or '한 문장으로' in s or s_strip.startswith('You are') or s_strip.startswith('You'):
        return None, 'prompt_instead', 'cell contains prompt text, not model output'
    wrapped = json.dumps({"raw": s_strip}, ensure_ascii=False)
    return wrapped, 'wrapped', 'wrapped raw text into {"raw":...}'

def main(inp, out_repaired, out_master=None):
    df = pd.read_csv(inp, dtype=str).fillna('')
    results = []
    updated = df.copy()
    n_ok = n_repaired = n_wrapped = n_problem = 0
    for i, row in df.iterrows():
        idv = row.get('id','')
        pred = row.get('prediction','')
        repaired, status, note = repair_row_prediction(pred)
        results.append({
            'id': idv,
            'original_prediction': pred,
            'repaired_prediction': repaired if repaired is not None else '',
            'status': status,
            'note': note
        })
        if status == 'ok':
            n_ok += 1
            updated.at[i, 'prediction'] = repaired
        elif status == 'wrapped':
            n_wrapped += 1
            updated.at[i, 'prediction'] = repaired
        elif status == 'echo_id' or status == 'prompt_instead' or status == 'empty':
            n_problem += 1
        else:
            if repaired:
                updated.at[i, 'prediction'] = repaired
                n_repaired += 1

    out_df = pd.DataFrame(results)
    out_df.to_csv(out_repaired, index=False, encoding='utf-8-sig')
    print(f"Wrote repaired report: {out_repaired}")
    print(f"counts: ok={n_ok}, wrapped={n_wrapped}, repaired={n_repaired}, problems={n_problem}")

    if out_master:
        updated.to_csv(out_master, index=False, encoding='utf-8-sig')
        print(f"Wrote master-updated CSV: {out_master}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python scripts/repair_predictions_robust.py <input_pairs.csv> <out_repaired.csv> [<out_master_updated.csv>]")
        sys.exit(1)
    inp = sys.argv[1]
    out_repaired = sys.argv[2]
    out_master = sys.argv[3] if len(sys.argv) > 3 else None
    main(inp, out_repaired, out_master)