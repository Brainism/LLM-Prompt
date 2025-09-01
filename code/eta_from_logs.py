from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Set

def load_latencies(files: List[Path]) -> List[float]:
    xs: List[float] = []
    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            ms = obj.get("latency_ms")
            if isinstance(ms, (int, float)):
                xs.append(float(ms))
        except Exception:
            pass
    return xs

def load_ids(files: List[Path]) -> Set[str]:
    ids: Set[str] = set()
    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if "id" in obj:
                ids.add(str(obj["id"]))
        except Exception:
            pass
    return ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mean-latency-ms", type=float, default=250.0,
                    help="Assumed average latency per request (ms).")
    ap.add_argument("--concurrency", type=int, default=1,
                    help="Number of concurrent workers.")
    a = ap.parse_args()
    print(f"[assume] overhead_ms={a.mean_latency_ms:.0f}  concurrency={a.concurrency}")

if __name__ == "__main__":
    main()