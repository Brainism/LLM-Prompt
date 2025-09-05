from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path
from typing import Any, List, Dict

def _read_lines_any(path: Path) -> List[str]:
    """UTF-8(BOM 포함) 우선, 실패 시 몇 가지 인코딩을 순회하며 안전하게 읽는다."""
    for enc in ("utf-8-sig", "utf-8", "cp949", "mbcs", "euc-kr", "latin1"):
        try:
            return path.read_text(encoding=enc, errors="replace").splitlines()
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore").splitlines()

def _percentile(xs: List[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    if n == 1:
        return float(xs[0])
    idx = (q / 100.0) * (n - 1)
    i = int(idx)
    j = min(i + 1, n - 1)
    frac = idx - i
    return float(xs[i] + (xs[j] - xs[i]) * frac)

def _mean(xs: List[float]) -> float:
    return (sum(xs) / len(xs)) if xs else 0.0

def _extract_latency_and_tokens(obj: Dict[str, Any]) -> tuple[float | None, float | None]:
    latency = None
    t = obj.get("timing")
    if isinstance(t, dict) and isinstance(t.get("latency_ms"), (int, float)):
        latency = float(t["latency_ms"])
    elif isinstance(obj.get("latency_ms"), (int, float)):
        latency = float(obj["latency_ms"])

    tokens = None
    if isinstance(obj.get("tokens"), (int, float)):
        tokens = float(obj["tokens"])

    return latency, tokens

def _summarize_file(jsonl_path: Path) -> Dict[str, Any]:
    latencies: List[float] = []
    tokens: List[float] = []

    for ln, s in enumerate(_read_lines_any(jsonl_path), start=1):
        s = s.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except Exception:
            continue
        lat, tok = _extract_latency_and_tokens(o)
        if isinstance(lat, float):
            latencies.append(lat)
        if isinstance(tok, float):
            tokens.append(tok)

    if not latencies:
        return {
            "file": jsonl_path.name,
            "n": 0,
            "latency_ms_mean": 0.0,
            "latency_ms_p50": 0.0,
            "latency_ms_p95": 0.0,
            "latency_ms_min": 0.0,
            "latency_ms_max": 0.0,
            "tokens_mean": _mean(tokens),
        }

    return {
        "file": jsonl_path.name,
        "n": len(latencies),
        "latency_ms_mean": round(_mean(latencies), 1),
        "latency_ms_p50": round(_percentile(latencies, 50.0) or 0.0, 1),
        "latency_ms_p95": round(_percentile(latencies, 95.0) or 0.0),  # p95는 정수로 보여도 무방
        "latency_ms_min": min(latencies),
        "latency_ms_max": max(latencies),
        "tokens_mean": round(_mean(tokens), 1) if tokens else 0.0,
    }

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Summarize latency & tokens per JSONL file.")
    ap.add_argument("--inputs", required=True, help="Directory containing *.jsonl (e.g., results/raw)")
    ap.add_argument("--out", required=True, help="Output CSV (e.g., results/quantitative/latency_summary.csv)")
    ap.add_argument("--glob", default="*.jsonl", help="Glob pattern under inputs (default: *.jsonl)")
    return ap.parse_args()

def main():
    args = parse_args()
    in_dir = Path(args.inputs)
    out_csv = Path(args.out)

    rows: List[Dict[str, Any]] = []
    for fp_str in glob.glob(str(in_dir / args.glob)):
        fp = Path(fp_str)
        if fp.is_file():
            rows.append(_summarize_file(fp))

    header = [
        "file",
        "n",
        "latency_ms_mean",
        "latency_ms_p50",
        "latency_ms_p95",
        "latency_ms_min",
        "latency_ms_max",
        "tokens_mean",
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})

    print("[OK] wrote", out_csv)

if __name__ == "__main__":
    main()