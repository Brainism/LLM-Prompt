import csv, sys

def main(inp, outp, ids):
    ids_set = set(ids)
    with open(inp, 'r', encoding='utf-8', errors='ignore', newline='') as fh, open(outp, 'w', encoding='utf-8-sig', newline='') as of:
        r = csv.DictReader(fh)
        w = csv.DictWriter(of, fieldnames=r.fieldnames)
        w.writeheader()
        for row in r:
            if row.get('id') in ids_set:
                w.writerow(row)
    print("Wrote subset to", outp)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python scripts\\create_prompt_subset.py <prompts.csv> out_subset.csv id1 id2 ...")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])