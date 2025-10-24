from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Aggregate p50/p95 latency & cost from JSONL logs.")
    ap.add_argument("--raw-glob", default="results/raw/*.jsonl",
                    help="Glob pattern for input JSONL logs (default: results/raw/*.jsonl)")
    ap.add_argument("--out", default="results/quantitative/efficiency_tile.json",
                    help="Output JSON path (default: results/quantitative/efficiency_tile.json)")
    ap.add_argument("--latency-field", default="latency_ms",
                    help="Field name for latency in milliseconds (default: latency_ms)")
    ap.add_argument("--cost-field", default="cost_usd",
                    help="Field name for cost in USD (default: cost_usd)")
    ap.add_argument("--group-by", default="",
                    help="Comma-separated fields to group by (e.g., model,mode). Empty for overall only.")
    ap.add_argument("--percentiles", default="50,95",
                    help="Comma-separated percentiles to compute (default: 50,95)")
    ap.add_argument("--fail-on-empty", action="store_true",
                    help="Exit with non-zero code if no valid records found.")
    return ap.parse_args()


def load_records(glob_pattern: str) -> List[Dict[str, Any]]:
    root = Path(".").resolve()
    recs: List[Dict[str, Any]] = []
    files = sorted(root.glob(glob_pattern))
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
                if isinstance(rec, dict):
                    recs.append(rec)
            except Exception:
                continue
    return recs


def safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def pct_stats(values: Iterable[float], percentiles: List[float]) -> Dict[str, float]:
    arr = np.array([x for x in values if x is not None], dtype=float)
    if arr.size == 0:
        return {"count": 0}
    out: Dict[str, float] = {
        "count": int(arr.size),
        "mean": float(arr.mean()),
    }
    ps = sorted(set([p for p in percentiles if 0 <= p <= 100]))
    for p in ps:
        out[f"p{int(p)}"] = float(np.percentile(arr, p))
    return out


def group_key(rec: Dict[str, Any], fields: List[str]) -> Tuple[Any, ...]:
    return tuple(rec.get(f, None) for f in fields)


def aggregate(
    recs: List[Dict[str, Any]],
    latency_field: str,
    cost_field: str,
    pcts: List[float],
    group_fields: List[str],
) -> Dict[str, Any]:
    lat_all: List[float | None] = []
    cost_all: List[float | None] = []
    for r in recs:
        lat_all.append(safe_float(r.get(latency_field)))
        cost_all.append(safe_float(r.get(cost_field)))

    result: Dict[str, Any] = {
        "overall": {
            "latency_ms": pct_stats([v for v in lat_all if v is not None], pcts),
            "cost_usd": pct_stats([v for v in cost_all if v is not None], pcts),
        },
        "meta": {
            "n_records": len(recs),
            "latency_field": latency_field,
            "cost_field": cost_field,
            "percentiles": pcts,
        },
    }

    if group_fields:
        groups: Dict[Tuple[Any, ...], Dict[str, List[float]]] = {}
        for r in recs:
            key = group_key(r, group_fields)
            g = groups.setdefault(key, {"lat": [], "cost": []})
            lat = safe_float(r.get(latency_field))
            cost = safe_float(r.get(cost_field))
            if lat is not None:
                g["lat"].append(lat)
            if cost is not None:
                g["cost"].append(cost)
        per_group: Dict[str, Any] = {}
        for k, vals in groups.items():
            label = "|".join([str(x) for x in k])
            per_group[label] = {
                "latency_ms": pct_stats(vals["lat"], pcts),
                "cost_usd": pct_stats(vals["cost"], pcts),
            }
        result["by_group"] = {
            "fields": group_fields,
            "tiles": per_group,
        }

    return result


def main() -> None:
    args = parse_args()
    recs = load_records(args.raw_glob)
    if not recs:
        msg = f"No records found for pattern: {args.raw_glob}"
        if args.fail_on_empty:
            raise SystemExit(msg)
        else:
            outp = Path(args.out)
            outp.parent.mkdir(parents=True, exist_ok=True)
            outp.write_text(json.dumps({"overall": {}, "meta": {"n_records": 0}}, indent=2), encoding="utf-8")
            print("[warn]", msg, "→ wrote empty tile:", outp)
            return

    pcts = []
    for tok in (args.percentiles.split(",") if args.percentiles else []):
        tok = tok.strip()
        if tok:
            try:
                pcts.append(float(tok))
            except Exception:
                pass
    if not pcts:
        pcts = [50.0, 95.0]

    group_fields = [f.strip() for f in args.group_by.split(",") if f.strip()]

    result = aggregate(
        recs=recs,
        latency_field=args.latency_field,
        cost_field=args.cost_field,
        pcts=pcts,
        group_fields=group_fields,
    )

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("[OK] wrote:", outp)


if __name__ == "__main__":
    main()