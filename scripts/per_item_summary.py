import csv
from pathlib import Path
from operator import itemgetter

IN_CSV = Path("results/quantitative/per_item_diffs.csv")
OUT_DIR = Path("results/quantitative")

METRICS = [
    ("bleu_sacre", "bleu_sacre_diff"),
    ("rouge", "rouge_diff"),
    ("chrf", "chrf_diff"),
]

def load_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run per_item_diffs generation first.")
    rows = []
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def to_float(x):
    try:
        return float(x) if x is not None and x != "" else None
    except Exception:
        return None

def write_subset(name, rows, header):
    out = OUT_DIR / name
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r.get(h,"") for h in header])
    return out

def main():
    rows = load_rows(IN_CSV)
    header = list(rows[0].keys()) if rows else []
    print(f"[INFO] loaded {len(rows)} rows from {IN_CSV}")
    for metric, diff_col in METRICS:
        items = []
        for r in rows:
            iid = r.get("id")
            diff = to_float(r.get(diff_col))
            items.append({"id": iid, "diff": diff, "row": r})
        items_valid = [i for i in items if i["diff"] is not None]
        top = sorted(items_valid, key=itemgetter("diff"), reverse=True)[:10]
        bottom = sorted(items_valid, key=itemgetter("diff"))[:10]
        top_name = f"top10_{metric}.csv"
        bottom_name = f"bottom10_{metric}.csv"
        write_subset(top_name, [i["row"] for i in top], header)
        write_subset(bottom_name, [i["row"] for i in bottom], header)
        print(f"\n=== {metric} ===")
        print("Top 10 (largest increases):")
        for i in top:
            print(f"  {i['id']:10s}  diff={i['diff']}")
        print("Bottom 10 (largest decreases):")
        for i in bottom:
            print(f"  {i['id']:10s}  diff={i['diff']}")
    print("\n[OK] wrote top/bottom CSVs to results/quantitative/")

if __name__ == "__main__":
    main()