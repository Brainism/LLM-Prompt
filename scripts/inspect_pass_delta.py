import argparse, json, csv, os
from typing import Dict, Any

def load_jsonl(path: str) -> Dict[str, Dict[str, Any]]:
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise RuntimeError(f"JSON decode error at {path}:{i}: {e}")
            ex_id = obj.get("id") or obj.get("example_id") or obj.get("meta", {}).get("id")
            if not ex_id:
                ex_id = f"ROW_{i}"
            data[str(ex_id)] = obj
    return data

def coerce_bool(x):
    if isinstance(x, bool): return x
    if isinstance(x, (int, float)): return bool(x)
    if isinstance(x, str): return x.strip().lower() in {"1","true","yes","y","t","pass"}
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--cvd", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = load_jsonl(args.baseline)
    cvd  = load_jsonl(args.cvd)

    ids = sorted(set(base.keys()) | set(cvd.keys()))

    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fw:
        w = csv.writer(fw)
        w.writerow([
            "id",
            "base_pass","cvd_pass","delta",
            "cluster_id","lang","len_bin","diff_bin"
        ])
        n_same= n_diff = n_only_base = n_only_cvd = 0
        for ex_id in ids:
            b = base.get(ex_id)
            c = cvd.get(ex_id)
            b_pass = coerce_bool(b.get("pass")) if b else None
            c_pass = coerce_bool(c.get("pass")) if c else None

            meta = {}
            for src in (c, b):
                if not src: continue
                for k in ("cluster_id","lang","len_bin","diff_bin"):
                    if k not in meta and k in src:
                        meta[k] = src[k]
            row = [
                ex_id,
                b_pass, c_pass,
                (None if (b_pass is None or c_pass is None) else int(c_pass) - int(b_pass)),
                meta.get("cluster_id",""),
                meta.get("lang",""),
                meta.get("len_bin",""),
                meta.get("diff_bin",""),
            ]
            w.writerow(row)

            if b and c:
                if (b_pass is None) or (c_pass is None):
                    pass
                elif b_pass == c_pass:
                    n_same += 1
                else:
                    n_diff += 1
            elif b and not c:
                n_only_base += 1
            elif c and not b:
                n_only_cvd += 1

    print(f"[OK] wrote {args.out}")
    print(f"pairs: same={n_same}, diff={n_diff}, only_base={n_only_base}, only_cvd={n_only_cvd}")

if __name__ == "__main__":
    main()