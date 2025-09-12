import argparse, os, json, csv, io
from pathlib import Path

def search_file_for_str(path, target):
    out=[]
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            for i, line in enumerate(fh, start=1):
                if target in line:
                    out.append((i, line.rstrip('\n')))
    except Exception as e:
        return []
    return out

def try_parse_jsonl(path, target):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                line = line.strip()
                if not line: continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict) and any(str(obj.get(k))==target for k in ("id","item_id","uid")):
                    return obj
    except Exception:
        pass
    return None

def try_parse_csv_row(path, target):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            sniffer = csv.Sniffer()
            sample = fh.read(8192)
            fh.seek(0)
            dialect = sniffer.sniff(sample) if sample else None
            reader = csv.reader(fh, dialect) if dialect else csv.reader(fh)
            headers = next(reader, None)
            if headers:
                id_idx = None
                for i,h in enumerate(headers):
                    if h and h.lower() in ("id","item_id","uid"):
                        id_idx = i; break
                if id_idx is not None:
                    fh.seek(0)
                    rdr = csv.DictReader(open(path, 'r', encoding='utf-8', errors='ignore'))
                    for row in rdr:
                        for k in row:
                            if row[k] and str(row[k]) == target:
                                return row
                else:
                    fh.seek(0)
                    for row in reader:
                        if any(target == str(cell) for cell in row):
                            return {"row": row}
    except Exception:
        pass
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="item id to search for, e.g. EX-0006")
    p.add_argument("--repo", default=r"C:\Project\LLM", help="root path to search")
    p.add_argument("--ext", default="jsonl,json,csv,txt,md,log,out", help="comma-separated extensions to search")
    args = p.parse_args()

    root = Path(args.repo)
    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()}
    print(f"Searching for '{args.id}' under {root} (exts={exts})\nThis may take a moment...")

    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        if '.venv' in dirpath.split(os.sep) or 'venv' in dirpath.split(os.sep):
            continue
        for fn in filenames:
            lp = Path(dirpath) / fn
            if lp.suffix.lower().lstrip('.') not in exts:
                continue
            found_lines = search_file_for_str(lp, args.id)
            if found_lines:
                matches.append((lp, found_lines))
    if not matches:
        print("No files containing the id were found under the given repo and extensions.")
        print("If you store outputs in a non-standard location or as binary, please provide the path.")
        return

    print(f"Found {len(matches)} file(s) containing '{args.id}':\n")
    for (path, lines) in matches:
        print("----")
        print("File:", path)
        print("Sample matches (up to 5):")
        for ln, text in lines[:5]:
            print(f"  line {ln}: {text}")
        obj = None
        if path.suffix.lower() in (".jsonl", ".json"):
            obj = try_parse_jsonl(path, args.id)
            if obj:
                print("Parsed JSON object for this id:")
                print(json.dumps(obj, ensure_ascii=False, indent=2))
        if path.suffix.lower() == ".csv" and not obj:
            row = try_parse_csv_row(path, args.id)
            if row:
                print("Parsed CSV row (matched):")
                print(row)
    print("\nDone. Use the file paths above to inspect full context or pass correct file paths to tools/inspect_item_outputs.py")

if __name__ == "__main__":
    main()