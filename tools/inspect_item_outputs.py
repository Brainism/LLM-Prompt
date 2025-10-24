import sys, json, os
def find_in_jsonl(path, item_id):
    if not os.path.exists(path):
        print("Not found:", path); return None
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            try:
                rec=json.loads(line)
            except:
                continue
            if rec.get('id')==item_id or rec.get('item_id')==item_id:
                return rec
    return None

if __name__=='__main__':
    if len(sys.argv)<4:
        print("Usage: python tools/inspect_item_outputs.py <ITEM_ID> <BASE_JSONL> <INSTR_JSONL>")
        sys.exit(1)
    item, basep, instrp = sys.argv[1], sys.argv[2], sys.argv[3]
    b = find_in_jsonl(basep, item)
    i = find_in_jsonl(instrp, item)
    print("=== BASE ===")
    print(json.dumps(b, indent=2, ensure_ascii=False))
    print("=== INSTR ===")
    print(json.dumps(i, indent=2, ensure_ascii=False))