import pandas as pd, sys
ids = [l.strip() for l in open('missing_instr_ids.txt','r',encoding='utf-8').read().split() if l.strip()]
print('missing ids count=', len(ids))
prompts = pd.read_csv('prompts\\main.csv', encoding='utf-8-sig', dtype=str)
sel = prompts[prompts['id'].isin(ids)]
sel.to_csv('prompts\\missing_instruct_prompts.csv', index=False, encoding='utf-8-sig')
print('Wrote prompts\\missing_instruct_prompts.csv rows=', len(sel))