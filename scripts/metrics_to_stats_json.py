import argparse, json
from pathlib import Path
from collections import defaultdict

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics_json", type=Path, required=True,
                    help="results/quantitative/metrics_per_item.json (from metrics_aggregate)")
    ap.add_argument("--metric", required=True, choices=["pass","lcs_ratio","out_len"],
                    help="which numeric metric to pivot into stats json")
    ap.add_argument("--out", type=Path, required=True,
                    help="path to write metric-specific JSON (e.g. results/quantitative/pass_metric.json)")
    args = ap.parse_args()

    obj = json.loads(args.metrics_json.read_text(encoding="utf-8"))
    per_item = obj.get("per_item") if isinstance(obj, dict) else obj
    group = {}
    for row in per_item:
        pid = str(row.get("id") or row.get("prompt_id") or row.get("prompt"))
        mode = row.get("mode", "").lower()
        val = row.get(args.metric)
        try:
            val = float(val)
        except Exception:
            val = 0.0
        if pid not in group:
            group[pid] = {"id": pid}
        if "general" in mode:
            group[pid]["general"] = val
        elif "instr" in mode:
            group[pid]["instructed"] = val
        else:
            group[pid][mode or "value"] = val

    items = []
    for pid, rec in sorted(group.items()):
        if "general" not in rec: rec["general"] = float("nan")
        if "instructed" not in rec: rec["instructed"] = float("nan")
        items.append({"id": pid, "general": rec["general"], "instructed": rec["instructed"]})

    out_obj = {"items": items}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] wrote", args.out.as_posix())

if __name__ == "__main__":
    main()