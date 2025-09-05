import json, argparse, glob, csv, re

def parse_meta(filename: str):
    base = filename.rsplit(".",1)[0]
    m = re.match(r"(.+?)_(general|instructed)_(baseline|cvd)$", base, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return "unknown","unknown","unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for fp in glob.glob(f"{args.raw-dir}/*.jsonl"):
        tot, pas = 0, 0
        with open(fp, "r", encoding="utf-8") as f:
            for ln in f:
                o = json.loads(ln)
                p = o.get("pass")
                if p is not None:
                    tot += 1
                    pas += 1 if p else 0
        model, mode, cfg = parse_meta(fp.split("\\")[-1])
        rows.append({
            "model": model, "mode": mode, "cfg": cfg,
            "total": tot, "pass": pas, "pass_rate": round(pas/max(1,tot), 4)
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model","mode","cfg","total","pass","pass_rate"])
        w.writeheader()
        for r in rows: w.writerow(r)
    print("[OK] wrote", args.out)

if __name__ == "__main__":
    main()