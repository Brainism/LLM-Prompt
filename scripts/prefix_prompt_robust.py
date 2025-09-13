import csv, sys, os

if len(sys.argv) < 3:
    print("Usage: python scripts/prefix_prompt_robust.py <in.csv> <out.csv>")
    sys.exit(1)

inp, out = sys.argv[1], sys.argv[2]
prefix = 'Output exactly one JSON object only. The JSON must be: {"text": "<one-sentence-summary-without-digits>"}. Do not output anything else.\n\n'

with open(inp, 'r', encoding='utf-8-sig', newline='') as fh:
    reader = csv.reader(fh)
    rows = list(reader)

if not rows:
    print("Error: input file is empty")
    sys.exit(2)

header = rows[0]
is_header = any(any(ch.isalpha() for ch in cell) for cell in header) and not header[0].lstrip().startswith(('{','[','{\"'))

fieldnames = None
prompt_col_idx = None
used_col_name = None

candidates = ['prompt','text','instruction','input','prompt_text','message']

if is_header:
    norm = [h.strip() for h in header]
    low = [h.lower() for h in norm]
    for cand in candidates:
        if cand in low:
            prompt_col_idx = low.index(cand)
            used_col_name = norm[prompt_col_idx]
            break
    if prompt_col_idx is None:
        prompt_col_idx = 0
        used_col_name = norm[0]
    fieldnames = norm
    data_rows = rows[1:]
else:
    prompt_col_idx = 0
    used_col_name = 'prompt'
    data_rows = rows

out_rows = []
for r in data_rows:
    if len(r) < len(fieldnames):
        r += [''] * (len(fieldnames) - len(r))
    d = dict(zip(fieldnames, r[:len(fieldnames)]))
    cur = d.get(fieldnames[prompt_col_idx], '')
    if not str(cur).lstrip().startswith('Output exactly one JSON object only.'):
        d[fieldnames[prompt_col_idx]] = prefix + str(cur)
    out_rows.append(d)

with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(out_rows)

print(f"Wrote {len(out_rows)} rows to {out} (prefixed column: '{used_col_name}')")