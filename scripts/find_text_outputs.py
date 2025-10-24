import os, json, csv, glob

ROOT = r"C:\Project\LLM"

def check_csv(path):
    try:
        with open(path, encoding='utf-8-sig') as fh:
            rdr = csv.DictReader(fh)
            has_ref=False; has_pred=False
            sample_ref=None; sample_pred=None
            total_rows=0; nonempty_ref=0; nonempty_pred=0
            for i,row in enumerate(rdr):
                total_rows += 1
                for rc in ['reference','ref','references','target','gold']:
                    if rc in row and row[rc] not in (None,'','[]'):
                        nonempty_ref += 1
                        if sample_ref is None: sample_ref = row[rc]
                        break
                for pc in ['prediction','pred','output','response','generated','text','system','hyp','base_output','instructed_output']:
                    if pc in row and row[pc] not in (None,''):
                        nonempty_pred += 1
                        if sample_pred is None: sample_pred = row[pc]
                        break
                if i>=200: break
            return {
                'path': path, 'type':'csv', 'rows_sampled': min(total_rows,200),
                'nonempty_ref': nonempty_ref, 'nonempty_pred': nonempty_pred,
                'sample_ref': sample_ref, 'sample_pred': sample_pred
            }
    except Exception as e:
        return {'path': path, 'error': str(e)}

def check_jsonl(path):
    try:
        nonempty_ref=0; nonempty_pred=0; sample_ref=None; sample_pred=None; total=0
        with open(path, encoding='utf-8') as fh:
            for i,line in enumerate(fh):
                line=line.strip()
                if not line: continue
                total += 1
                try:
                    j=json.loads(line)
                except:
                    continue
                for rc in ('reference','ref','references','target','gold'):
                    if rc in j and j[rc] not in (None,'','[]'):
                        nonempty_ref += 1
                        if sample_ref is None:
                            sample_ref = j[rc] if not isinstance(j[rc], list) else (j[rc][0] if j[rc] else None)
                        break
                for pc in ('prediction','pred','output','response','generated','text','system','hyp'):
                    if pc in j and j[pc] not in (None,''):
                        nonempty_pred += 1
                        if sample_pred is None:
                            sample_pred = j[pc]
                        break
                if i>=500: break
        return {
            'path': path, 'type':'jsonl', 'lines_sampled': min(total,500),
            'nonempty_ref': nonempty_ref, 'nonempty_pred': nonempty_pred,
            'sample_ref': sample_ref, 'sample_pred': sample_pred
        }
    except Exception as e:
        return {'path': path, 'error': str(e)}

def main():
    out=[]
    patterns = [
        os.path.join(ROOT, '**', '*.jsonl'),
        os.path.join(ROOT, '**', '*.csv'),
    ]
    files=[]
    for pat in patterns:
        files.extend(glob.glob(pat, recursive=True))
    files = [f for f in files if 'site-packages' not in f.replace('\\','/') and 'venv' not in f.replace('\\','/') and '.venv' not in f.replace('\\','/')]
    print(f"Scanning {len(files)} files...")
    for f in files:
        if f.lower().endswith('.csv'):
            r = check_csv(f)
        else:
            r = check_jsonl(f)
        out.append(r)
    hits = [o for o in out if ('nonempty_ref' in o and o['nonempty_ref']>0) or ('nonempty_pred' in o and o['nonempty_pred']>0) or 'error' in o]
    print("Files with non-empty text or read errors:", len(hits))
    for h in sorted(hits, key=lambda x: (-x.get('nonempty_pred',0), -x.get('nonempty_ref',0), x.get('path'))):
        print("----")
        print("path:", h.get('path'))
        if 'error' in h:
            print("  ERROR:", h['error'])
            continue
        print("  type:", h.get('type'))
        if 'rows_sampled' in h: print("  rows_sampled:", h.get('rows_sampled'))
        if 'lines_sampled' in h: print("  lines_sampled:", h.get('lines_sampled'))
        print("  nonempty_pred:", h.get('nonempty_pred'), " nonempty_ref:", h.get('nonempty_ref'))
        print("  sample_pred:", (h.get('sample_pred') or '')[:200])
        print("  sample_ref:", (h.get('sample_ref') or '')[:200])

if __name__ == '__main__':
    main()