import json, csv, argparse, re
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"
OUTCSV = ROOT / "results" / "quantitative" / "compliance_summary.csv"

def looks_json(s:str)->bool:
    s=s.strip()
    if not s: return False
    if s[0] in "[{":
        try: json.loads(s); return True
        except: return False
    return False

def count_bullets(s:str)->int:
    return len(re.findall(r'(^|\n)\s*(?:[-*•]|\d+\.)\s+', s))

def read_text_any(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949", "mbcs", "euc-kr", "latin1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=str(RAWDIR))
    ap.add_argument("--glob", default="*.jsonl")
    ap.add_argument("--limit-chars", type=int, default=1000)
    ap.add_argument("--bullets-min-n", type=int, default=3)
    ap.add_argument("--limit-items-json", type=int, default=5)
    ap.add_argument("--forbid-terms", type=str, default=None, help="newline-separated terms file")
    args = ap.parse_args()

    forbid = []
    if args.forbid_terms:
        p = Path(args.forbid_terms)
        if p.exists():
            text = read_text_any(p)
            forbid = [t.strip() for t in text.splitlines() if t.strip()]

    files = sorted(Path(args.raw_dir).glob(args.glob))
    rows=[]
    for fp in files:
        mode = fp.stem
        for ln, line in enumerate(fp.read_text(encoding="utf-8-sig", errors="replace").splitlines(), start=1):
            line=line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
            except:
                continue
            out = rec.get("output","")
            ok_format_json   = looks_json(out)
            ok_limit_chars   = len(out) <= args.limit_chars
            ok_bullets_min_n = count_bullets(out) >= args.bullets_min_n
            ok_forbid_terms  = (all((t not in out) for t in forbid) if forbid else None)

            ok_limit_items_json = None
            if ok_format_json:
                try:
                    j = json.loads(out)
                    if isinstance(j, list):
                        ok_limit_items_json = len(j) <= args.limit_items_json
                except:
                    ok_limit_items_json = False

            rows.append({
                "mode": mode,
                "id": rec.get("id"),
                "format_json": ok_format_json,
                "limit_chars": ok_limit_chars,
                "bullets_min_n": ok_bullets_min_n,
                "limit_items_json": ok_limit_items_json,
                "forbid_terms": ok_forbid_terms,
            })

    by_mode = {"general":{}, "instructed":{}}
    keys = ["format_json","limit_chars","bullets_min_n","limit_items_json","forbid_terms"]
    for mode in by_mode.keys():
        subset = [r for r in rows if r["mode"]==mode]
        n = len(subset) or 1
        for k in keys:
            vals = [r[k] for r in subset if r[k] is not None]
            denom = len(vals) or 1
            by_mode[mode][k] = sum(1 for v in vals if v) / denom

    OUTCSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTCSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric","general_rate","instructed_rate"])
        for k in keys:
            w.writerow([k, f"{by_mode['general'].get(k,0):.3f}", f"{by_mode['instructed'].get(k,0):.3f}"])
    print(f"[ok] wrote {OUTCSV}")

if __name__ == "__main__":
    main()