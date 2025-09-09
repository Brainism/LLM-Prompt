from __future__ import annotations
import argparse, csv, json, sys, traceback
from pathlib import Path
from typing import Dict

def read_prompts_csv(p: Path) -> Dict[str, str]:
    if not p.exists(): return {}
    m = {}
    with p.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = row.get("id") or row.get("ID") or row.get("prompt_id")
            ref = row.get("reference") or row.get("answer") or row.get("output") or ""
            if pid:
                m[str(pid).strip()] = (ref or "").strip()
    return m

def read_manifest_json(p: Path) -> Dict[str, str]:
    if not p.exists(): return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    m = {}
    if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], list):
        for it in obj["items"]:
            pid = str(it.get("id") or it.get("prompt_id") or "").strip()
            ref = it.get("reference") or it.get("answer") or ""
            if pid:
                m[pid] = (ref or "").strip()
    return m

def read_jsonl_map(p: Path) -> Dict[str, str]:
    out = {}
    if not p.exists(): return out
    with p.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            pid = str(o.get("id") or o.get("prompt_id") or "").strip()
            txt = o.get("output") or o.get("text") or o.get("response") or o.get("result") or ""
            if pid:
                out[pid] = str(txt)
    return out

def lcs_len(a: str, b: str) -> int:
    if not a or not b: return 0
    A, B = a, b
    la, lb = len(A), len(B)
    dp = [0]*(lb+1)
    for i in range(la):
        prev = 0
        ai = A[i]
        for j in range(lb):
            tmp = dp[j+1]
            if ai == B[j]:
                dp[j+1] = prev + 1
            else:
                if dp[j] > dp[j+1]:
                    dp[j+1] = dp[j]
            prev = tmp
    return dp[lb]

def compute_metrics(ref: str, out: str):
    ref_s = (ref or "").strip()
    out_s = (out or "").strip()
    if not ref_s:
        pass_flag = 0.0
        lcs_ratio = 0.0
    else:
        pass_flag = 1.0 if ref_s.lower() in out_s.lower() else 0.0
        lcs = lcs_len(ref_s, out_s)
        lcs_ratio = lcs / max(1, len(ref_s))
    return {"pass": float(pass_flag), "lcs_ratio": float(lcs_ratio), "out_len": len(out_s)}

def ensure_parent(path: Path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", type=Path, help="prompts CSV (id,reference,...)")
    ap.add_argument("--manifest", type=Path, help="manifest JSON with items[].id & items[].reference")
    ap.add_argument("--general", type=Path, required=True, help="general jsonl outputs")
    ap.add_argument("--instructed", type=Path, required=True, help="instructed jsonl outputs")
    ap.add_argument("--out_csv", type=Path, required=True)
    ap.add_argument("--out_json", type=Path, required=True)
    args = ap.parse_args()

    try:
        ref_map = {}
        if args.prompts and args.prompts.exists():
            ref_map.update(read_prompts_csv(args.prompts))
        if args.manifest and args.manifest.exists():
            ref_map.update(read_manifest_json(args.manifest))

        gen_map = read_jsonl_map(args.general)
        ins_map = read_jsonl_map(args.instructed)

        if not gen_map and not ins_map:
            print("ERROR: both general and instructed outputs appear empty or missing.", file=sys.stderr)
            sys.exit(2)

        ids = sorted(set(list(gen_map.keys()) + list(ins_map.keys()) + list(ref_map.keys())))

        per_item = []
        csv_rows = []
        for pid in ids:
            ref = ref_map.get(pid, "")
            out_g = gen_map.get(pid, "")
            mg = compute_metrics(ref, out_g)
            entry_g = {"id": pid, "prompt_id": pid, "mode": "general", **mg}
            per_item.append(entry_g)
            csv_rows.append(entry_g)
            out_i = ins_map.get(pid, "")
            mi = compute_metrics(ref, out_i)
            entry_i = {"id": pid, "prompt_id": pid, "mode": "instructed", **mi}
            per_item.append(entry_i)
            csv_rows.append(entry_i)

        out_json_obj = {"per_item": per_item}
        ensure_parent(args.out_json)
        ensure_parent(args.out_csv)

        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(out_json_obj, f, ensure_ascii=False, indent=2)
        fieldnames = ["id","prompt_id","mode","pass","lcs_ratio","out_len"]
        with args.out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in csv_rows:
                w.writerow({k: (r.get(k, "") if r.get(k, "") is not None else "") for k in fieldnames})

        print("[OK] wrote", args.out_csv.as_posix(), args.out_json.as_posix())
        sys.exit(0)

    except Exception as e:
        print("Unhandled error in metrics_aggregate:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(3)

if __name__ == "__main__":
    main()