import argparse
import os
import json
import csv
import math
from pathlib import Path
from difflib import unified_diff, SequenceMatcher

def safe_read_text(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return None

def load_refs(refs_path):
    refs = {}
    if not os.path.exists(refs_path):
        return refs
    with open(refs_path, 'r', encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rid = obj.get('id') or obj.get('item_id') or obj.get('uid')
                if rid:
                    v = obj.get('reference_text') or obj.get('reference') or obj.get('ref') or obj
                    refs[str(rid)] = v
            except Exception:
                continue
    return refs

def normalize_ref_text(ref_raw):
    if ref_raw is None:
        return ""
    if isinstance(ref_raw, dict):
        if 'title' in ref_raw:
            return str(ref_raw.get('title') or "")
        try:
            return json.dumps(ref_raw, ensure_ascii=False)
        except Exception:
            return str(ref_raw)
    if isinstance(ref_raw, list):
        try:
            return json.dumps(ref_raw, ensure_ascii=False)
        except Exception:
            return " ".join(map(str, ref_raw))
    return str(ref_raw)

def find_candidate_texts_in_obj(obj):
    out = {}
    if not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        kl = k.lower()
        if any(tok in kl for tok in ("output","pred","gen","text","response","hypo","answer","result","instr","base","candidate")):
            out[k] = v
    return out

def compute_basic_similarity(ref, hyp):
    try:
        if ref is None:
            ref_s = ""
        else:
            ref_s = json.dumps(ref, ensure_ascii=False) if isinstance(ref, (dict, list)) else str(ref)
        if hyp is None:
            hyp_s = ""
        else:
            hyp_s = json.dumps(hyp, ensure_ascii=False) if isinstance(hyp, (dict, list)) else str(hyp)
        r_tokens = ref_s.split()
        h_tokens = hyp_s.split()
        set_r = set(r_tokens)
        set_h = set(h_tokens)
        tok_overlap = float(len(set_r & set_h) / len(set_r)) if len(set_r) > 0 else 0.0
        seq = SequenceMatcher(None, ref_s, hyp_s).ratio()
        return {"token_overlap": float(tok_overlap), "sequence_similarity": float(seq)}
    except Exception:
        return {"token_overlap": 0.0, "sequence_similarity": 0.0}

def try_compute_sacrebleu(ref, hyp):
    # coerce to strings
    def to_str(x):
        if x is None:
            return ""
        if isinstance(x, (dict, list)):
            try:
                return json.dumps(x, ensure_ascii=False)
            except Exception:
                return str(x)
        return str(x)
    ref_s = to_str(ref)
    hyp_s = to_str(hyp)

    try:
        import sacrebleu
        try:
            score = sacrebleu.sentence_bleu(hyp_s, [ref_s])
            return {"sacrebleu": float(score.score)}
        except Exception:
            return None
    except Exception:
        if len(hyp_s.split()) == 0:
            return {"sacrebleu": 0.0}
        def ngram_counts(tokens, n):
            counts = {}
            L = len(tokens)
            for i in range(L - n + 1):
                ng = tuple(tokens[i:i+n])
                counts[ng] = counts.get(ng, 0) + 1
            return counts
        ref_toks = ref_s.split()
        hyp_toks = hyp_s.split()
        weights = [0.25, 0.25, 0.25, 0.25]
        p_n = []
        for n in range(1,5):
            ref_counts = ngram_counts(ref_toks, n)
            hyp_counts = ngram_counts(hyp_toks, n)
            total = sum(hyp_counts.values())
            if total == 0:
                p_n.append(0.0)
                continue
            clipped = 0
            for ng, cnt in hyp_counts.items():
                clipped += min(cnt, ref_counts.get(ng, 0))
            p_n.append(clipped / total)
        eps = 1e-12
        log_sum = 0.0
        for w, p in zip(weights, p_n):
            if p <= 0:
                log_sum += w * math.log(eps)
            else:
                log_sum += w * math.log(p)
        geo_mean = math.exp(log_sum)
        ref_len = len(ref_toks)
        hyp_len = len(hyp_toks)
        if hyp_len == 0:
            bp = 0.0
        elif hyp_len > ref_len:
            bp = 1.0
        else:
            bp = math.exp(1 - (ref_len / hyp_len))
        bleu_score = bp * geo_mean
        return {"sacrebleu": float(bleu_score * 100.0)}

def scan_repo_for_item(repo_root, item_id, exts=None):
    repo_root = Path(repo_root)
    results = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        parts = Path(dirpath).parts
        if '.venv' in parts or 'venv' in parts:
            continue
        for fn in filenames:
            path = Path(dirpath) / fn
            suffix = path.suffix.lower().lstrip('.')
            if exts and suffix not in exts:
                continue
            text = safe_read_text(path)
            if not text:
                continue
            if item_id not in text:
                continue
            entry = {"path": str(path), "candidates": []}
            if suffix in ('jsonl', 'json'):
                for i, line in enumerate(text.splitlines()):
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                    except Exception:
                        continue
                    if isinstance(obj, dict) and any(str(obj.get(k)) == item_id for k in ("id", "item_id", "uid")):
                        fields = find_candidate_texts_in_obj(obj)
                        entry['candidates'].append({"type": "json_record", "record": obj, "fields": fields})
                if not entry['candidates']:
                    try:
                        whole = json.loads(text)
                        if isinstance(whole, list):
                            for obj in whole:
                                if isinstance(obj, dict) and any(str(obj.get(k)) == item_id for k in ("id", "item_id", "uid")):
                                    fields = find_candidate_texts_in_obj(obj)
                                    entry['candidates'].append({"type": "json_array_record", "record": obj, "fields": fields})
                    except Exception:
                        pass
            if suffix == 'csv':
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        rdr = csv.DictReader(fh)
                        for row in rdr:
                            if any(str(v) == item_id for v in row.values()):
                                fields = {}
                                for k, v in row.items():
                                    if v and any(tok in k.lower() for tok in ("output","pred","gen","text","response","instr","base","ref","candidate")):
                                        fields[k] = v
                                entry['candidates'].append({"type": "csv_row", "row": row, "fields": fields})
                except Exception:
                    pass
            if not entry['candidates']:
                lines = text.splitlines()
                for i, l in enumerate(lines):
                    if item_id in l:
                        start = max(0, i-5); end = min(len(lines), i+6)
                        ctx = "\n".join(lines[start:end])
                        entry['candidates'].append({"type": "context_snippet", "lineno": i+1, "snippet": ctx})
                        break
            results.append(entry)
    return results

def write_json_report(outpath, obj):
    with open(outpath, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)

def write_text_report(txtpath, out):
    with open(txtpath, 'w', encoding='utf-8') as fh:
        fh.write(f"Analysis for {out.get('id')}\n\n")
        fh.write("Reference (normalized):\n")
        fh.write(out.get('ref_text', '') + "\n\n")
        fh.write(f"Found files: {len(out.get('files', []))}\n\n")
        for rec in out.get('files', []):
            fh.write("----\n")
            fh.write("File: " + rec.get('path', '') + "\n")
            for c in rec.get('candidates', []):
                fh.write("  Candidate type: " + c.get('file_type', '') + "\n")
                if 'field' in c:
                    fh.write("    Field: " + str(c.get('field')) + "\n")
                if 'text_preview' in c:
                    txt = c.get('text_preview') or ""
                    fh.write("    Preview (truncated):\n")
                    fh.write(txt + ("\n" if len(txt) < 800 else "\n...[truncated]\n"))
                    ref_text = out.get('ref_text', '') or ""
                    try:
                        diff = "\n".join(unified_diff(ref_text.splitlines(), txt.splitlines(), fromfile='reference', tofile='candidate', lineterm=''))
                        if diff.strip():
                            fh.write("    Unified diff (ref vs candidate):\n")
                            fh.write(diff + "\n")
                    except Exception:
                        pass
                    metrics = c.get('metrics') or {}
                    sim = metrics.get('similarity') or {}
                    fh.write("    Metrics:\n")
                    fh.write("      token_overlap = {:.4f}\n".format(sim.get('token_overlap', 0.0)))
                    fh.write("      seq_similarity = {:.4f}\n".format(sim.get('sequence_similarity', 0.0)))
                    sbleu = metrics.get('sacrebleu')
                    if isinstance(sbleu, dict) and 'sacrebleu' in sbleu:
                        fh.write("      sacreBLEU = {:.4f}\n".format(sbleu.get('sacrebleu')))
                    else:
                        fh.write("      sacreBLEU = (not available)\n")
                elif 'snippet' in c:
                    fh.write("    Snippet (context):\n")
                    fh.write(c.get('snippet', '') + "\n")
            fh.write("\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="item id (e.g. EX-0006)")
    p.add_argument("--repo", default=r"C:\Project\LLM", help="repository root")
    p.add_argument("--refs", default=r"C:\Project\LLM\data\refs.jsonl", help="refs jsonl path")
    p.add_argument("--outdir", default=r"C:\Project\LLM\analysis_outputs", help="output directory")
    p.add_argument("--exts", default="jsonl,json,csv,txt,md,log,out", help="file extensions to search (comma sep)")
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    refs = load_refs(args.refs)
    ref_raw = refs.get(args.id)
    ref_text = normalize_ref_text(ref_raw) if ref_raw is not None else ""

    exts = {e.strip().lower() for e in args.exts.split(",") if e.strip()}
    print(f"Scanning {args.repo!r} for id {args.id} (exts={exts}) ...")
    found = scan_repo_for_item(args.repo, args.id, exts=exts)
    print(f"Found {len(found)} file(s) containing '{args.id}'")

    out = {"id": args.id, "ref_text": ref_text, "found_files_count": len(found), "files": []}

    for f in found:
        rec = {"path": f.get('path'), "candidates": []}
        for cand in f.get('candidates', []):
            if cand.get('type') in ("json_record", "json_array_record"):
                fields = cand.get('fields', {})
                if not fields and isinstance(cand.get('record'), dict):
                    for k in cand.get('record').keys():
                        if any(tok in k.lower() for tok in ("output","pred","gen","text","response","instr","base","candidate","result")):
                            fields[k] = cand['record'][k]
                for k, v in fields.items():
                    if v is None:
                        txt = ""
                    elif isinstance(v, (dict, list)):
                        try:
                            txt = json.dumps(v, ensure_ascii=False)
                        except Exception:
                            txt = str(v)
                    else:
                        txt = str(v)
                    sim = compute_basic_similarity(ref_text, txt)
                    sbleu_raw = try_compute_sacrebleu(ref_text, txt)
                    sbleu = None
                    if isinstance(sbleu_raw, dict):
                        sbleu = sbleu_raw
                    elif isinstance(sbleu_raw, (int, float)):
                        sbleu = {"sacrebleu": float(sbleu_raw)}
                    else:
                        sbleu = None
                    rec['candidates'].append({
                        "file_type": cand.get('type'),
                        "field": k,
                        "text_preview": txt[:800],
                        "metrics": {"similarity": sim, "sacrebleu": sbleu}
                    })
            elif cand.get('type') == "csv_row":
                for k, v in cand.get('fields', {}).items():
                    txt = "" if v is None else str(v)
                    sim = compute_basic_similarity(ref_text, txt)
                    sbleu_raw = try_compute_sacrebleu(ref_text, txt)
                    sbleu = None
                    if isinstance(sbleu_raw, dict):
                        sbleu = sbleu_raw
                    elif isinstance(sbleu_raw, (int, float)):
                        sbleu = {"sacrebleu": float(sbleu_raw)}
                    rec['candidates'].append({
                        "file_type": "csv_row",
                        "field": k,
                        "text_preview": txt[:800],
                        "metrics": {"similarity": sim, "sacrebleu": sbleu}
                    })
            else:
                snippet = cand.get('snippet') or ""
                rec['candidates'].append({
                    "file_type": "context_snippet",
                    "lineno": cand.get('lineno'),
                    "snippet": snippet[:1600]
                })
        out['files'].append(rec)

    json_out = os.path.join(args.outdir, f"{args.id}_analysis.json")
    txt_out = os.path.join(args.outdir, f"{args.id}_analysis.txt")
    write_json_report(json_out, out)
    write_text_report(txt_out, out)

    print("Wrote JSON report:", json_out)
    print("Wrote text report: ", txt_out)
    print("If sacrebleu is not installed and you want exact sacreBLEU, run:")
    print("  (.venv) C:\\Project\\LLM> python -m pip install sacrebleu")
    print("Then re-run this script to include official sacreBLEU sentence scores in the reports.")

if __name__ == "__main__":
    main()