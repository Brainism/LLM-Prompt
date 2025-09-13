import json, sys

if len(sys.argv) < 3:
    print("Usage: python scripts/inspect_jsonl.py <file.jsonl> <ID1> [ID2 ...]")
    sys.exit(1)

fn = sys.argv[1]
ids = set(sys.argv[2:])

with open(fn, 'r', encoding='utf-8', errors='replace') as f:
    for lineno, line in enumerate(f, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # skip malformed line
            continue
        if obj.get('id') in ids:
            print(f"=== LINE {lineno} : id={obj.get('id')} ===")
            print(json.dumps(obj, ensure_ascii=False, indent=2))
            print()
