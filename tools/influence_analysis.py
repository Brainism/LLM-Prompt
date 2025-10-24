import pandas as pd, numpy as np, json, os
per_item = r"C:\Project\LLM\LLM-clean\results\quantitative\per_item_full_60.csv"
df = pd.read_csv(per_item, dtype=str)
df['base'] = pd.to_numeric(df['base'], errors='coerce')
df['instr'] = pd.to_numeric(df['instr'], errors='coerce')
df = df.dropna(subset=['base','instr']).copy()
df['delta'] = df['instr'] - df['base']
df.sort_values('delta', ascending=False, inplace=True)
top10 = df.head(10)[['id','base','instr','delta']]
bot10 = df.tail(10)[['id','base','instr','delta']]
print("Top10 contributors (by delta):\n", top10.to_string(index=False))
print("\nBottom10 contributors:\n", bot10.to_string(index=False))
res=[]
for k in [0,1,2,3,5,10]:
    d = df.copy()
    if k>0:
        d = d.iloc[k:]
    res.append((k, d['delta'].mean(), d['delta'].std(), len(d)))
print("\nMean delta after removing top-k:\n", res)
outdir = r"C:\Project\LLM\analysis_outputs"
os.makedirs(outdir, exist_ok=True)
top10.to_csv(os.path.join(outdir,"influence_top10.csv"), index=False)
bot10.to_csv(os.path.join(outdir,"influence_bot10.csv"), index=False)
print("Wrote influence CSVs to", outdir)