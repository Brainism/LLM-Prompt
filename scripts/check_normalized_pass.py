import json, re
def norm(s): return re.sub(r'\W+',' ', (s or '').lower()).strip()
m = json.load(open('split_manifest.json', encoding='utf-8'))
refs = {it['id']: it.get('reference','') for it in m['items']}
gen = [json.loads(l) for l in open('results/raw/general.jsonl', encoding='utf-8')]
instr = [json.loads(l) for l in open('results/raw/instructed.jsonl', encoding='utf-8')]
gmap = {o['id']: o.get('output','') for o in gen}
imap = {o['id']: o.get('output','') for o in instr}
hits = 0
for pid, ref in refs.items():
    r = norm(ref)
    og = norm(gmap.get(pid,''))
    oi = norm(imap.get(pid,''))
    if r and r in og: hits += 1
print('normalized hits (general):', hits, ' / ', len(refs))