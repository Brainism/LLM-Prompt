import json, sys
from pathlib import Path
import sacrebleu

def load_per_item_csv(path):
    import csv
    rows=[]
    with open(path, newline='', encoding='utf8') as fh:
        reader=csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows

def load_per_item_jsonl(path):
    rows=[]
    with open(path, encoding='utf8') as fh:
        for line in fh:
            if not line.strip(): continue
            rows.append(json.loads(line))
    return rows

def main():
    full_path = Path(r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv")
    rows = load_per_item_csv(full_path)
    refs = {}
    with open(r"C:\Project\LLM\LLM-clean\data\refs.jsonl", encoding='utf8') as fh:
        for line in fh:
            obj=json.loads(line)
            refs[obj['id']]=obj.get('reference_text', '')
    out=[]
    for r in rows:
        idr=r['id']
        cand_text_base = None
        cand_text_instr = None
        cand_text_base = str(r['base'])
        cand_text_instr = str(r['instr'])
        ref_text = refs.get(idr, "")
        try:
            s_base = sacrebleu.sentence_bleu(cand_text_base, [ref_text]).score
            s_instr = sacrebleu.sentence_bleu(cand_text_instr, [ref_text]).score
        except Exception as e:
            s_base = None
            s_instr = None
        out.append({
            'id': idr,
            'sacrebleu_base': s_base,
            'sacrebleu_instr': s_instr,
            'ref_preview': ref_text[:200],
            'cand_base_preview': cand_text_base[:200],
            'cand_instr_preview': cand_text_instr[:200]
        })
    import csv
    keys = ['id','sacrebleu_base','sacrebleu_instr','ref_preview','cand_base_preview','cand_instr_preview']
    with open(r"C:\Project\LLM\analysis_outputs\sentence_sacrebleu_by_item.csv", "w", encoding="utf8", newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for row in out:
            writer.writerow(row)
    print("Wrote: C:\\Project\\LLM\\analysis_outputs\\sentence_sacrebleu_by_item.csv")

if __name__ == '__main__':
    main()