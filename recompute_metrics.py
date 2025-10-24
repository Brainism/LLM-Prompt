import os, sys, json, argparse, glob
from tqdm import tqdm
import pandas as pd

def load_manifest(path):
    if not path or not os.path.exists(path):
        return {}
    s = open(path, 'r', encoding='utf-8').read().strip()
    try:
        data = json.loads(s)
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            items = []
    except Exception:
        items = []
        with open(path,'r',encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    items.append(json.loads(line))
                except:
                    continue
    mapping = {}
    for it in items:
        if not isinstance(it, dict): continue
        _id = it.get("id") or it.get("example_id") or it.get("input_id")
        ref = it.get("reference") or it.get("reference_text") or it.get("target") or it.get("text")
        if _id:
            mapping[str(_id)] = ref
    return mapping

def iter_output_files(pattern):
    files = []
    if os.path.isdir(pattern):
        files = glob.glob(os.path.join(pattern, '*'))
    else:
        files = glob.glob(pattern, recursive=True)
        if not files and os.path.exists(pattern):
            files = [pattern]
    return [f for f in files if os.path.isfile(f)]

def load_outputs(paths):
    rows = []
    for p in paths:
        lower = p.lower()
        if lower.endswith('.csv'):
            try:
                df = pd.read_csv(p, dtype=str)
                for _, r in df.iterrows():
                    obj = r.to_dict()
                    obj['_source_file']=p
                    rows.append(obj)
            except Exception:
                continue
        else:
            with open(p,'r',encoding='utf-8',errors='replace') as f:
                for line in f:
                    line=line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                    except:
                        continue
                    if isinstance(obj, dict):
                        obj['_source_file']=p
                        rows.append(obj)
    return rows

def get_text_from_output(o):
    if o is None: return ""
    if isinstance(o, str):
        return o
    if isinstance(o, dict):
        for k in ("prediction","pred","output","outputs","response","text","answer","generated","generation","hypothesis","cand","candidate"):
            if k in o and o[k] is not None:
                return str(o[k])
        for v in o.values():
            if isinstance(v, str) and v.strip():
                return v
    return ""

def safe_float(x):
    try:
        return float(x)
    except:
        return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True, help='path to manifest json/jsonl')
    p.add_argument('--outputs', required=True, help='glob or file path to outputs (jsonl or csv): e.g. "results/raw/*.jsonl"')
    p.add_argument('--out_csv', default='figs/per_item_metrics_recomputed.csv')
    p.add_argument('--force_ref_preview', action='store_true', help='if reference is a JSON string, try to extract text fields')
    args = p.parse_args()

    manifest = load_manifest(args.manifest)
    print(f"Loaded manifest entries: {len(manifest)}", file=sys.stderr)

    paths = iter_output_files(args.outputs)
    if not paths:
        print("No output files found for pattern:", args.outputs, file=sys.stderr)
        sys.exit(2)
    print("Found output files:", file=sys.stderr)
    for pp in paths:
        print("  ", pp, file=sys.stderr)

    outputs = load_outputs(paths)
    print(f"Loaded output objects: {len(outputs)}", file=sys.stderr)
    if len(outputs)==0:
        print("No JSON objects parsed from outputs.", file=sys.stderr)
        sys.exit(3)

    chrf_fn = None
    try:
        from sacrebleu.metrics import CHRF
        chrf_metric = CHRF()
        def compute_chrf(h,r):
            return chrf_metric.sentence_score(h, [r]).score
    except Exception:
        try:
            import sacrebleu
            def compute_chrf(h,r):
                try:
                    return sacrebleu.sentence_chrf(h, r)
                except:
                    return None
        except Exception:
            compute_chrf = lambda h,r: None

    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        def compute_rougeL(h,r):
            try:
                return scorer.score(r, h)['rougeL'].fmeasure
            except:
                return None
    except Exception:
        compute_rougeL = lambda h,r: None

    try:
        import sacrebleu
        def compute_sacrebleu(h,r):
            try:
                return float(sacrebleu.sentence_bleu(h, [r]).score)
            except:
                try:
                    return float(sacrebleu.sentence_chrf(h, r))
                except:
                    return None
    except Exception:
        compute_sacrebleu = lambda h,r: None

    rows=[]
    for obj in tqdm(outputs, desc="items"):
        _id = obj.get('id') or obj.get('example_id') or obj.get('input_id') or obj.get('item_id')
        _id = str(_id) if _id is not None else None
        hyp = get_text_from_output(obj)
        ref = manifest.get(_id) if _id else None
        if ref and isinstance(ref, str) and ref.strip().startswith('{') and args.force_ref_preview:
            try:
                rj=json.loads(ref)
                ref = rj.get('text') or rj.get('reference') or rj.get('title') or ref
            except:
                pass
        ch = None
        rg = None
        sb = None
        if ref and hyp:
            ch = compute_chrf(hyp, ref)
            rg = compute_rougeL(hyp, ref)
            sb = compute_sacrebleu(hyp, ref)
        rows.append({'id': _id, 'hypothesis': hyp, 'reference': ref, 'chrf': ch, 'rougeL': rg, 'sacrebleu': sb, '_source_file': obj.get('_source_file')})

    df = pd.DataFrame(rows)
    if 'chrf' in df.columns:
        sample = df['chrf'].dropna()
        if not sample.empty:
            smin,smax = sample.min(), sample.max()
            if smax <= 1.0:
                df['chrf'] = df['chrf'] * 100.0

    os.makedirs(os.path.dirname(args.out_csv) or '.', exist_ok=True)
    df.to_csv(args.out_csv, index=False, encoding='utf-8-sig')
    print("Wrote per-item metrics to", args.out_csv, file=sys.stderr)
    print(df[['id','chrf','rougeL','sacrebleu']].describe(include='all').to_string(), file=sys.stderr)

if __name__=='__main__':
    main()