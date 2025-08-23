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
    for enc in ("utf-8","utf-8-sig","cp949","mbcs","euc-kr","latin1"):
        try: return path.read_text(encoding=enc)
        except UnicodeDecodeError: continue
    return path.read_bytes().decode("utf-8", errors="ignore")

def parse_flag(v: str):
    if v is None: return None
    s = v.strip().lower()
    if s in ("1","true","y","yes"):  return True
    if s in ("0","false","n","no"):  return False
    return None

def load_apply_map(csv_path: Path, id_col="id"):
    """prompts.csv에서 id별 needs_* 플래그 로드 (없거나 비면 None)"""
    if not csv_path or not csv_path.exists(): return {}
    m={}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            pid = (row.get(id_col) or "").strip()
            if not pid: continue
            m[pid]={
                "needs_json":    parse_flag(row.get("needs_json")),
                "needs_bullets": parse_flag(row.get("needs_bullets")),
                "needs_length":  parse_flag(row.get("needs_length")),
                "needs_forbid":  parse_flag(row.get("needs_forbid")),
            }
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=str(RAWDIR))
    ap.add_argument("--glob", default="*.jsonl")
    ap.add_argument("--limit-chars", type=int, default=1000)
    ap.add_argument("--bullets-min-n", type=int, default=3)
    ap.add_argument("--limit-items-json", type=int, default=5)
    ap.add_argument("--forbid-terms", type=str, default=None, help="newline-separated terms file")
    ap.add_argument("--apply-from", type=str, default=None, help="prompts.csv with needs_* flags")
    ap.add_argument("--id-col", type=str, default="id")
    args = ap.parse_args()

    forbid = []
    if args.forbid_terms:
        p = Path(args.forbid_terms)
        if p.exists():
            text = read_text_any(p)
            forbid = [t.strip() for t in text.splitlines() if t.strip()]

    apply_map = load_apply_map(Path(args.apply_from), id_col=args.id_col) if args.apply_from else {}

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
            pid = str(rec.get("id", ""))
            needs = apply_map.get(pid, {
                "needs_json": None, "needs_bullets": None, "needs_length": None, "needs_forbid": None
            })
            out = rec.get("output","")

            v_format_json  = looks_json(out)                    if needs["needs_json"]    is True else None
            v_bullets_min  = (count_bullets(out) >= args.bullets_min_n) if needs["needs_bullets"] is True else None
            v_limit_chars  = (len(out) <= args.limit_chars)     if needs["needs_length"]  is True else None
            v_forbid_terms = (all((t not in out) for t in forbid) if forbid else None) if needs["needs_forbid"] is True else None

            v_limit_items_json = None
            if v_format_json is True:
                try:
                    j = json.loads(out)
                    if isinstance(j, list):
                        v_limit_items_json = (len(j) <= args.limit_items_json)
                    else:
                        v_limit_items_json = None
                except:
                    v_limit_items_json = False

            rows.append({
                "mode": mode, "id": pid,
                "format_json": v_format_json,
                "limit_chars": v_limit_chars,
                "bullets_min_n": v_bullets_min,
                "limit_items_json": v_limit_items_json,
                "forbid_terms": v_forbid_terms,
            })

    by_mode = {"general":{}, "instructed":{}}
    keys = ["format_json","limit_chars","bullets_min_n","limit_items_json","forbid_terms"]
    for mode in by_mode.keys():
        subset = [r for r in rows if r["mode"]==mode]
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