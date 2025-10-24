import sys, json
import pandas as pd

def load_parsed_outputs(parsed_csv):
    p = pd.read_csv(parsed_csv, dtype=str).fillna('')
    mapping = {}
    for _, row in p.iterrows():
        rid = row.get('id','').strip()
        outcell = row.get('output','')
        if not rid:
            continue
        outcell = outcell.strip()
        if not outcell:
            mapping[rid] = None
            continue
        val = None
        for try_s in (outcell, outcell.strip('"'), outcell.replace("''","'")):
            try:
                val = json.loads(try_s)
                break
            except Exception:
                pass
        if val is None:
            mapping[rid] = {"raw": outcell}
        else:
            mapping[rid] = val
    return mapping

def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    master_csv = sys.argv[1]
    parsed_csv = sys.argv[2]
    *ids, out_master = sys.argv[3:]
    master = pd.read_csv(master_csv, dtype=str).fillna('')
    parsed_map = load_parsed_outputs(parsed_csv)
    updated_count = 0
    for rid in ids:
        rid = rid.strip()
        if rid not in parsed_map:
            print(f"[WARN] id {rid} not found in parsed file {parsed_csv}")
            continue
        val = parsed_map[rid]
        if val is None:
            print(f"[SKIP] parsed output for {rid} is empty; skipping")
            continue
        try:
            new_pred = json.dumps(val, ensure_ascii=False)
        except Exception:
            new_pred = json.dumps({"raw": str(val)}, ensure_ascii=False)
        mask = master['id'].astype(str).str.strip() == rid
        if not mask.any():
            print(f"[WARN] id {rid} not found in master {master_csv}")
            continue
        master.loc[mask, 'prediction'] = new_pred
        updated_count += mask.sum()
        print(f"[OK] updated {mask.sum()} row(s) for id {rid}")
    master.to_csv(out_master, index=False, encoding='utf-8-sig')
    print(f"Wrote updated master to {out_master} (rows={len(master)}), updated_count={updated_count}")

if __name__ == '__main__':
    main()