import argparse, os, json, csv
from pathlib import Path

def is_text_file(path):
    try:
        with open(path, 'rb') as f:
            chunk = f.read(4096)
            if b'\0' in chunk:
                return False
    except Exception:
        return False
    return True

def scan_file_for_id(path, target):
    entries = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
    except Exception:
        return entries
    for i, line in enumerate(lines):
        if target in line:
            start = max(0, i-3)
            end = min(len(lines), i+4)
            ctx = ''.join(lines[start:end])
            entries.append((i+1, line.strip(), ctx))
    return entries

def try_parse_jsonl_object_from_lines(lines, lineno_in_file, target):
    idx = lineno_in_file - 1
    for offset in range(0,3):
        j = idx + offset
        if 0 <= j < len(lines):
            s = lines[j].strip()
            try:
                obj = json.loads(s)
                if isinstance(obj, dict) and any(str(obj.get(k))==target for k in ("id","item_id","uid")):
                    return obj
            except Exception:
                pass
    for span in range(1,6):
        for start in range(max(0, idx-span), idx+1):
            end = min(len(lines), start+span+1)
            chunk = ''.join(lines[start:end]).strip()
            try:
                obj = json.loads(chunk)
                if isinstance(obj, dict) and any(str(obj.get(k))==target for k in ("id","item_id","uid")):
                    return obj
            except Exception:
                pass
    return None

def find_candidate_fields(obj):
    keys = {}
    if not isinstance(obj, dict):
        return keys
    for k,v in obj.items():
        kl = k.lower()
        if any(tok in kl for tok in ("output","pred","gen","text","response","hypo","answer","result")):
            keys[k] = v
        if kl in ("base_output","instr_output","base","instr","base_text","instr_text","base_response","instr_response"):
            keys[k] = v
    return keys

def scan_repo_for_outputs(root, target, exts=None):
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        if '.venv' in dirpath.split(os.sep) or 'venv' in dirpath.split(os.sep):
            continue
        for fn in filenames:
            path = Path(dirpath) / fn
            if exts and path.suffix.lower().lstrip('.') not in exts:
                continue
            if not is_text_file(path):
                continue
            hits = scan_file_for_id(path, target)
            if not hits:
                continue
            parsed = None
            candidate_texts = {}
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = fh.readlines()
                for lineno, line, ctx in hits:
                    if path.suffix.lower() in ('.jsonl', '.json'):
                        obj = try_parse_jsonl_object_from_lines(lines, lineno, target)
                        if obj:
                            parsed = obj
                            candidate_texts = find_candidate_fields(obj)
                            break
                    if path.suffix.lower() == '.csv' and parsed is None:
                        try:
                            fh = open(path, 'r', encoding='utf-8', errors='ignore')
                            rdr = csv.DictReader(fh)
                            for row in rdr:
                                if any(str(row.get(k))==target for k in row.keys()):
                                    parsed = row
                                    for k in row:
                                        kl = k.lower()
                                        if any(tok in kl for tok in ("output","pred","gen","text","response","instr","base")):
                                            candidate_texts[k] = row[k]
                                    break
                        except Exception:
                            pass
            except Exception:
                pass
            matches.append({
                "path": str(path),
                "hits": hits,
                "parsed": parsed,
                "candidate_texts": candidate_texts
            })
    return matches

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="item id e.g. EX-0006")
    parser.add_argument("--repo", default=r"C:\Project\LLM", help="repo root")
    parser.add_argument("--ext", default="jsonl,json,csv,txt,md,log,out", help="extensions to search")
    args = parser.parse_args()

    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()}
    print("Searching", args.repo, "for id", args.id, "exts=", exts)
    matches = scan_repo_for_outputs(args.repo, args.id, exts=exts)
    outdir = Path(args.repo) / "analysis_outputs"
    outdir.mkdir(exist_ok=True)
    outpath = outdir / f"{args.id}_extract_report.txt"
    with open(outpath, "w", encoding="utf-8") as outfh:
        outfh.write(f"Search report for {args.id}\n\n")
        for m in matches:
            outfh.write("----\n")
            outfh.write("File: " + m["path"] + "\n")
            outfh.write("Sample hits:\n")
            for lineno, line, ctx in m["hits"][:5]:
                outfh.write(f"  line {lineno}: {line.strip()}\n")
            outfh.write("\n")
            if m["parsed"]:
                outfh.write("Parsed object/row (first match):\n")
                try:
                    outfh.write(json.dumps(m["parsed"], ensure_ascii=False, indent=2))
                    outfh.write("\n")
                except Exception:
                    outfh.write(str(m["parsed"]) + "\n")
            if m["candidate_texts"]:
                outfh.write("\nCandidate text fields found:\n")
                for k,v in m["candidate_texts"].items():
                    outfh.write(f"  FIELD: {k}\n")
                    s = str(v)
                    outfh.write(s[:400] + ("\n...[truncated]\n" if len(s)>400 else "\n"))
            outfh.write("\n")
    print("Wrote report to", outpath)
    print("If the report contains candidate text fields, examine them. If no raw outputs were found, provide the model outputs JSONL files or re-run generation to save them.")

if __name__ == "__main__":
    main()