import csv, sys

if len(sys.argv) < 3:
    print("Usage: python scripts/prefix_prompt.py <in.csv> <out.csv>")
    sys.exit(1)

inp, out = sys.argv[1], sys.argv[2]

prefix = 'Output exactly one JSON object only. The JSON must be: {\"text\": \"<one-sentence-summary-without-digits>\"}. Do not output anything else.\n\n'

with open(inp, 'r', encoding='utf-8-sig', newline='') as fh:
    reader = csv.DictReader(fh)
    rows = list(reader)
    fieldnames = reader.fieldnames

if 'prompt' not in (fieldnames or []):
    print("Error: input CSV has no 'prompt' column.")
    sys.exit(2)

for r in rows:
    if not (r['prompt'].lstrip().startswith('Output exactly one JSON object only.')):
        r['prompt'] = prefix + r['prompt']

with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {out}")