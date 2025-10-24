import json, csv, os, argparse
from collections import OrderedDict
from sacrebleu.metrics import BLEU, CHRF
from rouge_score import rouge_scorer

def read_prompts_csv(path):
    refs = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for row in r:
            ex_id = row.get('id') or row.get('ID') or row.get('Id')
            ref   = row.get('reference') or row.get('ref') or row.get('target')
            if ex_id:
                refs[str(ex_id)] = (ref or "").strip()
    return refs

def read_outputs_jsonl(path):
    out = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            obj = json.loads(line)
            ex_id = (obj.get('id') or obj.get('example_id') or
                     (obj.get('meta') or {}).get('id'))
            text = (obj.get('output') or obj.get('text') or obj.get('response') or
                    (obj.get('result') or {}).get('text') or
                    (obj.get('choices')[0].get('text') if obj.get('choices') else None) or
                    "")
            if ex_id:
                out[str(ex_id)] = str(text).strip()
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompts', required=True)
    ap.add_argument('--gen', required=True, help='results\\raw\\v2\\general.jsonl')
    ap.add_argument('--ins', required=True, help='results\\raw\\v2\\instructed.jsonl')
    ap.add_argument('--outdir', default='results/quantitative')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    refs = read_prompts_csv(args.prompts)
    gen  = read_outputs_jsonl(args.gen)
    ins  = read_outputs_jsonl(args.ins)

    ids = sorted(set(refs.keys()) & set(gen.keys()) & set(ins.keys()), key=lambda x: (len(x), x))

    bleu = BLEU(effective_order=True)
    chrf = CHRF(word_order=2)
    rsc  = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

    bleu_rows, chrf_rows, rouge_rows = [], [], []

    for ex_id in ids:
        ref = refs[ex_id] or ""
        g = gen.get(ex_id, "")
        i = ins.get(ex_id, "")

        bleu_g = bleu.sentence_score(g, [ref]).score
        bleu_i = bleu.sentence_score(i, [ref]).score
        chrf_g = chrf.sentence_score(g, [ref]).score
        chrf_i = chrf.sentence_score(i, [ref]).score

        r_g = rsc.score(ref, g)['rougeL'].fmeasure
        r_i = rsc.score(ref, i)['rougeL'].fmeasure

        bleu_rows.append(OrderedDict(id=ex_id, base=bleu_g, instr=bleu_i))
        chrf_rows.append(OrderedDict(id=ex_id, base=chrf_g, instr=chrf_i))
        rouge_rows.append(OrderedDict(id=ex_id, base=r_g,   instr=r_i))

    with open(os.path.join(args.outdir, 'bleu_sacre.json'), 'w', encoding='utf-8') as f:
        json.dump(bleu_rows, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.outdir, 'chrf.json'), 'w', encoding='utf-8') as f:
        json.dump(chrf_rows, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.outdir, 'rouge.json'), 'w', encoding='utf-8') as f:
        json.dump(rouge_rows, f, ensure_ascii=False, indent=2)

    print(f"[OK] wrote {args.outdir}\\bleu_sacre.json / chrf.json / rouge.json")
    print(f"n(ids)={len(ids)}")

if __name__ == '__main__':
    main()