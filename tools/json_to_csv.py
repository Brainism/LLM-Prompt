import sys, json
import pandas as pd
if len(sys.argv) < 3:
    print("Usage: python tools/json_to_csv.py input.json output.csv")
    sys.exit(1)
inp = sys.argv[1]
out = sys.argv[2]
with open(inp, "r", encoding="utf-8") as f:
    j = json.load(f)
if isinstance(j, dict) and "items" in j and isinstance(j["items"], list):
    rows = j["items"]
elif isinstance(j, list):
    rows = j
else:
    rows = [j]
df = pd.DataFrame(rows)
cols_lower = {c.lower(): c for c in df.columns}
id_col = cols_lower.get("id", None)
base_col = None
instr_col = None
for c in df.columns:
    low = c.lower()
    if "base" in low and "bleu" in low:
        base_col = c
    if "instr" in low and "bleu" in low:
        instr_col = c
if base_col is None:
    for c in df.columns:
        if c.lower() == "base":
            base_col = c
if instr_col is None:
    for c in df.columns:
        if c.lower() == "instr":
            if base_col is None or instr_col is None:
                bleu_cols = [c for c in df.columns if "bleu" in c.lower()]
    if len(bleu_cols) >= 2:
        if base_col is None: base_col = bleu_cols[0]
        if instr_col is None: instr_col = bleu_cols[1]
if id_col is None:
    df = df.reset_index().rename(columns={"index":"_idx"})
    df["_idx"] = df["_idx"].apply(lambda x: f"EX-{x+1:04d}")
    id_col = "_idx"
rename = {}
rename[id_col] = "id"
if base_col: rename[base_col] = "base"
if instr_col: rename[instr_col] = "instr"
df = df.rename(columns=rename)
keep = ["id"]
if "base" in df.columns: keep.append("base")
if "instr" in df.columns: keep.append("instr")
df[keep].to_csv(out, index=False, encoding="utf-8")
print("Wrote:", out)