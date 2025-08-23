from __future__ import annotations
import json, argparse
from pathlib import Path
from datetime import timedelta
import csv

ROOT = Path(__file__).resolve().parents[1]
RAW  = ROOT / "results" / "raw"
PROM = ROOT / "prompts" / "prompts.csv"

def read_latencies(fp: Path):
    xs=[]
    if not fp.exists(): return xs
    for ln,s in enumerate(fp.read_text(encoding="utf-8-sig", errors="replace").splitlines(),1):
        s=s.strip()
        if not s: continue
        try:
            rec=json.loads(s)
            t=rec.get("timing") or {}
            ms=t.get("latency_ms")
            if isinstance(ms,(int,float)): xs.append(float(ms))
        except: pass
    return xs

def ids_from_jsonl(fp: Path):
    ids=set()
    if not fp.exists(): return ids
    for s in fp.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s=s.strip()
        if not s: continue
        try:
            rec=json.loads(s)
            if "id" in rec: ids.add(str(rec["id"]))
        except: pass
    return ids

def all_ids_from_csv(csv_path: Path, id_col="id"):
    ids=[]
    with csv_path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            v=(row.get(id_col) or "").strip()
            if v: ids.append(v)
    return ids

def fmt_td(seconds: float) -> str:
    return str(timedelta(seconds=int(round(seconds))))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--prompts", type=Path, default=PROM)
    ap.add_argument("--general", type=Path, default=RAW/"general.jsonl")
    ap.add_argument("--instructed", type=Path, default=RAW/"instructed.jsonl")
    ap.add_argument("--overhead-ms", type=float, default=250.0, help="레코드당 고정 오버헤드(ms) 가정")
    ap.add_argument("--concurrency", type=int, default=1, help="동시 실행 개수(일반=1)")
    args=ap.parse_args()

    all_ids = all_ids_from_csv(args.prompts)
    total = len(all_ids)

    done_g = ids_from_jsonl(args.general)
    done_i = ids_from_jsonl(args.instructed)

    remain_g = total - len(done_g)
    remain_i = total - len(done_i)

    lat_g = read_latencies(args.general)
    lat_i = read_latencies(args.instructed)
    mean_g = (sum(lat_g)/len(lat_g)) if lat_g else None
    mean_i = (sum(lat_i)/len(lat_i)) if lat_i else None

    oh = args.overhead_ms
    sec_g = (remain_g * ((mean_g or 0)+oh))/1000.0 / max(args.concurrency,1)
    sec_i = (remain_i * ((mean_i or 0)+oh))/1000.0 / max(args.concurrency,1)

    total_sec = sec_g + sec_i

    print(f"[prompts] total={total}")
    print(f"[done] general={len(done_g)} instructed={len(done_i)}")
    print(f"[remain] general={remain_g} instructed={remain_i}")
    print(f"[latency(ms)] mean_general={mean_g:.1f} mean_instructed={mean_i:.1f}" if (mean_g is not None and mean_i is not None) else "[latency] 부족: 스모크라도 먼저 실행해 측정치를 남겨주세요")
    print(f"[assume] overhead_ms={oh:.0f}  concurrency={args.concurrency}")
    print(f"[ETA] general ~ {fmt_td(sec_g)}  +  instructed ~ {fmt_td(sec_i)}  =>  total ~ {fmt_td(total_sec)}")
if __name__=="__main__":
    main()